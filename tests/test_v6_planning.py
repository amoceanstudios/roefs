import sqlite3,unittest
from support import LiveServer
from services.labor_rules import DEMO
class V6Planning(unittest.TestCase):
 def setUp(self):self.s=LiveServer();self.token=self.s.login()
 def tearDown(self):self.s.close()
 def req(self,path,body=None,method=None,status=200):
  code,result,_=self.s.request('/api/v5/'+path,method or ('POST' if body is not None else 'GET'),body,self.token);self.assertEqual(code,status,result);return result
 def template(self):return {'object_id':1,'employee_id':1,'start_time':'08:00','end_time':'12:00','status':'Gepland'}
 def series(self):return {'title':'Fictieve meerdaagse reiniging','start':'2030-01-07','end':'2030-01-11','weekdays':[0,1,2,3,4],'exceptions':['2030-01-09'],'template':self.template()}
 def test_series_exceptions_cancel_restore_versions_restart(self):
  result=self.req('planning/series',self.series());self.assertEqual(len(result['items']),4)
  self.assertNotIn('2030-01-09',[x['date'] for x in result['items']])
  body={'action':'cancel','version':result['version'],'reason':'Fictieve sluiting','versions':{str(x['id']):x['version'] for x in result['items']}}
  cancelled=self.req('planning/series/'+str(result['id']),body);self.assertTrue(all(x['status']=='Geannuleerd' for x in cancelled['items']))
  self.req('planning/series/'+str(result['id']),body,status=409)
  restored=self.req('planning/series/'+str(result['id']),{'action':'restore','version':cancelled['version'],'reason':'Locatie heropend'});self.assertTrue(all(x['status']=='Gepland' for x in restored['items']))
  self.s.stop();self.s.start();self.assertEqual(len(self.req('planning/series')['items'][0]['items']),4)
 def test_series_all_or_nothing_conflict_and_safe_restore(self):
  self.req('shifts',{**self.template(),'date':'2030-01-10'})
  self.req('planning/series',self.series(),status=409)
  self.assertEqual(self.req('planning/series')['items'],[])
  with sqlite3.connect(self.s.db) as c:self.assertEqual(c.execute("SELECT COUNT(*) FROM shifts WHERE date='2030-01-07'").fetchone()[0],0)
 def test_configured_rules_daily_weekly_rest_break_and_legacy(self):
  self.req('settings',{'labor_rules':{**DEMO,'enabled':True}},'PUT')
  self.req('shifts',{**self.template(),'date':'2030-02-04','end_time':'16:00'},status=409)
  first=self.req('shifts',{**self.template(),'date':'2030-02-04','end_time':'16:00','break_minutes':30});self.assertEqual(first['break_minutes'],30)
  self.req('shifts',{**self.template(),'date':'2030-02-05','start_time':'01:00','end_time':'05:00'},status=409)
  self.req('shifts',{**self.template(),'date':'2030-02-04','start_time':'17:00','end_time':'21:00'},status=409)
  self.req('settings',{'labor_rules':{**DEMO,'enabled':True,'weekly_hours':8}},'PUT')
  self.req('shifts',{**self.template(),'date':'2030-02-06'},status=409)
  code,_,_=self.s.request('/api/records/shifts','POST',{**self.template(),'date':'2030-02-07'},self.token);self.assertEqual(code,409)
 def test_series_employee_denied(self):
  self.token=self.s.login('Bart van Aalde','Amocean2!');self.req('planning/series',self.series(),status=403)

 def test_closed_workorder_shift_cannot_be_cancelled_via_planning(self):
  work=self.req('workorders',{'object_id':1,'description':'Fictieve afgesloten opdracht','date':'2030-08-05','start_time':'08:00','end_time':'12:00'})
  shift=self.req('shifts',{**self.template(),'date':work['date'],'workorder_id':work['id']})
  with sqlite3.connect(self.s.db) as c:c.execute("UPDATE workorders SET workflow='Goedgekeurd' WHERE id=?",(work['id'],))
  self.req('shifts/'+str(shift['id']),{'version':shift['version'],'status':'Geannuleerd'},'PUT',409)
 def test_linked_resize_atomic_parent_and_shift_conflict_rollback(self):
  work=self.req('workorders',{'object_id':1,'description':'Fictief resizewerk','date':'2030-09-02','start_time':'08:00','end_time':'12:00'})
  shift=self.req('shifts',{**self.template(),'date':work['date'],'workorder_id':work['id']})
  self.req('shifts',{**self.template(),'date':work['date'],'start_time':'12:30','end_time':'14:00'})
  body={'version':shift['version'],'work_version':work['version'],'versions':{str(shift['id']):shift['version']},'end_time':'13:00'}
  self.req('planning/resize/'+str(shift['id']),body,status=409)
  self.assertEqual(self.req('workorders/'+str(work['id']))['workorder']['end_time'],'12:00')
  result=self.req('planning/resize/'+str(shift['id']),{**body,'end_time':'12:15'});self.assertEqual(result['items'][0]['end_time'],'12:15');self.assertEqual(result['workorder']['end_time'],'12:15')
  self.req('planning/resize/'+str(shift['id']),body,status=409)
