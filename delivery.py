"""Local delivery planning only. No client acceptance, sharing or contract mutation."""
import json
import operations
CHECKS=['scope','evidence','gaps','owner']
def ensure(c):
 c.execute('CREATE TABLE IF NOT EXISTS delivery_plans(account TEXT PRIMARY KEY,payload TEXT NOT NULL,version INTEGER NOT NULL,updated_at TEXT NOT NULL)')
 c.execute('CREATE TABLE IF NOT EXISTS delivery_events(id INTEGER PRIMARY KEY,account TEXT NOT NULL,payload TEXT NOT NULL,created_at TEXT NOT NULL)')
def state():
 with operations.connect() as c:
  ensure(c)
  return dict(plans={r['account']:dict(json.loads(r['payload']),version=r['version'],updated_at=r['updated_at']) for r in c.execute('SELECT * FROM delivery_plans')},limits='Local operator checklist only. Not client acceptance, approved clinical advice or a contract. No sharing or automatic stage movement.')
def save(body):
 account=body.get('account')
 if account not in {a['company'] for a in operations.work_state()['accounts']}:raise ValueError('Choose a known account')
 checks=body.get('checks',{})
 if not isinstance(checks,dict) or set(checks)!=set(CHECKS) or any(type(v)!=bool for v in checks.values()):raise ValueError('Invalid delivery checks')
 status=body.get('status')
 if status not in ['Draft','Open items','Ready for internal review']:raise ValueError('Invalid internal status')
 if status=='Ready for internal review' and not all(checks.values()):raise ValueError('Complete all internal checks before marking ready')
 text={}
 for k in ['scope_note','open_items','reviewer']:
  v=body.get(k,'')
  if not isinstance(v,str) or len(v)>3000:raise ValueError('Invalid delivery note')
  text[k]=v.strip()
 if status=='Ready for internal review' and (not text['scope_note'] or not text['reviewer']):raise ValueError('Add scope and a local reviewer label before marking ready')
 payload=dict(checks=checks,status=status,**text);now=operations.clock()
 with operations.connect() as c:
  ensure(c);c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT version FROM delivery_plans WHERE account=?',(account,)).fetchone();v=r[0] if r else 0
  if type(body.get('version'))!=int or body['version']!=v:raise RuntimeError('Delivery checklist changed. Reload before saving; your text has not been replaced.')
  c.execute('INSERT OR REPLACE INTO delivery_plans VALUES(?,?,?,?)',(account,json.dumps(payload),v+1,now))
  c.execute('INSERT INTO delivery_events(account,payload,created_at) VALUES(?,?,?)',(account,json.dumps(payload),now))
 return dict(saved=True,version=v+1,updated_at=now,source_data_changed=False)
