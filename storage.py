"""Schema and durable workflow state for the local, single-user portfolio app."""
import sqlite3,datetime,json,os,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DB=Path(os.environ.get('CGT_DB',ROOT/'gtm.db'))
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def connect():
 c=sqlite3.connect(DB,timeout=30);c.row_factory=sqlite3.Row;c.execute('PRAGMA journal_mode=WAL');return c

def migrate():
 with connect() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS batches(id TEXT PRIMARY KEY,started_at TEXT,finished_at TEXT,mode TEXT,status TEXT,summary TEXT);
CREATE TABLE IF NOT EXISTS check_history(id INTEGER PRIMARY KEY,batch_id TEXT,company TEXT,source TEXT,status TEXT,detail TEXT,url TEXT,checked_at TEXT,UNIQUE(batch_id,company,source));
CREATE TABLE IF NOT EXISTS evidence_history(id INTEGER PRIMARY KEY,batch_id TEXT,company TEXT,source TEXT,url TEXT,payload TEXT,observed_at TEXT,UNIQUE(batch_id,company,source,url));
CREATE TABLE IF NOT EXISTS changes(id INTEGER PRIMARY KEY,batch_id TEXT,company TEXT,source TEXT,kind TEXT,before_value TEXT,after_value TEXT,created_at TEXT);
CREATE TABLE IF NOT EXISTS document_versions(id INTEGER PRIMARY KEY,url TEXT,hash TEXT,payload_path TEXT,fetched_at TEXT,http_status INTEGER,UNIQUE(url,hash));
CREATE TABLE IF NOT EXISTS blocked_hosts(host TEXT PRIMARY KEY,reason TEXT,blocked_at TEXT);
CREATE TABLE IF NOT EXISTS account_work(company TEXT PRIMARY KEY,owner TEXT NOT NULL DEFAULT '',stage TEXT NOT NULL DEFAULT 'Unassigned',task TEXT NOT NULL DEFAULT '',due_date TEXT NOT NULL DEFAULT '',decision TEXT NOT NULL DEFAULT 'Not reviewed',note TEXT NOT NULL DEFAULT '',version INTEGER NOT NULL DEFAULT 0,updated_at TEXT);
CREATE TABLE IF NOT EXISTS workflow_events(id INTEGER PRIMARY KEY,company TEXT,event_type TEXT,actor TEXT,before_json TEXT,after_json TEXT,created_at TEXT);
CREATE TABLE IF NOT EXISTS trial_history(id INTEGER PRIMARY KEY,batch_id TEXT,nct TEXT,payload TEXT,observed_at TEXT,UNIQUE(batch_id,nct));
CREATE TABLE IF NOT EXISTS app_settings(key TEXT PRIMARY KEY,value TEXT);''')
  if c.execute("select name from sqlite_master where name='companies'").fetchone():
   c.execute("INSERT OR IGNORE INTO account_work(company,updated_at) SELECT name,? FROM companies",(now(),))
   c.execute("UPDATE account_work SET stage='On hold',decision='Hold',note='Newer company evidence conflicts with registry snapshot',version=1 WHERE company IN (SELECT company FROM review_flags) AND version=0")
  if c.execute("select name from sqlite_master where name='source_checks'").fetchone():
   if not c.execute('select 1 from check_history limit 1').fetchone():
    c.execute('INSERT OR IGNORE INTO batches VALUES(?,?,?,?,?,?)',('step7-baseline',now(),now(),'imported snapshot','completed','Original step 7 observations preserved before refresh'))
    c.execute("INSERT INTO check_history(batch_id,company,source,status,detail,url,checked_at) SELECT 'step7-baseline',company,source,status,detail,url,checked_at FROM source_checks")
   if not c.execute('select 1 from evidence_history limit 1').fetchone():
    for e in c.execute('select * from source_evidence').fetchall():
     x=dict(e);c.execute('INSERT OR IGNORE INTO evidence_history(batch_id,company,source,url,payload,observed_at) VALUES(?,?,?,?,?,?)',('step7-baseline',x['company'],x['source'],x['url'],json.dumps(x),x['fetched_at']))

def save_work(data):
 allowed_stages=['Unassigned','Researching','Ready for review','Reviewed','On hold']
 allowed_decisions=['Not reviewed','Research further','Hold','Reject','Research accepted']
 company=data.get('company','');actor=data.get('actor','Local operator').strip()[:80] or 'Local operator'
 with connect() as c:
  c.execute('BEGIN IMMEDIATE')
  row=c.execute('select * from account_work where company=?',(company,)).fetchone()
  if not row:raise ValueError('Unknown company')
  old=dict(row)
  if int(data.get('version',-1))!=row['version']:raise RuntimeError('This account changed. Reload before saving; no changes were overwritten.')
  new={k:str(data.get(k,old[k])).strip() for k in ['owner','stage','task','due_date','decision','note']}
  if new['stage'] not in allowed_stages or new['decision'] not in allowed_decisions:raise ValueError('Invalid workflow state')
  if new['stage']!='Unassigned' and not new['owner']:raise ValueError('Set an owner before advancing research')
  if new['due_date']:
   datetime.date.fromisoformat(new['due_date'])
  if new['decision']!='Not reviewed' and not new['note']:raise ValueError('A review decision needs a note')
  if new['stage']=='Ready for review' and not new['task']:raise ValueError('Write the next review task first')
  if len(new['note'])>3000 or len(new['task'])>1000 or len(new['owner'])>120:raise ValueError('Input is too long')
  if c.execute('select 1 from review_flags where company=?',(company,)).fetchone() and new['stage']!='On hold':raise ValueError('This company has an unresolved source-conflict hold. Keep it on hold.')
  ts=now();c.execute('UPDATE account_work SET owner=?,stage=?,task=?,due_date=?,decision=?,note=?,version=version+1,updated_at=? WHERE company=?',(*[new[k] for k in ['owner','stage','task','due_date','decision','note']],ts,company))
  c.execute('INSERT INTO workflow_events(company,event_type,actor,before_json,after_json,created_at) VALUES(?,?,?,?,?,?)',(company,'research_work_saved',actor,json.dumps(old),json.dumps(new),ts))
  return dict(c.execute('select * from account_work where company=?',(company,)).fetchone())
if __name__=='__main__':migrate();print('Migration complete; existing records preserved.')
