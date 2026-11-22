"""Fixed fictional reply scenarios and human-reviewed suggestions. No messaging or CRM writes."""
import os,json,sqlite3,hashlib,datetime
from pathlib import Path
import storage
DB=Path(os.environ.get('CGT_REPLIES_DB',storage.ROOT/'replies-simulation.db'))
CATEGORIES=['Sample requested','Scope question','Experience question','Deferred','Referral','Not interested','Do not contact','Ambiguous']
SCENARIOS=[
 {'id':'sample','company':'Demo Alder Sponsor','role':'Fictional clinical operations lead','context':'Fictional sponsor considering how to coordinate its first two cell-therapy sites. No work has been delivered.','prior':'Would a one-page sample showing site-to-manufacturing hand-off gaps help you assess whether a Cell Therapy Operations Review is relevant?','reply':'Please send the sample first. We are not looking to book a call at this stage.','category':'Sample requested','why':'Explicit request for a sample, with an explicit no-call boundary. This is not a booked consultation.','draft':'The sample is a fictional one-page hand-off map, not client work. It shows gaps, proposed owners and next actions. No call needed.','task':'Review the labelled sample and attachment wording before any separate, authorized send. Do not propose a call.','due':''},
 {'id':'scope','company':'Demo Cedar Hospital','role':'Fictional programme director','context':'Fictional hospital exploring a first cell-therapy programme. No patient data, dates or capacity claims.','prior':'Would a short outline of the Cell Therapy Operations Review help your team assess site-readiness gaps?','reply':'What would we actually receive, and would this include staff training or just recommendations?','category':'Scope question','why':'Asks about outputs and training. It does not establish a purchase, readiness assessment or meeting.','draft':'The proposed review ends with written operational gaps, suggested owners and next actions. Staff training would be a separate scope, only if the review shows a need.','task':'Review the scope wording. Keep training separate and avoid quoting an unapproved delivery date or price.','due':''},
 {'id':'experience','company':'Demo Fir Sponsor','role':'Fictional operations director','context':'Fictional sponsor asks for credentials. This portfolio case has no real clients, outcomes or references.','prior':'Would it help to see a fictional site-to-manufacturing hand-off map for a cell-therapy programme?','reply':'Before we go further, which sponsors have you supported and can you share a reference?','category':'Experience question','why':'A credibility question, not proof of interest or permission to invent clients.','draft':'This is a portfolio simulation, not a claim of sponsor work. I do not have client references or delivered sponsor results to share for this case. I can show the labelled fictional sample instead.','task':'Keep the lack of client references explicit. Do not substitute invented customers or outcomes.','due':''},
 {'id':'defer','company':'Demo Hazel Sponsor','role':'Fictional programme lead','context':'Scenario date: 22 November 2026. Counterpart gives a specific future date. It is a fictional planning example, not a real reminder.','prior':'Would a short outline help you assess the operational hand-offs for your planned site expansion?','reply':'We have paused this work until the budget review. Please come back on 15 January 2027, not before.','category':'Deferred','why':'Explicit deferral and date. Do not mark Lost, infer approved budget or send before that date.','draft':'Understood. No follow-up before 15 January 2027.','task':'Suggested only: review whether a follow-up is still appropriate on 15 January 2027. No reminder or outreach is created.','due':'2027-01-15'},
 {'id':'referral','company':'Demo Juniper Sponsor','role':'Fictional clinical development lead','context':'Fictional role referral with no named person, verified handle or introduction.','prior':'Are you the right person to assess a Cell Therapy Operations Review, or does clinical operations own this?','reply':'Our clinical operations team handles that. I am not involved in vendor selection.','category':'Referral','why':'Refers to a team, not a verified buyer or permission to contact someone new.','draft':'Thanks for clarifying. Is there a preferred route to the clinical operations team?','task':'Review the clarification question. No new contact, recipient or buying authority is established.','due':''},
 {'id':'no-fit','company':'Demo Maple Sponsor','role':'Fictional operations lead','context':'Fictional team says the capability is internal. No real deal or revenue exists.','prior':'Would a sample operational hand-off map help your team check gaps across its cell-therapy sites?','reply':'Thanks, but we have an internal team covering this and are not looking for outside support.','category':'Not interested','why':'Clear refusal. No rebuttal, nurture sequence or invented loss amount.','draft':'','task':'Stop follow-up for this fictional thread. No reply is needed; no CRM outcome is created.','due':''},
 {'id':'stop','company':'Demo Willow Sponsor','role':'Fictional recipient','context':'Fictional opt-out example. This app is not connected to any sending system or real suppression list.','prior':'Would a labelled sample of a cell-therapy hand-off review be useful to your team?','reply':'Please remove me from your list and do not contact me again.','category':'Do not contact','why':'Explicit opt-out. Suppress recommendations here, do not argue, ask why or schedule another approach.','draft':'','task':'Stop all follow-up recommendations for this fictional scenario. This does not update a real suppression system.','due':''},
 {'id':'ambiguous','company':'Demo Oak Sponsor','role':'Fictional programme team member','context':'Brief reply gives no question, decision or timing. No genuine interaction exists.','prior':'Would a short outline of a Cell Therapy Operations Review help your team assess hand-off risks?','reply':'Interesting. We are working through a few things internally.','category':'Ambiguous','why':'No clear request, timeline or commitment. It must remain Needs review.','draft':'','task':'Human review needed. Do not infer interest, book a call, invent a follow-up date or advance the pipeline.','due':''}
]
def _connect():
 if DB.resolve()==storage.DB.resolve():raise ValueError('Reply simulation must not use the public-research database')
 c=sqlite3.connect(DB,timeout=30);c.row_factory=sqlite3.Row;return c

