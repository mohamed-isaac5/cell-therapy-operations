"""Non-destructive, local committee research storage. No sending capability."""
import json
from storage import connect,now,ROOT
from prepare_committee import CATEGORIES
STATES=['Not reviewed','Needs source check','Evidence checked']
def migrate_committee():
 with connect() as c:c.executescript('''CREATE TABLE IF NOT EXISTS committee_accounts(id TEXT PRIMARY KEY,number INTEGER UNIQUE,company TEXT,payload TEXT);
CREATE TABLE IF NOT EXISTS committee_work(id TEXT PRIMARY KEY,owner TEXT DEFAULT '',task TEXT DEFAULT '',state TEXT DEFAULT 'Not reviewed',note TEXT DEFAULT '',version INTEGER DEFAULT 0,updated_at TEXT);
CREATE TABLE IF NOT EXISTS committee_events(id INTEGER PRIMARY KEY,account_id TEXT,actor TEXT,before_json TEXT,after_json TEXT,created_at TEXT);''')
def seed():
 migrate_committee();rows=json.loads((ROOT/'committee_sources/committee-seed.json').read_text())
 with connect() as c:
  for a in rows:
   c.execute('INSERT OR IGNORE INTO committee_accounts VALUES(?,?,?,?)',(a['id'],a['number'],a['company'],json.dumps(a)))
   c.execute('INSERT OR IGNORE INTO committee_work(id,updated_at) VALUES(?,?)',(a['id'],now()))
 return committee_state()
def committee_state():
 with connect() as c:
  rows=[]
  for r in c.execute('SELECT a.payload,w.* FROM committee_accounts a JOIN committee_work w ON a.id=w.id ORDER BY a.number'):
   a=json.loads(r['payload']);a['work']={k:r[k] for k in ['owner','task','state','note','version','updated_at']};rows.append(a)
  return {'accounts':rows,'categories':CATEGORIES,'events':[dict(r) for r in c.execute('SELECT * FROM committee_events ORDER BY id DESC LIMIT 150')],'demo':__import__('os').environ.get('CGT_DEMO')=='1'}
def save_committee(d):
 aid=d.get('id');actor=str(d.get('actor','Local operator')).strip()[:80] or 'Local operator'
 with connect() as c:
  c.execute('BEGIN IMMEDIATE')
  a=c.execute('SELECT * FROM committee_accounts WHERE id=?',(aid,)).fetchone();old=c.execute('SELECT * FROM committee_work WHERE id=?',(aid,)).fetchone()
  if not a or not old:raise ValueError('Unknown approved company')
  if int(d.get('version',-1))!=old['version']:raise RuntimeError('This research changed. Reload before saving; nothing was overwritten.')
  n={k:str(d.get(k,old[k])).strip() for k in ['owner','task','state','note']}
  if n['state'] not in STATES:raise ValueError('Invalid research state')
  if len(n['owner'])>120 or len(n['task'])>1000 or len(n['note'])>3000:raise ValueError('Input is too long')
  if (n['task'] or n['state']!='Not reviewed') and not n['owner']:raise ValueError('Assign a research owner first')
  if n['state']!='Not reviewed' and not n['note']:raise ValueError('A review state needs an evidence-gap or review note')
  if json.loads(a['payload'])['hold'] and n['state']=='Evidence checked':raise ValueError('Source-conflict hold: this account cannot be marked Evidence checked until the conflict is resolved outside this prototype.')
  before={k:old[k] for k in ['owner','task','state','note','version','updated_at']}
  c.execute('UPDATE committee_work SET owner=?,task=?,state=?,note=?,version=version+1,updated_at=? WHERE id=?',(*[n[k] for k in ['owner','task','state','note']],now(),aid))
  c.execute('INSERT INTO committee_events(account_id,actor,before_json,after_json,created_at) VALUES(?,?,?,?,?)',(aid,actor,json.dumps(before),json.dumps(n),now()))
 return {'saved':True}
if __name__=='__main__':
 s=seed();print(json.dumps({'accounts':len(s['accounts']),'roles':sum(len(a['roles']) for a in s['accounts'])}))
