"""Read-only local weekly report. Recorded activity is not commercial activity."""
import datetime as dt,json,sqlite3,os
from pathlib import Path
from zoneinfo import ZoneInfo
from collections import Counter
from contextlib import contextmanager
import storage,crm,replies,fit,outreach,reviews
TZ=ZoneInfo('Africa/Cairo')
EVENTS={'research workflow':('workflow_events','created_at'),'hospital review':('hospital_events','created_at'),'committee review':('committee_events','created_at'),'draft edit':('outreach_events','created_at'),'copy decision':('message_review_events','created_at'),'CRM save':('crm_events','created_at'),'research change':('changes','created_at'),'research batch':('batches','started_at')}
def clock():return dt.datetime.now(dt.timezone.utc)
def stamp(s):
 try:
  v=dt.datetime.fromisoformat(s.replace('Z','+00:00'))
  return v if v.tzinfo else None
 except (ValueError,TypeError,AttributeError):return None
def week_bounds(value=None,now=None):
 now=now or clock()
 try:
  d=dt.date.fromisoformat(value) if value else now.astimezone(TZ).date()
  if value and d.isoformat()!=value:raise ValueError()
 except (ValueError,TypeError):raise ValueError('Choose a valid date in YYYY-MM-DD format')
 if not 1900<=d.year<=2100:raise ValueError('Choose a date between 1900 and 2100')
 d-=dt.timedelta(days=d.weekday());a=dt.datetime.combine(d,dt.time(),TZ);return a,a+dt.timedelta(days=7)
@contextmanager
def read_db(path):
 p=Path(path)
 if not p.exists():raise ValueError('A local report source is unavailable. Start the local app to initialize its databases.')
 c=sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row;c.execute('PRAGMA query_only=ON');c.execute('BEGIN')
 try:yield c
 finally:c.rollback();c.close()
def rows(c,t):return [dict(x) for x in c.execute('SELECT * FROM '+t)]
def safe_json(s):
 try:return json.loads(s)
 except (TypeError,ValueError):return {}
def event_period(c,types,a,b,now):
 result=[];invalid=0;times=[];future=0
 for label,(table,key) in types.items():
  for r in rows(c,table):
   t=stamp(r.get(key))
   if t is None:invalid+=1;continue
   times.append(t)
   if t>now:future+=1;continue
   if a<=t<b:
    before=safe_json(r.get('before_json'));after=safe_json(r.get('after_json'));seed=label=='CRM save' and not before
    result.append(dict(kind='Fictional CRM seed' if seed else 'research snapshot import' if label=='research batch' and r.get('mode')=='imported snapshot' else label,id=r['id'],at=t.astimezone(TZ).isoformat(),entity=r.get('company') or r.get('deal_id') or r.get('account_id') or r.get('hospital_id') or r.get('scenario_id') or r['id'],detail=r.get('reason') or r.get('kind') or (('Batch '+r.get('mode','')+' / '+r.get('status','')) if label=='research batch' else '') or r.get('decision') or r.get('event_type') or 'Recorded local edit, not a sent message',stage_move=bool(label=='CRM save' and before and before.get('stage')!=after.get('stage')),loss=after.get('loss_reason') if label=='CRM save' and before and before.get('status')!='Lost' and after.get('status')=='Lost' else None))
 result.sort(key=lambda r:(r['at'],str(r['id'])),reverse=True)
 return dict(count=len(result),counts=dict(Counter(r['kind'] for r in result)),stage_moves=sum(r['stage_move'] for r in result),loss_reasons=dict(Counter(r['loss'] for r in result if r['loss'])),events=result[:100],display_limit=100,undated_excluded=invalid,future_dated_excluded=future,earliest_recorded=min(times).astimezone(TZ).isoformat() if times else None,latest_recorded=max(times).astimezone(TZ).isoformat() if times else None)
def task_state(accounts,today):
 overdue=[];unassigned=0
 for r in accounts:
  if r.get('status')=='Active' and not r.get('owner'):unassigned+=1
  due=r.get('due_date','')
  try:valid=dt.date.fromisoformat(due)
  except (ValueError,TypeError):continue
  if r.get('status')=='Active' and r.get('task') and valid<today:overdue.append({k:r.get(k,'') for k in ['id','company','owner','task','due_date']})
 return dict(overdue=overdue,unassigned_active=unassigned)
