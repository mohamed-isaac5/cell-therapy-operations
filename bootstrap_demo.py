"""Create only new fictional demo records. Refuses to overwrite a runtime database."""
from pathlib import Path
import sqlite3,json,datetime
ROOT=Path(__file__).resolve().parent
STAMP='2026-11-22T00:00:00+00:00'
def main():
 paths=[ROOT/n for n in ['gtm.db','crm-simulation.db','replies-simulation.db','operations-local.db']]
 if any(p.exists() for p in paths):raise SystemExit('A runtime database already exists. Keep it or move it aside yourself. No data was overwritten.')
 schemas=json.loads((ROOT/'demo-schema.json').read_text())
 for name,items in schemas.items():
  with sqlite3.connect(ROOT/name) as c:
   for item in items:c.execute(item['sql'])
 with sqlite3.connect(ROOT/'gtm.db') as c:
  for i,label in enumerate(['Alder','Birch','Cedar'],1):
   company='Demo Sponsor '+label
   c.execute('INSERT INTO companies VALUES(?,?,?,?,?,?,?,?,?)',(i,company,0,0,1,1,1,'FICTIONAL: a workflow practice record, not research.',STAMP))
   nct='DEMO-TRIAL-'+str(i)
   c.execute('INSERT INTO trials VALUES(?,?,?,?,?,?,?,?,?)',(i,nct,company,'FICTIONAL cell therapy workflow example '+str(i),'Unknown','UNKNOWN','2026-11-22',1,'United States'))
   c.execute('INSERT INTO sites VALUES(?,?,?,?)',(i,'Demo Hospital '+label,company,'United States'))
   for source in ['careers','funding','regulatory']:c.execute('INSERT INTO source_checks VALUES(?,?,?,?,?,?)',(company,source,'not_discovered','FICTIONAL demo: no external source was fetched.','',STAMP))
   c.execute('INSERT INTO account_work VALUES(?,?,?,?,?,?,?,?,?)',(company,'Demo analyst','Researching','FICTIONAL: write the next evidence question','','Not reviewed','All records in this public demo are invented.',0,STAMP))
   ident='BC'+str(i).zfill(2)
   payload=dict(id=ident,number=i,company=company,source_url='',retrieved_at=STAMP,source_date='Not applicable: fictional',roles=[],unknown_categories=['Clinical operations','Clinical strategy','Technical & quality','Executive / budget'],caveat='Invented workflow fixture. No named people, email or buyer authority.',hold=False,scope='Fictional public demo only',relationship='None',authority='Unknown',procurement_process='Unknown',source_status='No external evidence')
   c.execute('INSERT INTO committee_accounts VALUES(?,?,?,?)',(ident,i,company,json.dumps(payload)));c.execute('INSERT INTO committee_work VALUES(?,?,?,?,?,?,?)',(ident,'','','Not reviewed','FICTIONAL demo',0,STAMP))
   hid='DEMO-H'+str(i);facility='Demo Hospital '+label
   c.execute('INSERT INTO hospital_profiles VALUES(?,?,?,?,?,?,?,?,?)',(hid,facility,'Demo City','United States','US','','',0,STAMP))
   link=dict(facility=facility,city='Demo City',country='United States',region='US',nct=nct,company=company,lead_sponsor=company,status='UNKNOWN',overall_status='UNKNOWN',updated='2026-11-22',title='FICTIONAL site-context fixture',conditions=['Fictional scenario only'],source_url='',api_url='',observed_at=STAMP)
   c.execute('INSERT INTO hospital_trial_links VALUES(?,?,?,?,?)',(hid,nct,company,json.dumps(link),STAMP))
  c.execute('INSERT INTO app_settings VALUES(?,?)',('registry_refresh',json.dumps({'status':'fictional_offline_demo','checked_at':STAMP,'scope':'Three invented records. No live registry research.'})))
 print('Created fictional demo databases. No retained research, real people, credentials or external fetches.')
if __name__=='__main__':main()
