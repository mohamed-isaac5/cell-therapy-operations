"""Local-only backup, restore drill and curated copy. Never overwrite a folder."""
from pathlib import Path
import argparse,sqlite3,hashlib,json,shutil,datetime
ROOT=Path(__file__).resolve().parent
DATABASES=['gtm.db','crm-simulation.db','replies-simulation.db','operations-local.db']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(p):
 with sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True) as c:
  if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Integrity failure: '+p.name)
def backup(destination):
 d=Path(destination);d.mkdir(parents=True,exist_ok=False);manifest={}
 for name in DATABASES:
  p=ROOT/name
  if not p.exists():continue
  with sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True) as a,sqlite3.connect(d/name) as b:a.backup(b)
  check(d/name);manifest[name]=sha(d/name)
 (d/'backup-manifest.json').write_text(json.dumps(dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=manifest,limits='Sequential per-file SQLite backups. Stop editing first; not an atomic cross-file capture.'),indent=2));return manifest

def restore_check(source):
 import tempfile
 s=Path(source);manifest=json.loads((s/'backup-manifest.json').read_text())['files']
 with tempfile.TemporaryDirectory() as t:
  for name,digest in manifest.items():
   if name not in DATABASES or sha(s/name)!=digest:raise ValueError('Backup hash mismatch')
   shutil.copy2(s/name,Path(t)/name);check(Path(t)/name)
 return dict(passed=True,files=len(manifest),restored_to='Temporary directory; originals untouched',limits='Integrity and byte-copy drill, not full application disaster-recovery certification.')

def bundle(destination):
 d=Path(destination);d.mkdir(parents=True,exist_ok=False);included=[]
 for p in ROOT.iterdir():
  if not p.is_file() or p.suffix not in {'.py','.html','.js','.css','.json','.pdf','.md','.txt'}:continue
  if p.name.startswith(('test-','ui-','step','tests-')) or p.name.endswith(('-results.txt','-results.json')):continue
  if p.suffix=='.txt' and p.name!='requirements.txt':continue
  shutil.copy2(p,d/p.name);included.append(p.name)
 for name in ['committee_sources','hospital_sources','source_cache']:
  if (ROOT/name).exists():shutil.copytree(ROOT/name,d/name);included.append(name+'/')
 # Required historical regression fixtures, not live application data.
 if (ROOT/'step6-backup.db').exists():shutil.copy2(ROOT/'step6-backup.db',d/'step6-backup.db');included.append('step6-backup.db (regression fixture)')
 fixture=ROOT/'archive/prototype/core.py'
 if fixture.exists():
  (d/'archive/prototype').mkdir(parents=True);shutil.copy2(fixture,d/'archive/prototype/core.py');included.append('archive/prototype/core.py (guarded regression fixture)')
 for name in DATABASES:
  if not (ROOT/name).exists():continue
  with sqlite3.connect((ROOT/name).resolve().as_uri()+'?mode=ro',uri=True) as a,sqlite3.connect(d/name) as b:a.backup(b)
  check(d/name);included.append(name)
 (d/'LOCAL-BUNDLE-MANIFEST.json').write_text(json.dumps(dict(files=included,limits='Local review only. Source-data redistribution and code licensing remain open. No publication. Videos, logs, unrelated archive and old backup DBs excluded; two required historical regression fixtures retained.'),indent=2));return dict(destination=str(d),root_items=len(included))
if __name__=='__main__':
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
 for name in ['backup','bundle']:sub.add_parser(name).add_argument('--destination',required=True)
 sub.add_parser('restore-check').add_argument('--source',required=True);a=p.parse_args()
 print(json.dumps(backup(a.destination) if a.command=='backup' else bundle(a.destination) if a.command=='bundle' else restore_check(a.source),indent=2))