def snapshot(c,now,simulation=False):
 accounts=rows(c,'crm_deals');today=now.astimezone(TZ).date()
 if not simulation:
  holds={r['company'] for r in rows(c,'review_flags')}
  held_names={name for name,company in fit.MAP if company in holds}
  for r in accounts:
   if r['company'] in held_names:r['status']='Hold'
 out=dict(crm_total=len(accounts),stages=[dict(stage=i,label=label,count=sum(r['stage']==i for r in accounts)) for i,label in enumerate(crm.STAGES,1)],statuses=dict(Counter(r['status'] for r in accounts)),loss_reasons=dict(Counter(r['loss_reason'] or 'Unspecified' for r in accounts if r['status']=='Lost')),tasks=task_state(accounts,today))
 if simulation:return out
 committees=[safe_json(r['payload']) for r in rows(c,'committee_accounts')];modality=fit.raw_modalities();trials=rows(c,'trials');evidence=rows(c,'source_evidence');holds={r['company']:r for r in rows(c,'review_flags')};draft_edits={r['company']:r for r in rows(c,'outreach_work')};decisions={r['company']:r for r in rows(c,'message_reviews')};cs={r['company']:r for r in committees};draft_states=[];queue=[]
 for i,(name,company) in enumerate(fit.MAP,1):
  a=fit.compute_account(name,company,[r for r in trials if r['company']==company],[r for r in evidence if r['company']==company],holds.get(company),modality,today);a['number']=i;d=outreach.make_draft(a,cs.get(name));saved=draft_edits.get(name)
  if saved:
   d.update({k:saved[k] for k in ['subject','body','reviewer','review_note','state','version','updated_at']});d['stale']=saved['source_hash']!=d['source_hash']
   if not d['eligible']:d.update(subject='',body='',state='Hold' if d['hold'] else 'Needs evidence')
  draft_states.append(d['state']);review=decisions.get(name);outdated=bool(review and review['snapshot_hash']!=reviews.digest(reviews.snapshot(d)))
  queue.append('Source-conflict Hold' if d['hold'] else 'Needs evidence' if not d['eligible'] else 'Draft premise changed' if d['stale'] else 'Decision outdated' if outdated else review['decision'] if review else 'Needs review')
 research_tasks=task_state([dict(r,id=r['company'],status='Hold' if r['stage']=='On hold' or r['decision'] in ['Hold','Reject'] else 'Active') for r in rows(c,'account_work')],today)
 out.update(research_tasks=research_tasks,companies=len(rows(c,'companies')),trials=len(trials),committee_accounts=len(committees),listed_roles=sum(len(a.get('roles',[])) for a in committees),unknown_categories=sum(len(a.get('unknown_categories',[])) for a in committees),committee_states=dict(Counter(r['state'] for r in rows(c,'committee_work'))),draft_states=dict(Counter(draft_states)),copy_queue=dict(Counter(queue)),saved_draft_edits=len(draft_edits),holds=list(holds.values()),blocked_sources=rows(c,'blocked_hosts'))
 return out

def weekly_report(value=None):
 now=clock();a,b=week_bounds(value,now);current=a<=now<b;future=a>now
 paths=[storage.DB,crm.db_path('simulation'),replies.DB]
 if len({Path(p).resolve() for p in paths})!=3:raise ValueError('Reporting requires separate research, CRM simulation and reply simulation databases')
 with read_db(paths[0]) as c:
  research=dict(activity=event_period(c,EVENTS,a,b,now),snapshot=snapshot(c,now) if current else None)
 with read_db(paths[1]) as c:sim=dict(activity=event_period(c,{'CRM save':('crm_events','created_at')},a,b,now),snapshot=snapshot(c,now,True) if current else None)
 with read_db(paths[2]) as c:
  reply=dict(activity=event_period(c,{'fictional reply review':('reply_events','created_at')},a,b,now),snapshot=None)
  if current:
   saved={r['id']:r for r in rows(c,'reply_reviews')};states=[]
   for s in replies.SCENARIOS:
    r=saved.get(s['id']);states.append(r['decision'] if r and r['context_hash']==replies.scenario(s['id'])['context_hash'] else 'Needs review')
   reply['snapshot']=dict(scenarios=len(states),states=dict(Counter(states)))
 suggestions=[]
 if current:
  s=research['snapshot']
  if s['holds']:suggestions.append(dict(title='Keep source-conflict accounts on Hold',reason=f"{len(s['holds'])} stored source-conflict flag(s). Review conflicting evidence before any later prioritisation. No source refresh or status change is performed."))
  if s['tasks']['overdue']:suggestions.append(dict(title='Review overdue public-research CRM work',reason=f"{len(s['tasks']['overdue'])} Active record(s) have tasks due before today in Cairo. Check owners and scope; this report changes nothing."))
  elif s['unknown_categories']:suggestions.append(dict(title='Research missing committee roles',reason=f"{s['unknown_categories']} unknown role categories across {s['committee_accounts']} shortlist accounts. Public role listings do not establish buyer authority. No outreach recommended."))
  elif s['tasks']['unassigned_active']:suggestions.append(dict(title='Assign research ownership before more activity',reason=f"{s['tasks']['unassigned_active']} Active research records have no owner label. Owner labels are not authenticated team assignments."))
 if not suggestions:suggestions=[dict(title='No next-week action inferred',reason='The selected week has no reliable end-of-week snapshot. Inspect the dated activity and current-week view before deciding. No follow-up is presumed.')]
 return dict(generated_at=now.astimezone(TZ).isoformat(),timezone='Africa/Cairo',start=a.date().isoformat(),end_exclusive=b.date().isoformat(),end_display=(b.date()-dt.timedelta(days=1)).isoformat(),period='Future week' if future else 'Current week to date' if current else 'Completed week',snapshot_label='Current computed view at generation time, not an end-of-week snapshot' if current else 'Not available. No complete, versioned historical snapshot exists for this week.',research=research,simulation=sim,replies=reply,suggestions=suggestions[:2],conversion={'value':None,'target':None,'reason':'Not available. No reliable real sending, reply or commercial-cohort tracking is connected. Local reviews, public research and fictional Won/Lost examples are not conversion data. Targets have not been agreed.'},limits='Read-only on demand. No scheduled delivery, sending, reminder, CRM changes or source refresh. Events show recorded local activity, not commercial results. Missing history is not proof that nothing happened. Current-week views are partial; completed-week snapshots are unavailable. Database reads are consistent within each file, not an atomic snapshot across three files. Event totals use all dated rows; only the latest 100 per workspace are listed. Invalid or future-dated events are excluded and disclosed.')
