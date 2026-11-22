"""Loopback-only local app. No remote deployment, auth or real sending."""
import os,json,threading,subprocess,sys,argparse
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse,parse_qs
from storage import ROOT,migrate,connect,save_work
from run_step7 import execute
from hospitals import migrate_hospitals,hospital_state,save_hospital
from committee import migrate_committee,committee_state,save_committee
from fit import fit_state
from outreach import migrate_outreach,outreach_state,save_outreach
from reviews import migrate_reviews,review_state,save_review
from replies import migrate_replies,reply_state,save_reply
from crm import migrate_crm,crm_state,save_crm
from reporting import weekly_report
from dashboard import dashboard_state
from ui_polish import polish_html
import operations, delivery
os.environ['CGT_DEMO']='1'
JOB={'running':False,'result':None};LOCK=threading.Lock()
def render():
 for script in ['render_step7.py','enhance_page.py']:
  r=subprocess.run([sys.executable,str(ROOT/script)],cwd=ROOT,capture_output=True,text=True)
  if r.returncode:raise RuntimeError(r.stderr)
def state():
 with connect() as c:
  reg=c.execute("select value from app_settings where key='registry_refresh'").fetchone()
  return {'work':[dict(x) for x in c.execute('select * from account_work order by company')],
   'events':[dict(x) for x in c.execute('select * from workflow_events order by id desc limit 250')],
   'batches':[dict(x) for x in c.execute('select * from batches order by started_at desc limit 20')],
   'changes':[dict(x) for x in c.execute('select * from changes order by id desc limit 80')],
   'blocked':[dict(x) for x in c.execute('select * from blocked_hosts order by host')],
   'registry':json.loads(reg[0]) if reg else None,'demo':os.environ.get('CGT_DEMO')=='1'}
