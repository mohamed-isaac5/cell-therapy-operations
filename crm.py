"""Local CRM with a physically separate fictional simulation database."""
import os,sqlite3,json,hashlib,datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from storage import ROOT,now
import storage
from fit import fit_state
from committee import committee_state
STAGES=['Target account','Buying committee','Conversation','Cell Therapy Operations Review','Tiered service','Expanded deal']
STATUSES=['Active','Hold','Lost','Won']
LOSS_REASONS=['Chose a larger CRO','Building internally','Decision deferred','Not a service fit','Other']
PROOFS=['committee_note','conversation_note','consultation_output','service_scope','expanded_outcome']
SCHEMA='''CREATE TABLE IF NOT EXISTS crm_deals(id TEXT PRIMARY KEY,company TEXT,stage INTEGER,status TEXT,owner TEXT,task TEXT,due_date TEXT,note TEXT,loss_reason TEXT,proof_json TEXT,version INTEGER,updated_at TEXT);
CREATE TABLE IF NOT EXISTS crm_events(id INTEGER PRIMARY KEY,deal_id TEXT,actor TEXT,reason TEXT,before_json TEXT,after_json TEXT,created_at TEXT);'''
def db_path(space):
 if space=='research':return storage.DB
 if space=='simulation':
  p=Path(os.environ.get('CGT_CRM_DEMO_DB',ROOT/'crm-simulation.db'))
  if p.resolve()==Path(storage.DB).resolve():raise ValueError('Simulation database must be separate from public research')
  return p
 raise ValueError('Choose research or simulation workspace')
def db(space):
 c=sqlite3.connect(db_path(space),timeout=30);c.row_factory=sqlite3.Row;c.execute('PRAGMA journal_mode=WAL');return c
def base_inputs():
 f=fit_state();comm={a['company']:a for a in committee_state()['accounts']};out={}
 for a in f['accounts']:
  roles=comm.get(a['company'],{}).get('roles',[]);trial=next(c for c in a['criteria'] if c['key']=='trial');has_names=bool(roles)
  gate=dict(hold=a['hold'],programme=trial['status']=='Verified',committee_names=has_names,roles=roles,programme_evidence=trial['evidence'],buyer_verified=False)
  gate['source_hash']=hashlib.sha256(json.dumps(gate,sort_keys=True).encode()).hexdigest();out['shortlist-'+str(a['number']).zfill(2)]={'company':a['company'],'number':a['number'],'inputs':gate}
 return out
