import concurrent.futures,sqlite3,time,unittest
from support import LiveServer
from services import mfa

class V6Security(unittest.TestCase):
 def setUp(self):self.s=LiveServer();self.token=self.s.login()
 def tearDown(self):self.s.close()
 def request(self,path,body=None,token=None):return self.s.request('/api/'+path,'POST' if body is not None else 'GET',body,token)
 def enroll(self):
  status,setup,_=self.request('v5/security/mfa/setup',{'password':'Amocean1!'},self.token);self.assertEqual(status,200)
  status,result,_=self.request('v5/security/mfa/enable',{'password':'Amocean1!','code':mfa.code(setup['secret'],int(time.time()//30))},self.token);self.assertEqual(status,200)
  return setup,result['recovery_codes']
 def login_body(self,code):return {'username':'Roefs','password':'Amocean1!','code':code}
 def test_recovery_hashed_one_time_concurrent_and_persistent(self):
  _,codes=self.enroll();self.assertEqual(len(set(codes)),10)
  with sqlite3.connect(self.s.db) as c:
   saved=c.execute('SELECT digest,used_at FROM mfa_recovery_codes').fetchall();self.assertEqual(len(saved),10)
   self.assertFalse(any(code in str(saved) for code in codes))
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
   results=list(pool.map(lambda _:self.request('login',self.login_body(codes[0])),range(2)))
  self.assertEqual(sorted(r[0] for r in results),[200,401])
  token=next(r[1]['token'] for r in results if r[0]==200)
  self.assertEqual(self.request('v5/security/mfa/status',token=token)[1]['recovery_remaining'],9)
  self.s.stop();self.s.start()
  self.assertEqual(self.request('login',self.login_body(codes[0]))[0],401)
  with sqlite3.connect(self.s.db) as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM mfa_recovery_codes WHERE used_at IS NOT NULL').fetchone()[0],1)
  self.assertEqual(self.request('login',self.login_body(codes[1]))[0],200)
  self.assertEqual(self.request('me',token=token)[0],401)
 def test_recovery_requires_password_and_rotation_invalidates_old_codes(self):
  setup,codes=self.enroll()
  bad=self.login_body(codes[0]);bad['password']='Onjuist';self.assertEqual(self.request('login',bad)[0],401)
  status,login,_=self.request('login',self.login_body(codes[0]));self.assertEqual(status,200)
  token=login['token'];body={'password':'Amocean1!','code':mfa.code(setup['secret'],int(time.time()//30)+1)}
  status,result,_=self.request('v5/security/mfa/recovery',body,token);self.assertEqual(status,200,result)
  self.assertEqual(self.request('me',token=token)[0],401)
  self.assertEqual(self.request('login',self.login_body(codes[1]))[0],401)
  self.assertEqual(self.request('login',self.login_body(result['recovery_codes'][0]))[0],200)
 def test_account_limit_persisted_in_database(self):
  for _ in range(10):self.assertEqual(self.request('login',{'username':'Roefs','password':'Onjuist'})[0],401)
  self.s.stop();self.s.start()
  self.assertEqual(self.request('login',{'username':'Roefs','password':'Amocean1!'})[0],429)
  with sqlite3.connect(self.s.db) as c:self.assertEqual(c.execute('SELECT attempts FROM auth_attempts WHERE username=?',('Roefs',)).fetchone()[0],10)