def background(mode):
 try:
  result=execute(mode);render();JOB['result']={'status':result['status'],'batch':result['batch']}
 except Exception as e:JOB['result']={'status':'failed','error':str(e)}
 finally:JOB['running']=False
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def allowed(self,post=False):
  host=self.headers.get('Host','');expected={'127.0.0.1:'+str(self.server.server_port),'localhost:'+str(self.server.server_port)}
  if host not in expected:return False
  if post:
   origin=self.headers.get('Origin')
   if origin and origin not in {'http://'+h for h in expected}:return False
   if self.headers.get('Sec-Fetch-Site')=='cross-site':return False
   if self.headers.get('Content-Type','').split(';')[0]!='application/json':return False
  return True
 def send(self,status,data,ctype='application/json'):
  raw=json.dumps(data).encode() if ctype=='application/json' else data
  if ctype.startswith('text/html') and urlparse(self.path).path not in {'/home','/accounts','/sites','/delivery','/reports'}:raw=polish_html(raw,urlparse(self.path).path)
  self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY');self.end_headers();self.wfile.write(raw)
 def do_GET(self):
  if not self.allowed():return self.send(403,{'error':'Loopback origin required'})
  path=urlparse(self.path).path
  if path in {'/home','/accounts','/sites','/delivery','/reports'}:return self.send(200,(ROOT/'workspace.html').read_bytes(),'text/html; charset=utf-8')
  if path=='/workspace.css':return self.send(200,(ROOT/'workspace.css').read_bytes(),'text/css; charset=utf-8')
  if path=='/workspace.js':return self.send(200,(ROOT/'workspace.js').read_bytes(),'application/javascript; charset=utf-8')
  if path=='/api/delivery':
   try:return self.send(200,delivery.state())
   except Exception:return self.send(500,{'error':'Local delivery source unavailable. No checklist ready.'})
  if path=='/operations':return self.send(200,(ROOT/'operations.html').read_bytes(),'text/html; charset=utf-8')
  if path=='/api/operations':
   try:return self.send(200,operations.work_state())
   except Exception:return self.send(500,{'error':'Local operations sources unavailable. No records ready.'})
  if path=='/api/operations/snapshot':
   try:return self.send(200,operations.get_snapshot(parse_qs(urlparse(self.path).query).get('id',[''])[0]))
   except ValueError as e:return self.send(400,{'error':str(e)})
  if path=='/ui.css':return self.send(200,(ROOT/'ui.css').read_bytes(),'text/css; charset=utf-8')
  if path=='/context-links.js':return self.send(200,(ROOT/'context-links.js').read_bytes(),'application/javascript; charset=utf-8')
  if path=='/form-safety.js':return self.send(200,(ROOT/'form-safety.js').read_bytes(),'application/javascript; charset=utf-8')
  if path=='/ui.js':return self.send(200,(ROOT/'ui.js').read_bytes(),'application/javascript; charset=utf-8')
  if path=='/':return self.send(200,(ROOT/'index.html').read_bytes(),'text/html; charset=utf-8')
  if path=='/dashboard':return self.send(200,(ROOT/'dashboard.html').read_bytes(),'text/html; charset=utf-8')
  if path=='/api/dashboard':
   try:return self.send(200,dashboard_state())
   except Exception:return self.send(500,{'error':'Overview source unavailable or incompatible. No data was changed.'})
  if path=='/report':return self.send(200,(ROOT/'report.html').read_bytes(),'text/html; charset=utf-8')
  if path=='/api/report':
   try:return self.send(200,weekly_report(parse_qs(urlparse(self.path).query).get('week',[None])[0]))
   except ValueError as e:return self.send(400,{'error':str(e)})
   except Exception:return self.send(500,{'error':'Report source unavailable or incompatible. No data was changed. Check the local report log.'})
  if path=='/replies':return self.send(200,(ROOT/'replies.html').read_bytes(),'text/html; charset=utf-8')
  if path=='/api/replies':return self.send(200,reply_state())
  if path=='/crm':return self.send(200,(ROOT/'crm.html').read_bytes(),'text/html; charset=utf-8')
  if path=='/api/crm':
   try:return self.send(200,crm_state(parse_qs(urlparse(self.path).query).get('space',['research'])[0]))
   except ValueError as e:return self.send(400,{'error':str(e)})
  if path=='/reviews':return self.send(200,(ROOT/'reviews.html').read_bytes(),'text/html; charset=utf-8')
  if path=='/api/reviews':return self.send(200,review_state())
  if path=='/sample-map':return self.send(200,(ROOT/'sample-map.html').read_bytes(),'text/html; charset=utf-8')
  if path=='/sample-map.pdf':return self.send(200,(ROOT/'sample-map.pdf').read_bytes(),'application/pdf')
  if path=='/committee':return self.send(200,(ROOT/'committee.html').read_bytes(),'text/html; charset=utf-8')
  if path=='/api/committee':return self.send(200,committee_state())
  if path=='/hospitals':return self.send(200,(ROOT/'hospitals.html').read_bytes(),'text/html; charset=utf-8')
  if path=='/api/hospitals':return self.send(200,hospital_state())
  if path=='/api/state':return self.send(200,state())
  if path=='/api/outreach':return self.send(200,outreach_state())
  if path=='/api/fit':return self.send(200,fit_state())
  if path=='/api/job':return self.send(200,JOB)
  return self.send(404,{'error':'Not found'})
 def do_POST(self):
  if not self.allowed(True):return self.send(403,{'error':'Local JSON request required'})
  try:
   length=int(self.headers.get('Content-Length','0'))
   if length>20000:raise ValueError('Request too large')
   body=json.loads(self.rfile.read(length));path=urlparse(self.path).path
   if path=='/api/delivery':return self.send(200,delivery.save(body))
   if path=='/api/operations/plan':return self.send(200,operations.save_plan(body))
   if path=='/api/operations/snapshot':return self.send(200,operations.create_snapshot(body))
   if path=='/api/replies':return self.send(200,save_reply(body))
   if path=='/api/crm':return self.send(200,save_crm(body))
   if path=='/api/reviews':return self.send(200,save_review(body))
   if path=='/api/outreach':return self.send(200,save_outreach(body))
   if path=='/api/committee':return self.send(200,save_committee(body))
   if path=='/api/hospitals':return self.send(200,save_hospital(body))
   if path=='/api/work':return self.send(200,save_work(body))
   if path=='/api/run':
    return self.send(403,{'error':'Offline fictional public demo. External refresh is disabled in this candidate.'})
   return self.send(404,{'error':'Not found'})
  except RuntimeError as e:return self.send(409,{'error':str(e)})
  except (ValueError,KeyError,TypeError) as e:return self.send(400,{'error':str(e)})
  except Exception:return self.send(500,{'error':'Local save failed; no success was recorded. Inspect the local log.'})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8080);a=p.parse_args();migrate();migrate_hospitals();migrate_committee();migrate_outreach();migrate_reviews();migrate_crm();migrate_replies();render()
 server=ThreadingHTTPServer(('127.0.0.1',a.port),Handler);print(f'Local-only app: http://127.0.0.1:{a.port}/home',flush=True)
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:server.server_close()
