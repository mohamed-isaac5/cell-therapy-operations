"""Additive local operations workspace. Existing three databases are read-only here."""
import datetime as dt, hashlib, json, os, sqlite3, uuid
from pathlib import Path
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
import storage, reporting, fit, crm, replies, outreach
ROOT=Path(__file__).resolve().parent
SIDE=Path(os.environ.get('CGT_OPERATIONS_DB',ROOT/'operations-local.db'))
TZ=ZoneInfo('Africa/Cairo')

def clock():return dt.datetime.now(dt.timezone.utc).isoformat()
def connect():
 c=sqlite3.connect(SIDE,timeout=30);c.row_factory=sqlite3.Row
 c.executescript('CREATE TABLE IF NOT EXISTS plans(key TEXT PRIMARY KEY,payload TEXT NOT NULL,version INTEGER NOT NULL);CREATE TABLE IF NOT EXISTS plan_events(id INTEGER PRIMARY KEY,key TEXT,payload TEXT,created_at TEXT);CREATE TABLE IF NOT EXISTS snapshots(id TEXT PRIMARY KEY,created_at TEXT,payload TEXT NOT NULL,digest TEXT NOT NULL);')
 return c

def link(path,**params):return path+'?'+urlencode(params)
def rows(c,t):return [dict(r) for r in c.execute('SELECT * FROM '+t)]
def source_manifest():
 paths=[storage.DB,crm.db_path('simulation'),Path(os.environ.get('CGT_REPLIES_DB',ROOT/'replies-simulation.db'))]+[ROOT/n for n in ['cell.json','gene.json','fit-reviewed-events.json']]
 # Includes WAL commits using read-only SQLite backup to an in-memory database.
 result={}
 for p in paths:
  p=Path(p)
  if p.suffix=='.db':
   with reporting.read_db(p) as c:
    logical='\n'.join(c.iterdump()).encode();result[p.name]=hashlib.sha256(logical).hexdigest()
  else:result[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
 return result

def work_state():
 today=dt.datetime.now(TZ).date().isoformat();tasks=[];empty=[];modality=fit.raw_modalities();drafts={}
 def add(module,key,company,r,href,space='research'):
  task=str(r.get('task') or '').strip()
  if not task:
   empty.append(dict(module=module,key=key,company=company,owner=r.get('owner') or '',space=space));return
  due=r.get('due_date') or '';status=r.get('status') or r.get('state') or r.get('decision') or 'Recorded task'
  tasks.append(dict(id=space+':'+module+':'+key,module=module,company=company,task=task,owner=r.get('owner') or '',due_date=due,timing='overdue' if due and due<today else 'today' if due==today else 'upcoming' if due else 'no date',status=status,blocked='hold' in (str(status)+' '+str(r.get('stage',''))).lower(),href=href,space=space,version=r.get('version',0),completion='Source has no task-level Done field; review source status, do not infer completion.'))
 with reporting.read_db(storage.DB) as c:
  trials=rows(c,'trials');evidence=rows(c,'source_evidence');holds={r['company']:r for r in rows(c,'review_flags')};saved_drafts={r['company']:r for r in rows(c,'outreach_work')}
  research=rows(c,'account_work');committee=rows(c,'committee_accounts');cw={r['id']:r for r in rows(c,'committee_work')};hosp=rows(c,'hospital_profiles');hl=rows(c,'hospital_trial_links');cr=rows(c,'crm_deals')
  for r in research:add('Research',r['company'],r['company'],r,link('/',company=r['company'])+'#work')
  for r in committee:add('Committee',r['id'],r['company'],cw[r['id']],link('/committee',company=r['company']))
  for r in hosp:add('Hospitals',r['id'],r['facility'],r,link('/hospitals',record=r['id']))
  for r in cr:add('CRM',r['id'],r['company'],r,link('/crm',company=r['company']))
 with reporting.read_db(crm.db_path('simulation')) as c:
  for r in rows(c,'crm_deals'):add('CRM',r['id'],r['company'],r,link('/crm',company=r['company'],space='simulation'),'simulation')
 with connect() as c:plans={r['key']:dict(json.loads(r['payload']),version=r['version']) for r in c.execute('SELECT * FROM plans')};snaps=[dict(r) for r in c.execute('SELECT id,created_at,digest FROM snapshots ORDER BY created_at DESC')]
 for t in tasks:
  canonical=next((short for short,long in fit.MAP if t['company'] in (short,long)),t['company']);plan=plans.get(canonical,{}) if t['space']=='research' else {}
  t['planning_blocker']=plan.get('blocker','');t['blocked']=t['blocked'] or bool(t['planning_blocker']);t['priority']=plan.get('priority','Not set');t['effort']=plan.get('effort','Unknown')
 aliases=dict(fit.MAP);names=sorted(set(r['company'] for r in committee)|set(r['company'] for r in research))
 accounts=[]
 for name in names:
  canonical=next((short for short,long in fit.MAP if name in (short,long)),name)
  if canonical!=name:continue
  radar=aliases.get(name,name);known={name,radar};account_tasks=[t for t in tasks if t['space']=='research' and t['company'] in known]
  br=next((r for r in committee if r['company']==name),None);bc=json.loads(br['payload']) if br else None
  if bc:bc['work']=cw.get(br['id'],{})
  draft=None
  if name in aliases:
   f=fit.compute_account(name,radar,[t for t in trials if t['company']==radar],[e for e in evidence if e['company']==radar],holds.get(radar),modality,dt.datetime.now(dt.timezone.utc).date());f['number']=next(i for i,(short,long) in enumerate(fit.MAP,1) if short==name)
   fresh=outreach.make_draft(f,bc);saved=saved_drafts.get(name);draft=dict(current=fresh,saved=saved,stale=bool(saved and saved['source_hash']!=fresh['source_hash']))
  accounts.append(dict(company=name,radar=radar,mapped=radar is not None,committee=bc,draft=draft,tasks=account_tasks,hospitals=[dict(hospital_id=l['hospital_id'],nct=l['nct'],company=l['company'],href=link('/hospitals',record=l['hospital_id'])) for l in hl if l['company'] in known],links=dict(research=link('/',company=radar or name)+'#work',committee=link('/committee',company=name),crm=link('/crm',company=name),review=link('/reviews',company=name))))
 return dict(demo=os.environ.get('CGT_DEMO')=='1',generated_at=clock(),today=today,tasks=tasks,empty_records=empty,accounts=accounts,plans=plans,snapshots=snaps,manifest=source_manifest(),limits='Read aggregation, not an atomic cross-file snapshot. Explicit aliases only. Distinct source tasks remain distinct. Simulation is separate. Planning notes never change source evidence, scores, approvals or task status.')

FIELDS={'priority':{'Not set','High','Normal','Low'},'effort':{'Unknown','Short','Medium','Long'},'blocker':None,'next_evidence':None,'note':None,'proposal_subject':None,'proposal_body':None,'reconciliation_note':None}
def save_plan(body):
 key=str(body.get('key',''));valid={a['company'] for a in work_state()['accounts']}
 if key not in valid:raise ValueError('Choose a known account')
 payload={}
 for k,allowed in FIELDS.items():
  v=body.get(k,'Not set' if k=='priority' else 'Unknown' if k=='effort' else '')
  if not isinstance(v,str) or len(v)>3000 or (allowed and v not in allowed):raise ValueError('Invalid planning field: '+k)
  payload[k]=v.strip()
 with connect() as c:
  c.execute('BEGIN IMMEDIATE');old=c.execute('SELECT version FROM plans WHERE key=?',(key,)).fetchone();v=old[0] if old else 0
  if body.get('version')!=v:raise RuntimeError('Planning note changed. Reload before saving.')
  c.execute('INSERT OR REPLACE INTO plans VALUES(?,?,?)',(key,json.dumps(payload),v+1));c.execute('INSERT INTO plan_events(key,payload,created_at) VALUES(?,?,?)',(key,json.dumps(payload),clock()))
 return dict(saved=True,version=v+1,source_data_changed=False)

def create_snapshot(body):
 report=reporting.weekly_report(body.get('week') or None);data=work_state();payload=dict(report=report,work=data,method='Retained evidence at manual capture time, not a historical reconstruction. Separate read transactions; no atomic cross-module snapshot.',schema=1)
 raw=json.dumps(payload,sort_keys=True);digest=hashlib.sha256(raw.encode()).hexdigest();sid=uuid.uuid4().hex;created=clock()
 with connect() as c:c.execute('INSERT INTO snapshots VALUES(?,?,?,?)',(sid,created,raw,digest))
 return dict(id=sid,created_at=created,digest=digest)
def get_snapshot(sid):
 with connect() as c:r=c.execute('SELECT * FROM snapshots WHERE id=?',(sid,)).fetchone()
 if not r:raise ValueError('Snapshot not found')
 if hashlib.sha256(r['payload'].encode()).hexdigest()!=r['digest']:raise ValueError('Snapshot integrity check failed')
 return dict(id=r['id'],created_at=r['created_at'],digest=r['digest'],payload=json.loads(r['payload']))
