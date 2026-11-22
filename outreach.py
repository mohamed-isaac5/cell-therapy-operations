"""Evidence-led, review-only sales drafts for the fictional portfolio service."""
import json,hashlib
from fit import fit_state
from committee import committee_state
from storage import connect,now
ANGLES={}
# Public demo deliberately has no company-specific sales premises.
def migrate_outreach():
 with connect() as c:c.executescript('''CREATE TABLE IF NOT EXISTS outreach_work(company TEXT PRIMARY KEY,subject TEXT,body TEXT,reviewer TEXT,review_note TEXT,state TEXT,source_hash TEXT,version INTEGER DEFAULT 0,updated_at TEXT);
CREATE TABLE IF NOT EXISTS outreach_events(id INTEGER PRIMARY KEY,company TEXT,actor TEXT,before_json TEXT,after_json TEXT,created_at TEXT);''')
def make_draft(a,committee):
 angle=ANGLES.get(a['company']);criteria={c['key']:c for c in a['criteria']};evidence=criteria['trial']['evidence'];eligible=bool(angle and criteria['trial']['status']=='Verified' and not a['hold']);trial=next((e for e in evidence if angle and e.get('record')==angle['record']),None)
 eligible=eligible and bool(trial)
 gaps=['Pain and buying intent are unverified.','No verified recipient email, sending identity, postal address or opt-out process.','No current positive outreach trigger verified; registry update is context, not buying intent.','Recheck programme status, source freshness and recipient before any real use.','Fictional service scope and sender placeholders require review.','The linked Sample is fictional format-only material. It is not a company assessment or evidence of results.']
 if a['hold']:reason='Source conflict. This account remains on Hold. No sales draft is generated.'
 elif not eligible:reason='A relevant cell-based programme is not established in the retained scoring evidence. Verify modality and programme relevance before writing a sales claim. Funding or geography alone is not enough.'
 else:reason='Evidence-led working copy. The pain is a question, not a diagnosed company problem. No draft is send-ready.'
 if not a['radar_company']:reason='No mapped registry record in this retained sample. Add reviewed programme evidence before drafting.'
 roles=(committee or {}).get('roles',[]);role=next((r for cat in ['Clinical operations','Clinical strategy'] for r in roles if r['category']==cat),None)
 target={'role':'Clinical operations / clinical development, proposed role only','person':None,'url':None,'caveat':'No named recipient established. No email guessed.'}
 if role:target={'role':role['visible_role'],'person':role['person'],'url':role['source_url'],'caveat':'Official-page role listing only. Suggested stakeholder, not a verified buyer or confirmed recipient. No email known.'}
 subject=body=''
 if eligible:
  subject=angle['subject'];fact=f"The retained ClinicalTrials.gov record for {angle['programme']} ({trial['record']}, updated {trial['date']}) lists {trial['detail']}."
  phases,status,countries=trial['detail'].split(' · ');phase=phases.replace('PHASE','Phase ').replace(',', ' / ');status={'RECRUITING':'recruiting','NOT_YET_RECRUITING':'not yet recruiting','ACTIVE_NOT_RECRUITING':'active, not recruiting'}.get(status,status.lower().replace('_',' '));opening=f"The ClinicalTrials.gov record updated {trial['date']} lists {angle['programme']} as {phase}, {status}."
  body=f"Hello,\n\n{opening}\n\n{angle['pain']}\n\nOur Cell Therapy Operations Review would {angle['output']}.\n\n{angle['cta']}\n\n[Name]\n[Fictional company]"
 else:fact='No sales premise generated from insufficient or conflicting evidence.'
 source_hash=hashlib.sha256(json.dumps({'copy_version':'v2-short','trial':trial,'hold':a['hold'],'angle':angle,'target':target},sort_keys=True).encode()).hexdigest()
 return dict(company=a['company'],number=a['number'],eligible=eligible,hold=a['hold'],reason=reason,source_hash=source_hash,subject=subject,body=body,fact=fact,pain_hypothesis=angle['pain'] if eligible else None,proposed_output=angle['output'] if eligible else None,target=target,evidence=[trial] if trial else [],gaps=gaps,state='Working draft' if eligible else ('Hold' if a['hold'] else 'Needs evidence'),version=0,reviewer='',review_note='',updated_at=None,edited=False,stale=False)