def blank_proofs():return {k:'' for k in PROOFS}
def migrate_crm():
 inputs=base_inputs()
 for space in ['research','simulation']:
  with db(space) as c:c.executescript(SCHEMA)
 with db('research') as c:
  for ident,a in inputs.items():c.execute('INSERT OR IGNORE INTO crm_deals VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(ident,a['company'],1,'Hold' if a['inputs']['hold'] else 'Active','','','','','',json.dumps(blank_proofs()),0,now()))
 examples=[('demo-alder','Demo Alder Sponsor',3,'Active','Demo BD analyst','Prepare a fictional consultation outline','2026-11-23','Illustrative conversation only. No real counterpart.', ''),('demo-cedar','Demo Cedar Hospital',4,'Active','Demo network lead','Review fictional site-readiness output','2026-11-24','Invented first-time hospital pathway. No actual consultation.', ''),('demo-elm','Demo Elm Sponsor',5,'Lost','Demo BD lead','','','Fictional prospect chose internal operations. No real lost revenue.','Building internally'),('demo-birch','Demo Birch Sponsor',6,'Won','Demo founder','','','Fictional expanded scope accepted. No real contract, price or payment.','')]
 with db('simulation') as c:
  for ident,company,stage,status,owner,task,due,note,loss in examples:
   proofs=blank_proofs()
   for j,key in enumerate(PROOFS,2):
    if j<=stage:proofs[key]='SIMULATED: '+{'committee_note':'fictional operations and medical roles mapped; no actual people.','conversation_note':'invented interest in an operations review; not a real reply.','consultation_output':'fictional hand-off gaps and next actions recorded; no delivered client work.','service_scope':'invented readiness assessment and staff-training scope; no obligation.','expanded_outcome':'fictional wider operations scope accepted; no legal agreement or money.'}[key]
   vals=(ident,company,stage,status,owner,task,due,note,loss,json.dumps(proofs),0,now())
   cur=c.execute('INSERT OR IGNORE INTO crm_deals VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',vals)
   if cur.rowcount:c.execute('INSERT INTO crm_events(deal_id,actor,reason,before_json,after_json,created_at) VALUES(?,?,?,?,?,?)',(ident,'Demo seed','Fictional initial scenario, not a recorded real transition.','{}',json.dumps(dict(zip(['id','company','stage','status','owner','task','due_date','note','loss_reason','proof_json','version','updated_at'],vals))),now()))
def unpack(r):
 a=dict(r);a['proofs']=json.loads(a.pop('proof_json'));return a
def crm_state(space='research'):
 with db(space) as c:
  rows=[unpack(r) for r in c.execute('SELECT * FROM crm_deals ORDER BY company')];events=[dict(r) for r in c.execute('SELECT * FROM crm_events ORDER BY id DESC LIMIT 100')]
 inputs=base_inputs() if space=='research' else {};today=datetime.datetime.now(ZoneInfo('Africa/Cairo')).date().isoformat()
 for a in rows:
  a['simulation']=space=='simulation';a['stage_name']=STAGES[a['stage']-1];a['inputs']=inputs[a['id']]['inputs'] if space=='research' else None
  a['source_hash']=a['inputs']['source_hash'] if a['inputs'] else 'fictional-simulation-v1';a['hold_locked']=bool(a['inputs'] and a['inputs']['hold'])
  if a['hold_locked']:a['status']='Hold'
  a['stage_reconciliation']=bool(a['inputs'] and a['stage']==2 and not(a['inputs']['programme'] and a['inputs']['committee_names']))
  a['max_stage']=2 if a['inputs'] and a['inputs']['programme'] and a['inputs']['committee_names'] and not a['hold_locked'] else 1 if a['inputs'] else 6
  a['overdue']=bool(a['status']=='Active' and a['due_date'] and a['due_date']<today)
  a['gate_note']='Simulation only. Required fictional evidence notes guard progression, not real verification.' if a['simulation'] else 'Source-conflict Hold. Progression is locked.' if a['hold_locked'] else 'No verified buyer authority or genuine interaction. Buying committee is research in progress, not a completed committee.' if a['max_stage']==2 else 'Programme or named-role evidence is incomplete. Continue account research; no later-stage completion.'
 counts=[dict(stage=i,name=name,total=sum(a['stage']==i for a in rows),active=sum(a['stage']==i and a['status']=='Active' for a in rows)) for i,name in enumerate(STAGES,1)]
 return dict(space=space,accounts=rows,events=events,stages=STAGES,statuses=STATUSES,loss_reasons=LOSS_REASONS,proof_fields=PROOFS,counts=counts,today=today,limits='Single-operator local CRM. No sending, mailbox, payments or authenticated staff roles. Simulation records are fictional and stored in a separate database. No automatic qualification or completed real conversations, consultations or deals.')
def save_crm(b):
 space=b.get('space');db_path(space);current=crm_state(space);a=next((x for x in current['accounts'] if x['id']==b.get('id')),None)
 if not a:raise ValueError('Unknown account in this workspace')
 if b.get('source_hash')!=a['source_hash']:raise RuntimeError('Research inputs changed. Reload before saving; no transition was recorded.')
 try:stage=int(b.get('stage',0));version=int(b.get('version',-1))
 except (ValueError,TypeError):raise ValueError('Stage and version must be valid integers')
 if not 1<=stage<=6:raise ValueError('Choose one of the six stages')
 n={k:str(b.get(k,'')).strip() for k in ['owner','task','due_date','note','loss_reason','status']};actor=str(b.get('actor','')).strip();reason=str(b.get('reason','')).strip()
 if n['status'] not in STATUSES:raise ValueError('Choose a valid outcome status')
 if not actor or not reason:raise ValueError('Operator label and change reason are required')
 for k,v in {**n,'actor':actor,'reason':reason}.items():
  if len(v)>(1000 if k=='task' else 3000 if k in ['note','reason'] else 120):raise ValueError('A field is too long')
 if n['due_date']:datetime.date.fromisoformat(n['due_date'])
 if n['due_date'] and not n['task']:raise ValueError('A due date needs a next task')
 if not n['owner']:raise ValueError('Assign an owner label before saving')
 if n['status']=='Active' and (not n['task'] or not n['due_date']):raise ValueError('Active work needs a next task and due date')
 if n['status']=='Hold' and not n['note']:raise ValueError('Hold needs an explanatory note')
 if n['status']=='Lost':
  if n['loss_reason'] not in LOSS_REASONS or not n['note']:raise ValueError('Lost needs a structured loss reason and explanatory note')
 elif n['loss_reason']:raise ValueError('Loss reason belongs only to Lost records; clear it when reopening')
 if a['hold_locked'] and (n['status']!='Hold' or stage!=1):raise ValueError('the held account source-conflict Hold cannot be overridden or advanced')
 if space=='research':
  if stage>a['max_stage']:raise ValueError('Missing verified programme, committee or real interaction evidence. This prototype cannot record later real activity; use the separate simulation.')
  if n['status'] in ['Lost','Won']:raise ValueError('No genuine commercial outcome is established. Use simulation for invented won/lost examples.')
  proofs=blank_proofs()
  if not isinstance(b.get('proofs',{}),dict):raise ValueError('Evidence notes must be an object')
  if any(str(v).strip() for v in b.get('proofs',{}).values()):raise ValueError('Real interaction proof entry is not enabled. Do not mix simulated activity into public research.')
 else:
  provided=b.get('proofs',{})
  if not isinstance(provided,dict):raise ValueError('Simulation evidence notes must be an object')
  proofs={k:str(provided.get(k,'')).strip() for k in PROOFS}
  if any(len(v)>2000 for v in proofs.values()):raise ValueError('Simulation evidence note is too long')
  missing=[key for i,key in enumerate(PROOFS,2) if stage>=i and not proofs[key]]
  if missing:raise ValueError('Incomplete simulation evidence: '+', '.join(missing)+'. No stage was completed.')
  if n['status']=='Won' and stage!=6:raise ValueError('Won requires Expanded deal and its fictional outcome note')
 with db(space) as c:
  c.execute('BEGIN IMMEDIATE');old=c.execute('SELECT * FROM crm_deals WHERE id=?',(a['id'],)).fetchone()
  if not old or old['version']!=version:raise RuntimeError('This CRM record changed in another tab. Reload; nothing was overwritten.')
  if space=='research' and base_inputs()[a['id']]['inputs']['source_hash']!=a['source_hash']:raise RuntimeError('Research inputs changed during save. Reload.')
  ts=now();c.execute('UPDATE crm_deals SET stage=?,status=?,owner=?,task=?,due_date=?,note=?,loss_reason=?,proof_json=?,version=version+1,updated_at=? WHERE id=?',(stage,n['status'],n['owner'],n['task'],n['due_date'],n['note'],n['loss_reason'],json.dumps(proofs),ts,a['id']))
  after=unpack(c.execute('SELECT * FROM crm_deals WHERE id=?',(a['id'],)).fetchone())
  after['decision_context']={'space':space,'source_hash':a['source_hash'],'max_stage_at_save':a['max_stage'],'simulation':space=='simulation'}
  if space=='research':after['decision_context'].update(programme_evidence=a['inputs']['programme_evidence'],named_role_sources=sorted({r['source_url'] for r in a['inputs']['roles']}),buyer_authority_verified=False)
  c.execute('INSERT INTO crm_events(deal_id,actor,reason,before_json,after_json,created_at) VALUES(?,?,?,?,?,?)',(a['id'],actor,reason,json.dumps(unpack(old)),json.dumps(after),ts))
 return dict(saved=True,space=space,version=after['version'],simulation=space=='simulation',sent=False)
