import unittest,sqlite3
from support import LiveServer
class ServicePlans(unittest.TestCase):
 def setUp(self):self.s=LiveServer();self.token=self.s.login()
 def tearDown(self):self.s.close()
 def req(self,path,body=None,status=200,method=None,token=None):
  code,data,_=self.s.request('/api/v5/'+path,method or ('POST' if body is not None else 'GET'),body,token or self.token);self.assertEqual(code,status,data);return data
 def test_school_budget_calendar_tasks_idempotency_and_restart(self):
  demo=self.req('school-demo',{});cid=demo['contract']['id'];weekly,glass=demo['items'];self.assertEqual(weekly['weekly_hours'],'11.5');self.assertEqual(weekly['agreed_hours'],'460.0');self.assertEqual(weekly['selected_hours'],'460.0');self.assertEqual(glass['definition']['dates'],[])
  self.assertEqual(self.req('school-demo',{})['contract']['id'],cid)
  slots={str(i):{'start_time':'16:00','end_time':end,'capacity':1} for i,end in enumerate(['18:00','18:00','19:00','18:00','18:30'])}
  path=f'contracts/{cid}/services/{weekly["id"]}/generate';r=self.req(path,{'version':1,'slots':slots});self.assertEqual(len(r['created']),200)
  self.assertEqual(self.req(path,{'version':1,'slots':slots}),{'created':[],'existing':200})
  with sqlite3.connect(self.s.db) as c:
   self.assertEqual(c.execute('SELECT COUNT(*) FROM checklist WHERE workorder_id IN (SELECT workorder_id FROM contract_service_jobs)').fetchone()[0],400)
   self.assertEqual(c.execute('SELECT COUNT(*) FROM shifts WHERE workorder_id IN (SELECT workorder_id FROM contract_service_jobs)').fetchone()[0],0)
   self.assertEqual(c.execute('SELECT COUNT(*) FROM hours WHERE workorder_id IN (SELECT workorder_id FROM contract_service_jobs)').fetchone()[0],0)
  self.req(f'contracts/{cid}/services/{glass["id"]}/generate',{'version':1,'slots':{}},status=409)
  self.s.stop();self.s.start();self.assertEqual(len(self.req(f'contracts/{cid}/services')['items'][0]['jobs']),200)
 def test_exceptions_versions_atomic_error_and_rights(self):
  demo=self.req('school-demo',{});cid=demo['contract']['id'];r=demo['items'][0];d=r['definition'];d['exceptions']=[d['weeks'][0]]
  updated=self.req(f'contracts/{cid}/services/{r["id"]}',{'name':r['name'],'version':1,'definition':d},method='PUT')['items'][0];self.assertEqual(updated['selected_hours'],'458.0')
  self.req(f'contracts/{cid}/services/{r["id"]}',{'name':r['name'],'version':1,'definition':d},method='PUT',status=409)
  slots={'1':{'start_time':'16:00','end_time':'18:00','capacity':1}}
  self.req(f'contracts/{cid}/services/{r["id"]}/generate',{'version':2,'slots':slots},status=400)
  self.assertEqual(self.req(f'contracts/{cid}/services')['items'][0]['jobs'],[])
  emp=self.s.login('Bart van Aalde','Amocean2!');self.req(f'contracts/{cid}/services',token=emp,status=403);self.req('school-demo',{},token=emp,status=403)
 def test_periodic_dates_explicit_not_automatic_quarters(self):
  demo=self.req('school-demo',{});cid=demo['contract']['id'];r=demo['items'][1];year=demo['contract']['start_date'][:4];d=r['definition'];d['dates']=[year+'-02-03',year+'-05-19',year+'-09-07',year+'-11-24']
  self.req(f'contracts/{cid}/services/{r["id"]}',{'name':r['name'],'version':1,'definition':d},method='PUT')
  slots={day:{'start_time':'08:00','end_time':'09:00','capacity':2} for day in d['dates']};out=self.req(f'contracts/{cid}/services/{r["id"]}/generate',{'version':2,'slots':slots});self.assertEqual(len(out['created']),4)
  with sqlite3.connect(self.s.db) as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM checklist WHERE workorder_id=?',(out['created'][0],)).fetchone()[0],3)
