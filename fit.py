"""Deterministic evidence-backed shortlist score. Read-only; no network or AI."""
import json,re,datetime,hashlib
from pathlib import Path
from storage import connect,ROOT
VERSION='icp-evidence-v1'
ACTIVE={'RECRUITING','ACTIVE_NOT_RECRUITING','ENROLLING_BY_INVITATION','NOT_YET_RECRUITING'}
MAP=[('Demo Sponsor Alder','Demo Sponsor Alder'),('Demo Sponsor Birch','Demo Sponsor Birch'),('Demo Sponsor Cedar','Demo Sponsor Cedar')]
REGIONS={'United States','United Kingdom','Germany','Spain','France','Italy','Belgium','Netherlands','Poland','Portugal','Austria','Denmark','Sweden','Finland','Norway','Switzerland','Ireland','Czechia','Czech Republic','Romania','Bulgaria','Hungary','Greece','Saudi Arabia','United Arab Emirates','Qatar','Kuwait','Bahrain','Oman'}
# Bounded rule: evidence must describe administered cells, not merely target cells or an in-vivo vector.
CELL=re.compile(r'\bCAR[ -]?T\b|\bTCR[ -]?T\b|\b(?:autologous|allogeneic|engineered|regulatory|hematopoietic|haematopoietic)\b.{0,90}\b(?:T[ -]?cells?|stem cells?|cell therapy|NK cells?)\b|\bT[ -]cell immunotherapy\b|\bNK cell therapy\b',re.I)
def raw_modalities():
 out={}
 for file in ['cell.json','gene.json']:
  for study in json.loads((ROOT/file).read_text()).get('studies',[]):
   p=study['protocolSection'];n=p['identificationModule']['nctId'];texts=[]
   for i in p.get('armsInterventionsModule',{}).get('interventions',[]):
    texts.extend([i.get('name',''),i.get('description','')])
   texts.append(p['identificationModule'].get('briefTitle',''))
   texts.append(p.get('descriptionModule',{}).get('briefSummary',''))
   out[n]=' '.join(texts)
 return out
def criterion(key,label,status,reason,evidence=None):
 return dict(key=key,label=label,status=status,points=2 if status=='Verified' else 0,reason=reason,evidence=evidence or [])
