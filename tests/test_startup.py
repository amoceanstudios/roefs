import json,os,sqlite3,subprocess,sys,tempfile,unittest
from pathlib import Path
from support import ROOT
class Startup(unittest.TestCase):
 def test_repeatable_start_and_backup(self):
  with tempfile.TemporaryDirectory() as d:
   env={**os.environ,'ROEFS_DB':d+'/roefs.db','PORT':'19771','ROEFS_DEMO_GATE':''}
   for _ in range(2):
    r=subprocess.run([sys.executable,str(ROOT/'start.py'),'--check','--quiet'],env=env,capture_output=True,text=True,timeout=20);self.assertEqual(r.returncode,0,r.stderr)
   accounts=json.loads((Path(d)/'demo-accounts.json').read_text());self.assertGreaterEqual(len(accounts['ROEFS_ADMIN_PASSWORD']),20)
   backups=list((Path(d)/'backups').glob('*.db'));self.assertEqual(len(backups),1)
   with sqlite3.connect(backups[0]) as c:self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')
 def test_original_database_migration(self):
  # Exact oud schema, bestaande fictieve namen en gegevens blijven behouden.
  with tempfile.TemporaryDirectory() as d:
   db=Path(d)/'old.db'
   with sqlite3.connect(db) as c:
    c.execute('CREATE TABLE users(id INTEGER PRIMARY KEY,username TEXT UNIQUE,salt TEXT,password_hash TEXT,role TEXT)')
    c.execute("INSERT INTO users VALUES(1,'Fictief oud account','00','oude-hash','admin')")
   env={**os.environ,'ROEFS_DB':str(db),'PORT':'19772','ROEFS_DEMO_GATE':''}
   r=subprocess.run([sys.executable,str(ROOT/'start.py'),'--check','--quiet'],env=env,capture_output=True,text=True,timeout=20);self.assertEqual(r.returncode,0,r.stderr)
   with sqlite3.connect(db) as c:
    self.assertEqual(c.execute('SELECT username FROM users').fetchone()[0],'Fictief oud account');self.assertEqual(c.execute('SELECT COUNT(*) FROM users').fetchone()[0],1)
    self.assertEqual(c.execute('SELECT COUNT(*) FROM availability').fetchone()[0],0)
 def test_tunnel_start_check_reuses_existing_gate(self):
  with tempfile.TemporaryDirectory() as d:
   # --check controleert de server, niet de externe Cloudflare-verbinding.
   env={**os.environ,'ROEFS_DB':d+'/roefs.db','PORT':'19773','ROEFS_HOST':'127.0.0.1','ROEFS_DEMO_GATE':'fictieve-testtoegang','CLOUDFLARED_BIN':sys.executable}
   r=subprocess.run([sys.executable,str(ROOT/'start.py'),'--tunnel','--check','--quiet'],env=env,capture_output=True,text=True,timeout=20)
   self.assertEqual(r.returncode,0,r.stderr);self.assertNotIn('fictieve-testtoegang',r.stdout);self.assertIn('Gereed:',r.stdout)
 def test_occupied_port_fails_without_stopping_existing_server(self):
  from support import LiveServer
  existing=LiveServer()
  try:
   with tempfile.TemporaryDirectory() as d:
    env={**os.environ,'ROEFS_DB':d+'/new.db','PORT':str(existing.port),'ROEFS_HOST':'127.0.0.1','ROEFS_DEMO_GATE':''}
    r=subprocess.run([sys.executable,str(ROOT/'start.py'),'--check','--quiet'],env=env,capture_output=True,text=True,timeout=20)
    self.assertNotEqual(r.returncode,0);self.assertEqual(existing.request('/api/health')[0],200)
  finally:existing.close()
if __name__=='__main__':unittest.main(verbosity=2)
