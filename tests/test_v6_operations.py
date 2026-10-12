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
 def test_contract_locations_renewal_and_workorder_constraints(self):
  status,customer,_=self.s.request('/api/v5/entities/customers','POST',{'name':'Fictieve contractklant'},self.admin);self.assertEqual(status,201)
  locations=[]
  for name in ('Vestiging A','Vestiging B'):
   status,obj,_=self.s.request('/api/v5/entities/objects','POST',{'name':name,'customer_id':customer['id']},self.admin);self.assertEqual(status,201);locations.append(obj)
  status,c,_=self.s.request('/api/v5/entities/contracts','POST',{'name':'Fictief contract','customer_id':customer['id'],'object_id':locations[0]['id'],'monthly_value':'1000','start_date':'2030-01-01','end_date':'2030-12-31','status':'Actief'},self.admin);self.assertEqual(status,201,c)
  status,d,_=self.s.request('/api/v5/contracts/'+str(c['id'])+'/locations','PUT',{'version':c['version'],'locations':[{'object_id':x['id'],'frequency':'Wekelijks'} for x in locations]},self.admin);self.assertEqual(status,200,d)
  work=self.req('workorders',{'contract_id':c['id'],'object_id':locations[1]['id'],'description':'Fictief contractwerk','date':'2030-06-01','start_time':'08:00','end_time':'12:00'});self.assertEqual(work['contract_id'],c['id'])
  self.req('workorders',{'contract_id':c['id'],'object_id':1,'description':'Verkeerde klant','date':'2030-06-01','start_time':'08:00','end_time':'12:00'},status=409)
  self.req('workorders',{'contract_id':c['id'],'object_id':locations[1]['id'],'description':'Buiten looptijd','date':'2031-06-01','start_time':'08:00','end_time':'12:00'},status=409)
  d=self.req('contracts/'+str(c['id'])+'/decision',{'action':'renew','version':d['contract']['version'],'reason':'Fictieve overeenkomst','end_date':'2031-12-31','renewal_date':'2031-11-01'});self.assertEqual(d['contract']['end_date'],'2031-12-31');self.assertEqual(d['events'][0]['action'],'renew')
  self.req('contracts/'+str(c['id']),token=self.emp,status=403)
  report=self.req('reports/management?from=2030-01-01&to=2030-12-31&customer_id='+str(customer['id']));self.assertEqual(report['contracts'][0]['workorders'],1);self.assertEqual(report['customers'][0]['workorders'],1);self.assertEqual(report['finance']['total'],'0.00')
  self.req('reports/management',token=self.emp,status=403)
 def test_legacy_pagination_search_and_employee_scope(self):
  with sqlite3.connect(self.s.db) as c:
   c.executemany("INSERT INTO customers(name,status) VALUES(?,'Actief')",[(f'Fictieve paginaklant {i}',) for i in range(75)])
   c.execute("INSERT INTO hours(employee_id,date,hours,status) VALUES('999','2030-01-01','1','Ingediend')")
  code,first,_=self.s.request('/api/records/customers?limit=50&offset=0',token=self.admin);self.assertEqual(code,200);self.assertEqual(len(first['items']),50);self.assertEqual(first['total'],76)
  second=self.s.request('/api/records/customers?limit=50&offset=50',token=self.admin)[1];self.assertEqual(len(second['items']),26);self.assertFalse({x['id'] for x in first['items']}&{x['id'] for x in second['items']})
  found=self.s.request('/api/records/customers?limit=50&q=paginaklant%2074',token=self.admin)[1];self.assertEqual(found['total'],1)
  own=self.s.request('/api/records/hours?limit=50',token=self.emp)[1];self.assertTrue(all(x['employee_id']=='1' for x in own['items']))