def compute_account(name,company,trials,evidence,hold,modality,as_of):
 rows=[];eligible=[];regional=[]
 for t in trials:
  text=modality.get(t['nct'],'')
  match=CELL.search(text)
  phase=bool(set(t['phases'].split(','))&{'PHASE1','PHASE2'})
  ev=dict(source='ClinicalTrials.gov retained snapshot',record=t['nct'],url='https://clinicaltrials.gov/study/'+t['nct'],date=t['last_update'],detail=f"{t['phases']} · {t['status']} · {t['countries']}")
  if match and phase and t['status'] in ACTIVE:
   ev['excerpt']=text[max(0,match.start()-30):match.end()+100];eligible.append(ev)
  if set(t['countries'].split('|'))&REGIONS:regional.append(ev)
 if hold:
  rows.append(criterion('trial','Phase 1/2 cell-therapy trial','Unknown','Registry evidence conflicts with a newer company update. Hold overrides fit evidence.',[dict(source='Company strategic update',url=hold['source_url'],detail=hold['reason'],date=hold['reviewed_at'])]))
 else:
  rows.append(criterion('trial','Phase 1/2 cell-therapy trial','Verified' if eligible else 'Unknown','Eligible cell-based intervention, phase and active/planned status are visible in the retained registry sample. Not proof of current commercial need.' if eligible else 'No qualifying cell-based phase 1/2 trial is established by this bounded sample. Gene therapy alone is not treated as cell therapy; this is not a company-wide exclusion.',eligible[:2]))
 rows.append(criterion('team','Small / stretched operations team','Unknown','A leadership list or vacancy does not establish operations-team size or capacity. No reliable team-size evidence has been reviewed.'))
 rows.append(criterion('manufacturing','External manufacturing / CDMO','Unknown','No reviewed evidence establishes external manufacturing for the relevant programme. A CRO is not a CDMO.'))
 hot=[];context=[]
 reviewed=json.loads((ROOT/'fit-reviewed-events.json').read_text())
 for e in evidence:
  if e['source'] not in {'funding','careers'}:continue
  context.append(dict(source=e['title'],url=e['url'],date=e['event_date'] or 'Event date not verified',detail=e['verification']))
  # Only reviewed exact-source records can supply dates missing from collector fields.
  date=e['event_date'][:10] if e['event_date'] else ''
  if not date:
   match=next((r for r in reviewed if r['company']==company and r['url']==e['url'] and r['excerpt_hash']==hashlib.sha256(e['excerpt'].encode()).hexdigest()),None)
   if match:date=match['date'];context[-1]['date']=date
  try:age=(as_of-datetime.date.fromisoformat(date)).days
  except ValueError:continue
  if e['verification']=='publisher_announcement_retrieved' and e['source']=='funding' and 0<=age<=28:
   hot.append(dict(source=e['title'],url=e['url'],date=date,detail=f'Publisher financing event, {age} day(s) old. Not buying intent.'))
 rows.append(criterion('signal','Hot signal within 28 days','Verified' if hot and not hold else 'Unknown','A dated publisher financing event falls within the agreed 28-day window. Funding is not buying intent.' if hot and not hold else 'No current positive signal has been verified in the bounded evidence. Old news, undated jobs, trial updates and leadership appointments do not earn points.',hot if hot and not hold else context[:3]))
 rows.append(criterion('region','US / Europe / Gulf trial footprint','Verified' if regional else 'Unknown','Retained trial locations include the agreed region. This is trial footprint, not company headquarters or a complete operating-market map.' if regional else 'No mapped registry evidence establishes the agreed trial-location footprint for this shortlist record.',regional[:2]))
 pts=sum(r['points'] for r in rows);unknown=sum(r['status']=='Unknown' for r in rows);notmet=sum(r['status']=='Not met' for r in rows)
 return dict(company=name,radar_company=company,points=pts,max_points=10,unknown=unknown,not_met=notmet,criteria=rows,hold=bool(hold),status='Hold' if hold else 'Incomplete evidence',complete=unknown==0,reason='Source-conflict hold. Excluded from the ranked queue.' if hold else f'{pts}/10 evidence-backed points; {unknown} of 5 criteria unknown. Research order only, not final qualification.',rule_version=VERSION)
def fit_state(as_of=None):
 as_of=as_of or datetime.datetime.now(datetime.timezone.utc).date();modality=raw_modalities();accounts=[]
 with connect() as c:
  for i,(name,company) in enumerate(MAP,1):
   trials=[dict(r) for r in c.execute('select * from trials where company=?',(company,))] if company else []
   evidence=[dict(r) for r in c.execute('select * from source_evidence where company=?',(company,))] if company else []
   h=c.execute('select * from review_flags where company=?',(company,)).fetchone() if company else None
   a=compute_account(name,company,trials,evidence,dict(h) if h else None,modality,as_of);a['number']=i;accounts.append(a)
  setting=c.execute("select value from app_settings where key='registry_refresh'").fetchone()
 accounts.sort(key=lambda a:(a['hold'],-a['points'],a['company'].lower()))
 previous=None;rank=0
 for i,a in enumerate(accounts,1):
  if a['hold']:a['rank']=None;continue
  if a['points']!=previous:rank=i
  a['rank']=rank;previous=a['points']
 return dict(accounts=accounts,as_of=as_of.isoformat(),rule_version=VERSION,registry=json.loads(setting[0]) if setting else None,limits='Read-only calculation from retained evidence. Refreshing the page recalculates the score, not the sources. No final ICP score, automatic exclusion, AI or contact approval. Ties share a rank; alphabetical order only breaks the display tie.')
