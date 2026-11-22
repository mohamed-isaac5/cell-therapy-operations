"""Internal message decision queue. Decisions bind immutable copy/evidence snapshots."""
import json,hashlib
from storage import connect,now,ROOT
from outreach import outreach_state
DECISIONS=['Copy reviewed','Return for revision','Hold']
def migrate_reviews():
 with connect() as c:c.executescript('''CREATE TABLE IF NOT EXISTS message_reviews(company TEXT PRIMARY KEY,decision TEXT,reviewer TEXT,reason TEXT,snapshot_hash TEXT,snapshot_json TEXT,version INTEGER DEFAULT 0,created_at TEXT);
CREATE TABLE IF NOT EXISTS message_review_events(id INTEGER PRIMARY KEY,company TEXT,decision TEXT,reviewer TEXT,reason TEXT,snapshot_hash TEXT,snapshot_json TEXT,version INTEGER,created_at TEXT);''')
def snapshot(a):
 return {k:a[k] for k in ['company','subject','body','source_hash','version','evidence','pain_hypothesis','proposed_output','target','gaps','eligible','hold','stale']}|{'sample_pdf_sha256':hashlib.sha256((ROOT/'sample-map.pdf').read_bytes()).hexdigest(),'copy_rules':'sales-drafts-v2-short'}
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def review_state():
 o=outreach_state()
 with connect() as c:
  saved={r['company']:dict(r) for r in c.execute('SELECT * FROM message_reviews')};events=[dict(r) for r in c.execute('SELECT * FROM message_review_events ORDER BY id DESC LIMIT 100')]
 rows=[]
 for a in o['accounts']:
  snap=snapshot(a);h=digest(snap);r=saved.get(a['company']);outdated=bool(r and r['snapshot_hash']!=h)
  status='Source-conflict Hold' if a['hold'] else 'Needs evidence' if not a['eligible'] else 'Draft premise changed' if a['stale'] else 'Decision outdated' if outdated else r['decision'] if r else 'Needs review'
  row=dict(a,current_snapshot=snap,current_hash=h,queue_status=status,decision_outdated=outdated,decision_version=r['version'] if r else 0,last_decision=None)
  if r:r['snapshot']=json.loads(r.pop('snapshot_json'));row['last_decision']=r
  rows.append(row)
 return dict(accounts=rows,events=events,as_of=o['as_of'],decisions=DECISIONS,limits='Internal copy review only. No approval to contact, send action, email connection or real audience. Reviewer is an entered label in a single-operator local prototype, not an authenticated role.')
def save_review(b):
 a=next((a for a in review_state()['accounts'] if a['company']==b.get('company')),None)
 if not a:raise ValueError('Unknown shortlist company')
 if a['hold']:raise ValueError('Source-conflict Hold is locked. No message decision can override the held account Hold.')
 if not a['eligible']:raise ValueError('No supported sales draft. Research programme evidence before making a copy decision.')
 if a['stale']:raise ValueError('Draft premise changed. Reconcile the saved draft before deciding.')
 if b.get('current_hash')!=a['current_hash']:raise RuntimeError('Copy, evidence or Sample changed. Reload and review the current version; no decision was saved.')
 decision=b.get('decision');reviewer=str(b.get('reviewer','')).strip();reason=str(b.get('reason','')).strip()
 if decision not in DECISIONS:raise ValueError('Choose an internal copy decision, not send approval')
 if not reviewer or len(reviewer)>100:raise ValueError('Reviewer is required, up to 100 characters')
 if not reason or len(reason)>2000:raise ValueError('A clear decision reason is required, up to 2000 characters')
 with connect() as c:
  old=c.execute('SELECT * FROM message_reviews WHERE company=?',(a['company'],)).fetchone();v=old['version'] if old else 0
  if int(b.get('decision_version',-1))!=v:raise RuntimeError('Another queue decision was saved. Reload; nothing was overwritten.')
  # Re-read the draft under the writer transaction to avoid a source-version race.
  c.execute('BEGIN IMMEDIATE')
  fresh=next(x for x in review_state()['accounts'] if x['company']==a['company'])
  if fresh['current_hash']!=a['current_hash'] or fresh['decision_version']!=v:raise RuntimeError('Review inputs changed. Reload before deciding.')
  ts=now();vals=(a['company'],decision,reviewer,reason,a['current_hash'],json.dumps(a['current_snapshot'],ensure_ascii=False),v+1,ts)
  c.execute('INSERT OR REPLACE INTO message_reviews VALUES(?,?,?,?,?,?,?,?)',vals)
  c.execute('INSERT INTO message_review_events(company,decision,reviewer,reason,snapshot_hash,snapshot_json,version,created_at) VALUES(?,?,?,?,?,?,?,?)',vals)
 return {'saved':True,'decision_version':v+1,'internal_only':True}
