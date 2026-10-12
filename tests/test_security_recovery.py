import base64,json,os,sqlite3,tempfile,time,unittest,zipfile
from pathlib import Path
from support import LiveServer
from services import mfa
from manage import backup,restore

class SecurityRecovery(unittest.TestCase):
 def setUp(self):self.s=LiveServer();self.token=self.s.login()
 def tearDown(self):self.s.close()
 def request(self,path,method='GET',body=None,status=200,token=True):
  code,result,_=self.s.request('/api/'+path,method,body,self.token if token else None);self.assertEqual(code,status,result);return result
 def test_mfa_enrollment_login_replay_session_invalidation(self):
  self.request('security/mfa/status',status=404)
  setup=self.request('v5/security/mfa/setup','POST',{'password':'Amocean1!'})
  current=int(time.time()//30);code=mfa.code(setup['secret'],current)
  self.request('v5/security/mfa/enable','POST',{'password':'Amocean1!','code':code})
  self.request('me',status=401)
  self.request('login','POST',{'username':'Roefs','password':'Amocean1!'},401,False)
  self.request('login','POST',{'username':'Roefs','password':'Amocean1!','code':code},401,False)
  login=self.request('login','POST',{'username':'Roefs','password':'Amocean1!','code':mfa.code(setup['secret'],current+1)},token=False);self.assertIn('token',login)
  self.request('login','POST',{'username':'Roefs','password':'Amocean1!','code':mfa.code(setup['secret'],current+1)},401,False)
  with sqlite3.connect(self.s.db) as c:self.assertEqual(c.execute('SELECT password_iterations FROM users WHERE id=1').fetchone()[0],600000)
 def test_full_backup_files_restore_private_and_sessions_revoked(self):
  self.request('v5/files','POST',{'name':'fictief.txt','category':'Test','customer_id':1,'content':base64.b64encode(b'Fictieve bijlage').decode()})
  with tempfile.TemporaryDirectory() as d:
   archive=Path(d)/'private.zip';target=Path(d)/'restored';backup(self.s.db,archive);restore(archive,target)
   with sqlite3.connect(target/'roefs.db') as c:
    self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok');self.assertEqual(c.execute('SELECT COUNT(*) FROM sessions').fetchone()[0],0);key=c.execute('SELECT storage_key FROM files').fetchone()[0]
   self.assertEqual((target/'uploads'/key).read_bytes(),b'Fictieve bijlage')
   if os.name!='nt':self.assertEqual(archive.stat().st_mode&0o777,0o600)
   with self.assertRaises(ValueError):restore(archive,target)
 def test_restore_rejects_traversal_and_corruption(self):
  with tempfile.TemporaryDirectory() as d:
   archive=Path(d)/'bad.zip'
   with zipfile.ZipFile(archive,'w') as z:z.writestr('../escape','bad')
   with self.assertRaises(ValueError):restore(archive,Path(d)/'restored')
 def test_weak_password_and_inactive_connectors(self):
  self.request('users','POST',{'username':'Fictief zwak','password':'123456789','role':'admin'},400)
  sync=self.request('v5/sync');self.assertEqual(sync['connections'],[])
