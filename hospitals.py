"""Fictional public-demo site workflow. No fuzzy identity merging or readiness inference."""
import json,sqlite3,hashlib,datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from storage import connect,now,ROOT
AXES=['Cell collection and chain of identity','Manufacturing and scheduling','Transport and cold chain','Site preparation and administration','Staff and training','Follow-up and data collection']
COLORS=['Grey','Green','Yellow','Red']
def migrate_hospitals():
 with connect() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS hospital_profiles(id TEXT PRIMARY KEY,facility TEXT,city TEXT,country TEXT,region TEXT,owner TEXT DEFAULT '',task TEXT DEFAULT '',version INTEGER DEFAULT 0,updated_at TEXT);
CREATE TABLE IF NOT EXISTS hospital_trial_links(hospital_id TEXT,nct TEXT,company TEXT,payload TEXT,observed_at TEXT,PRIMARY KEY(hospital_id,nct));
CREATE TABLE IF NOT EXISTS hospital_assessments(hospital_id TEXT,nct TEXT,payload TEXT,version INTEGER DEFAULT 0,updated_at TEXT,PRIMARY KEY(hospital_id,nct));
CREATE TABLE IF NOT EXISTS hospital_events(id INTEGER PRIMARY KEY,hospital_id TEXT,nct TEXT,actor TEXT,event_type TEXT,before_json TEXT,after_json TEXT,created_at TEXT);''')
def seed():
 migrate_hospitals();raw=json.loads((ROOT/'hospital_sources/registry-live.json').read_text());rows=json.loads((ROOT/'hospital_sources/candidates.json').read_text())
 selected=[0,2,7,14,15,20,24,120,124,235,37,39,40,53,55,78,80,83,96,241]
 with connect() as c:
  for idx in selected:
   r=rows[idx];hid='H-'+hashlib.sha256((r['facility']+'|'+r['city']+'|'+r['country']).encode()).hexdigest()[:10]
   c.execute('INSERT OR IGNORE INTO hospital_profiles(id,facility,city,country,region,updated_at) VALUES(?,?,?,?,?,?)',(hid,*[r[k] for k in ['facility','city','country','region']],raw['fetched_at']))
   # Retain exact registry labels. Do not imply cross-campus identity resolution.
   links=[x for x in rows if (x['facility'],x['city'],x['country'])==(r['facility'],r['city'],r['country'])]
   for l in links:
    l['source_url']='https://clinicaltrials.gov/study/'+l['nct'];l['api_url']=raw['url'];l['observed_at']=raw['fetched_at']
    c.execute('INSERT OR IGNORE INTO hospital_trial_links VALUES(?,?,?,?,?)',(hid,l['nct'],l['company'],json.dumps(l),raw['fetched_at']))
 return hospital_state()
def default_assessment():return {'axes':[{'axis':a,'status':'Grey','note':'','source':'','reviewed_on':''} for a in AXES]}
def aggregate(axes):
 states=[x['status'] for x in axes]
 return 'Red' if 'Red' in states else 'Yellow' if 'Yellow' in states else 'Grey' if 'Grey' in states else 'Green'
def hospital_state():
 with connect() as c:
  out=[]
  for row in c.execute('SELECT * FROM hospital_profiles ORDER BY region DESC,facility'):
   h=dict(row);h['links']=[json.loads(x['payload']) for x in c.execute('SELECT * FROM hospital_trial_links WHERE hospital_id=? ORDER BY nct',(h['id'],))];h['assessments']={}
   for l in h['links']:
    r=c.execute('SELECT * FROM hospital_assessments WHERE hospital_id=? AND nct=?',(h['id'],l['nct'])).fetchone();a=json.loads(r['payload']) if r else default_assessment();a['version']=r['version'] if r else 0;a['updated_at']=r['updated_at'] if r else None;a['overall']=aggregate(a['axes']);h['assessments'][l['nct']]=a
   out.append(h)
  return {'hospitals':out,'events':[dict(x) for x in c.execute('SELECT * FROM hospital_events ORDER BY id DESC LIMIT 150')],'axes':AXES,'demo':__import__('os').environ.get('CGT_DEMO')=='1'}
def save_hospital(d):
 from urllib.parse import urlparse
 hid=d.get('id','');nct=d.get('nct','');actor=str(d.get('actor','Local operator')).strip()[:80] or 'Local operator';mode=d.get('mode','workflow')
 with connect() as c:
  c.execute('BEGIN IMMEDIATE')
  h=c.execute('SELECT * FROM hospital_profiles WHERE id=?',(hid,)).fetchone()
  if not h:raise ValueError('Unknown hospital')
  if mode=='workflow':
   if int(d.get('version',-1))!=h['version']:raise RuntimeError('This hospital changed. Reload before saving.')
   new={k:str(d.get(k,'')).strip() for k in ['owner','task']}
   if len(new['owner'])>120 or len(new['task'])>1000:raise ValueError('Input too long')
   if new['task'] and not new['owner']:raise ValueError('Assign an owner for this task')
   c.execute('UPDATE hospital_profiles SET owner=?,task=?,version=version+1,updated_at=? WHERE id=?',(new['owner'],new['task'],now(),hid));before=dict(h)
  elif mode=='assessment':
   if not c.execute('SELECT 1 FROM hospital_trial_links WHERE hospital_id=? AND nct=?',(hid,nct)).fetchone():raise ValueError('Trial is not linked to this hospital')
   old=c.execute('SELECT * FROM hospital_assessments WHERE hospital_id=? AND nct=?',(hid,nct)).fetchone();v=old['version'] if old else 0
   if int(d.get('version',-1))!=v:raise RuntimeError('This assessment changed. Reload before saving.')
   axes=d.get('axes',[])
   if not isinstance(axes,list) or len(axes)!=6:raise ValueError('Six assessment axes required')
   new={'axes':[]}
   for i,x in enumerate(axes):
    if x.get('axis')!=AXES[i] or x.get('status') not in COLORS:raise ValueError('Invalid assessment axis or colour')
    a={k:str(x.get(k,'')).strip() for k in ['axis','status','note','source','reviewed_on']}
    if len(a['note'])>1500 or len(a['source'])>2000:raise ValueError('Evidence too long')
    if a['status']!='Grey':
     u=urlparse(a['source'])
     if not a['note'] or u.scheme not in ['https','http'] or not u.netloc or not str(d.get('actor','')).strip():raise ValueError('Every non-grey axis needs evidence URL, note, review date and reviewer label')
     dt=datetime.date.fromisoformat(a['reviewed_on'])
     if dt>datetime.datetime.now(ZoneInfo('Africa/Cairo')).date():raise ValueError('Review date cannot be in the future')
    new['axes'].append(a)
   before=json.loads(old['payload']) if old else default_assessment()
   c.execute('INSERT OR REPLACE INTO hospital_assessments VALUES(?,?,?,?,?)',(hid,nct,json.dumps(new),v+1,now()))
  else:raise ValueError('Invalid save mode')
  c.execute('INSERT INTO hospital_events(hospital_id,nct,actor,event_type,before_json,after_json,created_at) VALUES(?,?,?,?,?,?,?)',(hid,nct,actor,mode,json.dumps(before),json.dumps(new),now()))
 return {'saved':True}
if __name__=='__main__':
 s=seed();print(json.dumps({'hospitals':len(s['hospitals']),'links':sum(len(x['links']) for x in s['hospitals']),'regions':{r:sum(x['region']==r for x in s['hospitals']) for r in ['US','Europe']},'sponsors':len({l['company'] for x in s['hospitals'] for l in x['links']})}))
