import datetime as dt,json,sqlite3,unittest
from zoneinfo import ZoneInfo
from support import LiveServer
from services.finance import draft_number,validate_numbering
from domain import Problem
class V6Operations(unittest.TestCase):
 def setUp(self):self.s=LiveServer();self.admin=self.s.login();self.emp=self.s.login('Bart van Aalde','Amocean2!')
 def tearDown(self):self.s.close()
 def req(self,path,body=None,token=None,status=200):
  code,data,_=self.s.request('/api/v5/'+path,'POST' if body is not None else 'GET',body,token or self.admin);self.assertEqual(code,status,data);return data
 def test_clock_persistence_ownership_duplicate_and_actual_hours(self):
  work=self.req('workorders',{'object_id':1,'description':'Fictieve klokopdracht','date':'2030-04-01','start_time':'08:00','end_time':'12:00'})
  self.req('shifts',{'object_id':1,'employee_id':1,'date':work['date'],'start_time':'08:00','end_time':'12:00','workorder_id':work['id']})
  for state in ('Gepland','Toegewezen','In uitvoering'):work=self.req('workorders/'+str(work['id'])+'/transition',{'version':work['version'],'state':state})
  clock=self.req('clock',{'workorder_id':work['id']},self.emp)
  self.req('clock',{'workorder_id':work['id']},self.emp,status=409)
  self.req('clock',{'workorder_id':work['id'],'employee_id':999},self.emp,status=403)
  self.s.stop();self.s.start();self.assertEqual(self.req('clock',token=self.emp)[0]['id'],clock['id'])
  # Gecontroleerde fictieve start in het verleden; geen minuten wachten in tests.
  start=(dt.datetime.now(ZoneInfo('Europe/Amsterdam'))-dt.timedelta(hours=2)).isoformat(timespec='seconds')
  with sqlite3.connect(self.s.db) as c:c.execute('UPDATE time_clocks SET starts_at=? WHERE id=?',(start,clock['id']))
  closed=self.req('clock/'+str(clock['id']),{'version':1,'break_minutes':30},self.emp);self.assertEqual(closed['state'],'Afgesloten')
  with sqlite3.connect(self.s.db) as c:self.assertEqual(c.execute('SELECT hours FROM hours WHERE id=?',(closed['hours_id'],)).fetchone()[0],'1.50')
  self.req('clock/'+str(clock['id']),{'version':1,'break_minutes':30},self.emp,status=409)
 def test_configurable_draft_numbers_rollback_collision_and_no_fiscal_activation(self):
  with sqlite3.connect(self.s.db) as c:
   profile={'enabled':True,'prefix':'TEST','width':5};validate_numbering(profile)
   c.execute("INSERT INTO settings(key,value) VALUES('invoice_numbering',?)",(json.dumps(profile),));c.commit()
   first=draft_number(c,1);self.assertTrue(first.startswith('CONCEPT-TEST-'));self.assertTrue(first.endswith('00001'));c.rollback()
   self.assertEqual(draft_number(c,1),first);second=draft_number(c,2);self.assertTrue(second.endswith('00002'));c.commit()
  with self.assertRaises(Problem):validate_numbering({'enabled':True,'prefix':'<script>','width':5})
