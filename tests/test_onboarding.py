import unittest
from support import LiveServer

class Onboarding(unittest.TestCase):
 def setUp(self):self.s=LiveServer();self.token=self.s.login()
 def tearDown(self):self.s.close()
 def get(self):
  code,data,_=self.s.request('/api/v5/onboarding',token=self.token);self.assertEqual(code,200);return {r['key']:r for r in data['steps']}
 def save(self,key,status='Goedgekeurd',code=200,**extra):
  row=self.get()[key]
  actual,data,_=self.s.request('/api/v5/onboarding/'+key,'PUT',{'version':row['version'],'status':status,'owner':'Fictieve acceptant','evidence':'Fictief acceptatieverslag',**extra},self.token)
  self.assertEqual(actual,code,data);return data
 def test_explicit_evidence_dependencies_revoke_restart(self):
  self.assertTrue(all(r['status']=='Open' for r in self.get().values()))
  self.save('golive',code=409);self.save('sources',code=400,evidence='')
  for key in ('sources','exports','validated','mapping','trial','reconciliation','workflows','accounting','final','golive'):self.save(key)
  self.assertTrue(self.get()['golive']['completed_at'])
  self.s.stop();self.s.start();self.assertEqual(self.get()['golive']['status'],'Goedgekeurd')
  self.save('exports','In uitvoering')
  rows=self.get();self.assertEqual(rows['golive']['status'],'Open');self.assertIsNone(rows['golive']['completed_at']);self.assertEqual(rows['accounting']['status'],'Goedgekeurd');self.assertEqual(rows['sources']['status'],'Goedgekeurd')
  code,data,_=self.s.request('/api/v5/onboarding/report',token=self.token);self.assertEqual(code,200);self.assertIn(b'Fictieve acceptant',data)
 def test_authorization_and_stale_version(self):
  row=self.get()['sources'];self.save('sources')
  code,_,_=self.s.request('/api/v5/onboarding/sources','PUT',{'version':row['version'],'status':'Open'},self.token);self.assertEqual(code,409)
  employee=self.s.login('Bart van Aalde','Amocean2!')
  for path,method,body in [('/api/v5/onboarding','GET',None),('/api/v5/onboarding/report','GET',None),('/api/v5/onboarding/sources','PUT',{})]:
   code,_,_=self.s.request(path,method,body,employee);self.assertEqual(code,403)