def migrate_replies():
 with _connect() as c:c.executescript('''CREATE TABLE IF NOT EXISTS reply_reviews(id TEXT PRIMARY KEY,version INTEGER NOT NULL,context_hash TEXT NOT NULL,category TEXT NOT NULL,decision TEXT NOT NULL,draft TEXT NOT NULL,task TEXT NOT NULL,due_date TEXT NOT NULL,reviewer TEXT NOT NULL,reason TEXT NOT NULL,updated_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS reply_events(id INTEGER PRIMARY KEY,scenario_id TEXT NOT NULL,before_json TEXT NOT NULL,after_json TEXT NOT NULL,created_at TEXT NOT NULL);''')

def scenario(ident):
 s=next((dict(s) for s in SCENARIOS if s['id']==ident),None)
 if s is None:raise ValueError('Unknown fictional scenario')
 s['context_hash']=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest();return s

def reply_state():
 migrate_replies()
 with _connect() as c:
  reviews={r['id']:dict(r) for r in c.execute('SELECT * FROM reply_reviews')}
  items=[]
  for source in SCENARIOS:
   s=scenario(source['id']);r=reviews.get(s['id']);s['review']=r;s['version']=r['version'] if r else 0;s['outdated']=bool(r and r['context_hash']!=s['context_hash']);s['state']='Needs review' if not r or s['outdated'] else r['decision'];items.append(s)
  return {'space':'fictional-replies-only','scenarios':items,'categories':CATEGORIES,'events':[dict(e) for e in c.execute('SELECT * FROM reply_events ORDER BY id DESC LIMIT 100')],'limits':'Suggestions only. No sending, calendar reminders, real suppression sync or CRM updates. the held account stays Hold in public research.'}

def save_reply(data):
 if data.get('space')!='fictional-replies-only':raise ValueError('Only the separate fictional reply space is supported')
 s=scenario(data.get('id'));decision=data.get('decision');category=data.get('category')
 if data.get('context_hash')!=s['context_hash']:raise RuntimeError('Scenario context changed. Reload and review again.')
 if decision not in ['Needs review','Reviewed suggestion','Stop follow-up']:raise ValueError('Invalid review decision')
 if category not in CATEGORIES:raise ValueError('Invalid classification')
 fields={k:str(data.get(k,'')).strip() for k in ['draft','task','due_date','reviewer','reason']}
 if any(len(v)>3000 for v in fields.values()) or len(fields['reviewer'])>120:raise ValueError('Input too long')
 if not fields['reviewer'] or not fields['reason']:raise ValueError('Reviewer and reason are required')
 if fields['due_date']:
  try:
   if datetime.date.fromisoformat(fields['due_date']).isoformat()!=fields['due_date']:raise ValueError()
  except ValueError:raise ValueError('Use a valid YYYY-MM-DD date')
 # Conservative fixed-scenario guardrails. Labels cannot erase the source reply boundary.
 if s['id'] in ['stop','no-fit']:
  if category!=s['category'] or decision!='Stop follow-up' or fields['draft'] or fields['due_date']:raise ValueError('A clear refusal requires Stop follow-up, its original category, no draft and no follow-up date')
 if s['id']=='ambiguous' or category=='Ambiguous':
  if decision!='Needs review' or fields['draft'] or fields['due_date']:raise ValueError('Ambiguous replies remain Needs review, with no draft or invented date')
 if s['id'] in ['stop','no-fit','ambiguous'] and fields['task']!=s['task']:raise ValueError('Keep the fixed no-follow-up or human-review task for this protected scenario')
 if s['id']=='defer' and fields['due_date'] and fields['due_date']<'2027-01-15':raise ValueError('No suggested follow-up before the explicit fictional date')
 if decision=='Reviewed suggestion' and (not fields['draft'] or not fields['task']):raise ValueError('A reviewed suggestion needs both draft wording and a next-task explanation')
 if decision=='Stop follow-up' and (fields['draft'] or fields['due_date']):raise ValueError('Stop follow-up has no outgoing draft or date')
 with _connect() as c:
  c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT * FROM reply_reviews WHERE id=?',(s['id'],)).fetchone();old=dict(row) if row else None;v=old['version'] if old else 0
  if type(data.get('version')) is not int or data['version']!=v:raise RuntimeError('This review changed. Reload before saving; nothing was overwritten.')
  new=dict(id=s['id'],version=v+1,context_hash=s['context_hash'],category=category,decision=decision,**fields,updated_at=storage.now())
  keys=list(new);c.execute('INSERT OR REPLACE INTO reply_reviews ('+','.join(keys)+') VALUES ('+','.join('?' for _ in keys)+')',[new[k] for k in keys]);c.execute('INSERT INTO reply_events(scenario_id,before_json,after_json,created_at) VALUES(?,?,?,?)',(s['id'],json.dumps(old),json.dumps(dict(new,scenario_snapshot=s)),new['updated_at']))
 return new
