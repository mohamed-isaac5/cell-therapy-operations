import unittest,tempfile,shutil,subprocess,time,urllib.request,urllib.error,json,sqlite3,os
from pathlib import Path
R=Path(__file__).resolve().parent
class PublicCandidateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.p=Path(cls.tmp.name)
  for f in R.iterdir():
   if f.is_file() and f.suffix not in ['.db','.pyc'] and '-wal' not in f.name and '-shm' not in f.name:shutil.copyfile(f,cls.p/f.name)
  r=subprocess.run(['python3','bootstrap_demo.py'],cwd=cls.p,capture_output=True,text=True);assert r.returncode==0,r.stderr
  cls.log=open(cls.p/'test-server.log','w');cls.proc=subprocess.Popen(['python3','app.py','--port','8919'],cwd=cls.p,stdout=cls.log,stderr=cls.log)
  for _ in range(150):
   try:cls.get('/api/operations');break
   except Exception:time.sleep(.05)
  else:raise AssertionError('Clean startup did not become ready')
 @classmethod
 def tearDownClass(cls):cls.proc.terminate();cls.proc.wait(timeout=10);cls.log.close();cls.tmp.cleanup()
 @classmethod
 def get(cls,path):
  with urllib.request.urlopen('http://127.0.0.1:8919'+path,timeout=5) as r:return r.status,r.read()
 @classmethod
 def post(cls,path,body):
  req=urllib.request.Request('http://127.0.0.1:8919'+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
  try:
   with urllib.request.urlopen(req,timeout=5) as r:return r.status,json.load(r)
  except urllib.error.HTTPError as e:return e.code,json.load(e)
 def test_five_main_routes(self):
  for r in ['/home','/accounts','/sites','/delivery','/reports']:
   with self.subTest(route=r):status,body=self.get(r);self.assertEqual(status,200);self.assertIn(b'FICTIONAL PUBLIC DEMO',body)
 def test_static_assets(self):
  for r in ['/workspace.js','/workspace.css','/ui.js','/ui.css','/form-safety.js','/context-links.js']:
   with self.subTest(route=r):self.assertEqual(self.get(r)[0],200)
 def test_all_api_reads(self):
  for r in ['/api/operations','/api/delivery','/api/fit','/api/committee','/api/hospitals','/api/outreach','/api/reviews','/api/replies','/api/crm','/api/report','/api/dashboard','/api/state']:
   with self.subTest(route=r):status,body=self.get(r);self.assertEqual(status,200);self.assertIsInstance(json.loads(body),dict)
 def test_all_specialist_pages(self):
  for r in ['/','/committee','/hospitals','/crm','/reviews','/replies','/operations','/report','/dashboard','/sample-map']:
   with self.subTest(route=r):self.assertEqual(self.get(r)[0],200)
 def test_only_fictional_sponsors(self):
  data=json.loads(self.get('/api/fit')[1]);self.assertEqual(len(data['accounts']),3);self.assertTrue(all(a['company'].startswith('Demo Sponsor ') for a in data['accounts']))
 def test_no_named_people(self):
  data=json.loads(self.get('/api/committee')[1]);self.assertTrue(all(not a['roles'] for a in data['accounts']))
 def test_sites_not_ready_by_default(self):
  data=json.loads(self.get('/api/hospitals')[1]);self.assertEqual(len(data['hospitals']),3);self.assertTrue(all(all(a['overall']=='Grey' for a in h['assessments'].values()) for h in data['hospitals']))
 def test_unsupported_sales_premises_not_invented(self):
  data=json.loads(self.get('/api/outreach')[1]);self.assertTrue(all(not a['eligible'] and not a['body'] for a in data['accounts']))
 def test_plan_save_and_stale_conflict(self):
  body={'key':'Demo Sponsor Alder','version':0,'next_evidence':'Fictional test question'};status,data=self.post('/api/operations/plan',body);self.assertEqual(status,200);self.assertTrue(data['saved']);self.assertFalse(data['source_data_changed']);status,data=self.post('/api/operations/plan',body);self.assertEqual(status,409)
 def test_unknown_plan_rejected(self):self.assertEqual(self.post('/api/operations/plan',{'key':'Not in demo','version':0})[0],400)
 def test_external_refresh_disabled(self):self.assertEqual(self.post('/api/run',{'mode':'refresh'})[0],403)
 def test_bootstrap_never_overwrites(self):
  before=(self.p/'gtm.db').read_bytes();r=subprocess.run(['python3','bootstrap_demo.py'],cwd=self.p,capture_output=True);self.assertNotEqual(r.returncode,0);self.assertEqual(before,(self.p/'gtm.db').read_bytes())
 def test_database_integrity(self):
  for name in ['gtm.db','crm-simulation.db','replies-simulation.db','operations-local.db']:
   with sqlite3.connect(self.p/name) as c:self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')
 def test_host_header_guard(self):
  req=urllib.request.Request('http://127.0.0.1:8919/home',headers={'Host':'example.invalid'})
  with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(req)
  self.assertEqual(e.exception.code,403)
if __name__=='__main__':unittest.main()