def outreach_state():
 f=fit_state();cs={a['company']:a for a in committee_state()['accounts']}
 with connect() as c:
  saved={r['company']:dict(r) for r in c.execute('SELECT * FROM outreach_work')};events=[dict(r) for r in c.execute('SELECT * FROM outreach_events ORDER BY id DESC LIMIT 100')]
 accounts=[]
 for a in f['accounts']:
  d=make_draft(a,cs.get(a['company']));s=saved.get(a['company'])
  if s:
   d.update({k:s[k] for k in ['subject','body','reviewer','review_note','state','version','updated_at']});d['edited']=True;d['stale']=s['source_hash']!=d['source_hash']
   if not d['eligible']:d.update(subject='',body='',state='Hold' if d['hold'] else 'Needs evidence')
  accounts.append(d)
 return dict(accounts=accounts,events=events,as_of=f['as_of'],version='sales-drafts-v2-short',limits='Local fictional portfolio copy. No AI, email guessing, sending endpoint or send-ready state. Edits are not fact-checked automatically. All claims and compliance details need human review before real use.')
def save_outreach(b):
 d=next((a for a in outreach_state()['accounts'] if a['company']==b.get('company')),None)
 if not d:raise ValueError('Unknown shortlist company')
 if not d['eligible']:raise ValueError('This company is held or needs programme evidence. No draft can be saved.')
 if b.get('source_hash')!=d['source_hash']:raise RuntimeError('Evidence changed. Reload and review the premise before saving.')
 if d['stale']:raise RuntimeError('Saved draft premise changed. A manual source reconciliation is required; no edit was overwritten.')
 if b.get('state') not in ['Working draft','Wording reviewed']:raise ValueError('Invalid review-only state')
 vals={k:str(b.get(k,'')).strip() for k in ['subject','body','reviewer','review_note','state']}
 if not vals['subject'] or not vals['body'] or not vals['reviewer']:raise ValueError('Subject, body and reviewer are required')
 if len(vals['subject'])>200 or len(vals['body'])>8000 or len(vals['review_note'])>2000 or len(vals['reviewer'])>100:raise ValueError('Draft field is too long')
 if vals['state']=='Wording reviewed' and not vals['review_note']:raise ValueError('Add a review note. Wording review is not contact approval.')
 with connect() as c:
  c.execute('BEGIN IMMEDIATE')
  fresh=next(a for a in outreach_state()['accounts'] if a['company']==d['company'])
  if fresh['source_hash']!=d['source_hash'] or fresh['stale'] or not fresh['eligible']:raise RuntimeError('Evidence changed during save. Reload; nothing was overwritten.')
  old=c.execute('SELECT * FROM outreach_work WHERE company=?',(d['company'],)).fetchone();v=old['version'] if old else 0
  if int(b.get('version',-1))!=v:raise RuntimeError('Draft changed in another tab. Reload; nothing was overwritten.')
  n=dict(vals,company=d['company'],source_hash=d['source_hash'],version=v+1,updated_at=now())
  c.execute('INSERT OR REPLACE INTO outreach_work VALUES(?,?,?,?,?,?,?,?,?)',tuple(n[k] for k in ['company','subject','body','reviewer','review_note','state','source_hash','version','updated_at']))
  c.execute('INSERT INTO outreach_events(company,actor,before_json,after_json,created_at) VALUES(?,?,?,?,?)',(d['company'],vals['reviewer'],json.dumps(dict(old) if old else {}),json.dumps(n),n['updated_at']))
 return {'saved':True,'version':v+1}
