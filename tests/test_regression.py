import base64,datetime,hashlib,json,sqlite3,sys,unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from support import LiveServer,ROOT
sys.path.insert(0,str(ROOT))
from domain import REQUIRED,STATUSES
class Regression(unittest.TestCase):
 def setUp(self):
  self.s=LiveServer();self.a=self.s.login();self.b=self.s.login('Bart van Aalde','Amocean2!');self.day=datetime.date.today().isoformat()
 def tearDown(self):self.s.close()
 def call(self,path,method='GET',data=None,token=None,status=200,**kw):
  code,body,headers=self.s.request('/api/'+path,method,data,self.a if token is None else token,**kw)
  self.assertEqual(code,status,(path,body));return body
 def create(self,m,data):return self.call('records/'+m,'POST',data,status=201)['id']
 def employee(self):return self.create('employees',{'name':'Fictieve collega','contract_hours':'32','status':'Actief'})
 def shift(self,eid='1',**kw):return {'object_id':'1','employee_id':str(eid),'date':self.day,'start_time':'12:00','end_time':'16:00','status':'Gepland',**kw}
 def test_all_modules_crud_persist_restart(self):
  modules=self.call('modules');self.assertEqual(len(modules),21)
  for m,meta in modules.items():
   with self.subTest(module=m):
    source=self.call('records/'+m)
    if m=='availability':row={'employee_id':'1','date':self.day,'start_time':'18:00','end_time':'20:00','status':'Niet beschikbaar'}
    else:row={f:source[0][f] for f in meta['fields']}
    if m=='shifts':row=self.shift()
    if m=='hours':row.update(shift_id='',hours='2')
    if m=='invoices':row['number']='TEST-UNIEK'
    rid=self.create(m,row);self.assertEqual(self.call(f'records/{m}/{rid}')['status'],row['status'])
    self.call(f'records/{m}/{rid}','PUT',{'status':row['status']})
    self.call(f'records/{m}/{rid}','DELETE');self.call(f'records/{m}/{rid}',status=404)
  rid=self.create('customers',{'name':'Fictieve bewaarklant'})
  self.s.stop();self.s.start();self.assertEqual(self.call(f'records/customers/{rid}')['name'],'Fictieve bewaarklant')
 def test_every_module_rejects_invalid_fields(self):
  for m in self.call('modules'):
   with self.subTest(module=m):self.call('records/'+m,'POST',{'unknown':'x'},status=400)
 def test_numeric_date_and_relationship_validation(self):
  for field,value in [('hours','NaN'),('hours','Infinity'),('hours','-1'),('hours','25'),('date','2026-02-30'),('employee_id','999')]:
   with self.subTest(field=field,value=value):self.call('records/hours','POST',{'employee_id':'1','date':self.day,'hours':'2',field:value},status=400)
  self.call('records/hours','POST',{'employee_id':'1','date':self.day,'hours':'2','status':'Goedgekeurrd'},status=400)
 def test_cross_customer_invoice_contract(self):
  cid=self.create('customers',{'name':'Andere fictieve klant'})
  self.call('records/invoices','POST',{'number':'FOUT','customer_id':str(cid),'contract_id':'1','amount':'10','due_date':self.day},status=400)
 def test_invoice_unique(self):
  self.call('records/invoices','POST',{'number':'CONCEPT-001','customer_id':'1','amount':'10','due_date':self.day},status=409)
 def test_delete_protects_links(self):
  for m in ['customers','objects','employees','contracts','shifts']:
   with self.subTest(module=m):self.call('records/'+m+'/1','DELETE',status=409)
 def test_no_default_data_reseed(self):
  with sqlite3.connect(self.s.db) as c:c.execute('DELETE FROM customers')
  self.s.stop();self.s.start();self.assertEqual(self.call('records/customers'),[])
 def test_rename_keeps_employee_binding(self):
  self.call('records/employees/1','PUT',{'name':'Fictieve nieuwe naam'})
  self.assertEqual(len(self.call('records/shifts',token=self.b)),1)
 def test_same_name_cannot_impersonate_employee(self):
  self.call('users','POST',{'username':'Fictieve collega','password':'EenWachtwoord123','role':'employee'},status=201)
  eid=self.employee();t=self.s.login('Fictieve collega','EenWachtwoord123');self.create('shifts',self.shift(eid))
  self.assertEqual(self.call('records/shifts',token=t),[])
 def test_link_account_explicitly(self):
  eid=self.employee();uid=self.call('users','POST',{'username':'Tweede testaccount','password':'EenWachtwoord123'},status=201)['id']
  self.call('users/link','POST',{'user_id':uid,'employee_id':eid});t=self.s.login('Tweede testaccount','EenWachtwoord123');sid=self.create('shifts',self.shift(eid))
  self.assertEqual([x['id'] for x in self.call('records/shifts',token=t)],[sid])
 def test_employee_cannot_access_other_records_or_counters(self):
  eid=self.employee();sid=self.create('shifts',self.shift(eid));self.call('records/shifts/'+str(sid),token=self.b,status=404)
  self.assertEqual(self.call('dashboard',token=self.b)['counts']['shifts'],1)
  self.call('users/link','POST',{'user_id':2,'employee_id':eid},token=self.b,status=403)
 def test_admin_endpoints_deny_employee(self):
  for route,method,data in [('users','GET',None),('audit','GET',None),('smart/overview','GET',None),('hr/profiles','GET',None),('autopilot/propose','POST',{}),('sos/assign','POST',{}),('planning/suggest','POST',{}),('cao/calculate','POST',{})]:
   with self.subTest(route=route):self.call(route,method,data,token=self.b,status=403)
 def test_account_deactivation_and_last_admin(self):
  self.call('users/update','POST',{'user_id':1,'active':False},status=409)
  self.call('users/update','POST',{'user_id':2,'active':False})
  self.call('me',token=self.b,status=401)
  self.call('login','POST',{'username':'Bart van Aalde','password':'Amocean2!'},token='',status=401)
  self.call('users/update','POST',{'user_id':2,'active':True,'password':'NieuwFictief123!'})
  t=self.s.login('Bart van Aalde','NieuwFictief123!');self.call('me',token=t)
  self.call('users/update','POST',{'user_id':1,'role':'employee'},token=t,status=403)
 def test_employee_hours_save_and_approval(self):
  rid=self.call('records/hours','POST',{'date':self.day,'hours':'1.5'},token=self.b,status=201)['id']
  self.assertEqual(self.call('records/hours/'+str(rid),token=self.b)['status'],'Ingediend')
  self.call('records/hours/'+str(rid),'PUT',{'status':'Goedgekeurd'},token=self.b,status=403)
  self.call('records/hours/'+str(rid),'PUT',{'status':'Goedgekeurd'})
  self.call('records/hours/'+str(rid),'DELETE',token=self.b,status=403)
 def test_employee_cannot_set_other_employee(self):
  eid=self.employee();self.call('records/hours','POST',{'employee_id':str(eid),'date':self.day,'hours':'1'},token=self.b,status=403)
 def test_hour_duplicate_and_24h(self):
  self.call('records/hours','POST',{'employee_id':'1','shift_id':'1','date':self.day,'hours':'2'},status=409)
  self.call('records/hours','POST',{'employee_id':'1','date':self.day,'hours':'21'},status=409)
 def test_workorder_employee_completion(self):
  self.call('records/workorders/1','PUT',{'status':'Afgerond','hours':'3','signed_by':'Fictieve medewerker'},token=self.b)
  self.assertEqual(self.call('records/workorders/1')['signed_by'],'Fictieve medewerker')
  self.call('records/workorders/1','PUT',{'description':'Overnemen'},token=self.b,status=403)
 def test_logbook_scoped(self):
  cid=self.create('customers',{'name':'Afgeschermde fictieve klant'});oid=self.create('objects',{'name':'Andere locatie','customer_id':str(cid)})
  rid=self.create('logbook',{'object_id':str(oid),'author':'Test','date':self.day,'message':'Afgeschermd'})
  self.call('records/logbook/'+str(rid),token=self.b,status=404)
  self.call('records/logbook','POST',{'object_id':str(oid),'date':self.day,'message':'test'},token=self.b,status=403)
  out=self.call('records/logbook','POST',{'object_id':'1','date':self.day,'message':'Fictieve melding'},token=self.b,status=201)
  self.assertEqual(self.call('records/logbook/'+str(out['id']))['author'],'Bart van Aalde')
 def test_availability_and_suggestions(self):
  self.call('records/availability','POST',{'date':self.day,'start_time':'12:00','end_time':'14:00','status':'Niet beschikbaar'},token=self.b,status=201)
  self.assertEqual(self.call('planning/suggest','POST',self.shift())['candidates'],[])
  self.call('records/shifts','POST',self.shift(),status=409)
 def test_available_window(self):
  self.create('availability',{'employee_id':'1','date':self.day,'start_time':'12:00','end_time':'14:00','status':'Beschikbaar'})
  self.assertEqual(len(self.call('planning/suggest','POST',self.shift(end_time='14:00'))['candidates']),1)
  self.assertEqual(self.call('planning/suggest','POST',self.shift())['candidates'],[])
 def test_leave_blocks_all_assignment_paths(self):
  eid=self.employee();self.create('leave',{'employee_id':str(eid),'start_date':self.day,'end_date':self.day,'type':'Verlof','status':'Goedgekeurd'})
  self.call('records/shifts','POST',self.shift(eid),status=409)
  self.call('sos/assign','POST',{'shift_id':1,'employee_id':eid},status=409)
  self.assertNotIn(eid,[x['id'] for x in self.call('sos/candidates','POST',{'shift_id':1})['candidates']])
  jid=self.call('autopilot/propose','POST',{'kind':'shift_replacement','source_id':1,'candidate_id':eid},status=201)['id']
  self.call('autopilot/decide','POST',{'id':jid,'decision':'approve'},status=409)
 def test_leave_after_schedule_visible_conflict(self):
  self.create('leave',{'employee_id':'1','start_date':self.day,'end_date':self.day,'type':'Ziekte','status':'Ziek'})
  self.assertEqual(self.call('planning/overview')['availability_conflicts'][0]['id'],1)
 def test_normalized_times_and_required_object(self):
  self.call('records/shifts','POST',self.shift(start_time='9:00'),status=400)
  self.call('records/shifts','POST',self.shift(object_id=''),status=400)
 def test_concurrent_overlap_atomic(self):
  with ThreadPoolExecutor(2) as pool:results=list(pool.map(lambda _:self.s.request('/api/records/shifts','POST',self.shift(),self.a)[0],range(2)))
  self.assertEqual(sorted(results),[201,409])
 def test_workflow_approve_once(self):
  jid=self.call('autopilot/propose','POST',{'kind':'workorder_from_log','source_id':1},status=201)['id']
  self.call('autopilot/decide','POST',{'id':jid,'decision':'approve'});self.call('autopilot/decide','POST',{'id':jid,'decision':'approve'},status=409)
  self.assertEqual(len(self.call('records/workorders')),2)
 def test_invoice_workflow(self):
  jid=self.call('autopilot/propose','POST',{'kind':'invoice_from_contract','source_id':1},status=201)['id']
  self.call('autopilot/decide','POST',{'id':jid,'decision':'approve'});self.assertEqual(len(self.call('records/invoices')),2)
 def test_widgets_refresh_after_mutation(self):
  before=self.call('smart/overview')['widgets']['alerts']['count'];rid=self.create('alerts',{'title':'Fictieve melding','severity':'Normaal','description':'Test','status':'Open'})
  self.assertEqual(self.call('smart/overview')['widgets']['alerts']['count'],before+1)
  self.call('records/alerts/'+str(rid),'PUT',{'status':'Afgerond'});self.assertEqual(self.call('smart/overview')['widgets']['alerts']['count'],before)
 def test_messages_isolation_and_read(self):
  self.call('messages','POST',{'subject':'Fictief','body':'Bericht'},token=self.b,status=201)
  msg=self.call('messages')[0];self.call('messages/read','POST',{'id':msg['id']});self.assertTrue(self.call('messages',token=self.b)[0]['read_at'])
  self.call('messages/read','POST',{'id':999},status=404)
 def test_malformed_bodies_and_content_type(self):
  for body in [b'[]',b'null',b'{',b'{"hours":NaN}']:
   with self.subTest(body=body):self.call('records/hours','POST',raw=body,status=400)
  self.call('records/hours','POST',raw=b'{}',headers={'Content-Type':'text/plain'},status=415)
 def test_origin_and_headers(self):
  self.call('messages','POST',{'subject':'x','body':'y'},headers={'Origin':'https://evil.invalid'},status=403)
  for path in ['/','/ui.js','/assets/amocean-mark.png']:
   status,_,h=self.s.request(path);self.assertEqual(status,200);self.assertEqual(h['X-Frame-Options'],'DENY');self.assertIn("frame-ancestors 'none'",h['Content-Security-Policy'])
 def test_session_hash_expiry_and_logout(self):
  with sqlite3.connect(self.s.db) as c:
   tokens=[x[0] for x in c.execute('SELECT token FROM sessions')];self.assertNotIn(self.a,tokens);self.assertIn(hashlib.sha256(self.a.encode()).hexdigest(),tokens)
   c.execute("UPDATE sessions SET expires='2000-01-01' WHERE token=?",(hashlib.sha256(self.b.encode()).hexdigest(),))
  self.call('me',token=self.b,status=401);self.call('logout','POST',{});self.call('me',status=401)
 def test_login_throttle(self):
  for _ in range(10):self.call('login','POST',{'username':'onbekend','password':'fout'},token='',status=401)
  self.call('login','POST',{'username':'onbekend','password':'fout'},token='',status=429)
 def test_failed_mutation_rollback(self):
  self.call('records/shifts','POST',self.shift(start_time='09:00'),status=409)
  rid=self.create('customers',{'name':'Na fout'});self.assertTrue(rid)
 def test_demo_chain_accepts_more_records(self):
  self.create('customers',{'name':'Extra fictieve klant'});self.assertTrue(all(x['ok'] for x in self.call('demo/chain')['checks']))
 def test_hr_cao_and_contracts(self):
  self.call('hr/profile','POST',{'employee_id':1,'employment_start':'2025-01-01','wage_group':1,'step':1,'notes':'Fictief'})
  result=self.call('hr/preview','POST',{'employee_id':1,'date':'2026-10-11','period':self.day[:7]});self.assertEqual(result['approved_hours'],'4')
  self.assertEqual(self.call('cao/calculate','POST',{'date':'2026-10-11','group':1,'step':1,'hours':'4'})['gross_estimate'],'62.08')
  self.call('hr/contract-term','POST',{'employee_id':1,'start_date':'2026-02-01','end_date':'2026-03-01'},status=409)
 def test_more_than_1000_records_not_silently_truncated(self):
  with sqlite3.connect(self.s.db) as c:c.executemany("INSERT INTO alerts(title,severity,description,status) VALUES(?,'Normaal','Fictief','Open')",[(f'Fictief {n}',) for n in range(1005)])
  self.assertEqual(len(self.call('records/alerts')),1006)
class Gate(unittest.TestCase):
 def test_gate_basic_cookie_and_bearer(self):
  s=LiveServer(gate='test-gate-only')
  try:
   self.assertEqual(s.request('/')[0],401)
   basic='Basic '+base64.b64encode(b'demo:test-gate-only').decode();status,_,h=s.request('/',headers={'Authorization':basic});self.assertEqual(status,200)
   cookie=h['Set-Cookie'];self.assertIn('HttpOnly',cookie);self.assertIn('Secure',cookie)
   headers={'Cookie':cookie.split(';')[0]};status,b,_=s.request('/api/login','POST',{'username':'Roefs','password':'Amocean1!'},headers=headers);self.assertEqual(status,200)
   self.assertEqual(s.request('/api/me',token=b['token'],headers=headers)[0],200)
  finally:s.close()
if __name__=='__main__':unittest.main(verbosity=2)
