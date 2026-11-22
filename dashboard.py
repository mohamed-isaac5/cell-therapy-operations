"""Read-only overview of retained work. No refresh, matching or mutations."""
from collections import Counter
import reporting,storage,hospitals

def hospital_summary(c):
 profiles=reporting.rows(c,'hospital_profiles');links=reporting.rows(c,'hospital_trial_links');saved={(r['hospital_id'],r['nct']):r for r in reporting.rows(c,'hospital_assessments')};states=Counter();invalid=0
 for link in links:
  row=saved.get((link['hospital_id'],link['nct']));a=reporting.safe_json(row['payload']) if row else hospitals.default_assessment();axes=a.get('axes',[]) if isinstance(a,dict) else []
  if len(axes)!=6 or any(not isinstance(x,dict) or x.get('axis')!=hospitals.AXES[i] or x.get('status') not in hospitals.COLORS for i,x in enumerate(axes)):
   states['Unavailable']+=1;invalid+=1
  else:states[hospitals.aggregate(axes)]+=1
 return dict(locations=len(profiles),trial_links=len(links),regions=dict(Counter(r['region'] for r in profiles)),assessment_states=dict(states),invalid_assessments=invalid,missing_saved_assessments=sum((r['hospital_id'],r['nct']) not in saved for r in links),unassigned_locations=sum(not r['owner'] for r in profiles),observed_latest=max((r['observed_at'] or '' for r in links),default=None),limits='Registry-listed locations and exact retained trial links, not a contracted hospital network, verified capacity, current recruiting status or sponsor-site recommendations. Colours are local per-trial assessments, not clinical certification. Missing assessments default to Grey.')

def dashboard_state():
 report=reporting.weekly_report();s=report['research']['snapshot']
 if not s:raise ValueError('Current reporting view unavailable')
 with reporting.read_db(storage.DB) as c:
  hospital=hospital_summary(c);checks=reporting.rows(c,'source_checks');signals=reporting.rows(c,'signals');batches=reporting.rows(c,'batches')
  source=dict(checks=len(checks),statuses=dict(Counter(r['status'] for r in checks)),last_checked=max((r['checked_at'] or '' for r in checks),default=None),signal_labels=len(signals),signal_types=dict(Counter(r['kind'] for r in signals)),latest_batch=max(batches,key=lambda r:r['started_at'] or '',default=None),blocked_hosts=len(s['blocked_sources']))
 attention=[]
 for h in s['holds']:attention.append(dict(kind='Source conflict',title=h['company'],reason=h['reason'],source='Retained source-conflict review; no new source check',href='/#review'))
 if s['unknown_categories']:attention.append(dict(kind='Committee evidence',title=f"{s['unknown_categories']} unknown role categories",reason=f"Across {s['committee_accounts']} shortlist accounts. Listed roles do not establish buyer authority.",source='Retained committee research',href='/committee'))
 for title,key,url in [('CRM task','tasks','/crm'),('Research task','research_tasks','/#work')]:
  t=s[key]
  for r in t['overdue']:attention.append(dict(kind='Overdue '+title.lower(),title=r['company'],reason=f"{r['task']} | Due {r['due_date']}; owner: {r['owner'] or 'not labelled'}",source='Current local tasks, Cairo today; due-today excluded',href=url))
  if t['unassigned_active']:attention.append(dict(kind='Owner labels',title=f"{t['unassigned_active']} active {'CRM' if key=='tasks' else 'research-workflow'} records without an owner label",reason='A local owner label is not an authenticated staff assignment.',source='Current local task records',href=url))
 if hospital['missing_saved_assessments']:attention.append(dict(kind='Hospital evidence',title=f"{hospital['missing_saved_assessments']} trial links without saved assessments",reason='Grey means unknown. Registry inclusion is not operational readiness.',source='Retained hospital trial links and local assessments',href='/hospitals'))
 return dict(generated_at=report['generated_at'],period_start=report['start'],period_end=report['end_display'],research=s,sources=source,hospitals=hospital,fictional_crm=report['simulation'],fictional_replies=report['replies'],weekly_activity=report['research']['activity'],suggestions=report['suggestions'],attention=attention,conversion=report['conversion'],limits='Local read-only overview, generated on demand from retained sources. No sending, source refresh, CRM changes, matching or scheduling. Public research is not verified commercial activity. Views may be incomplete or stale. Separate read transactions are not an atomic snapshot across modules or files. No authentication or multi-user access; loopback portfolio app only. No deployment or publication.')
