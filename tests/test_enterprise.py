"""Echte HTTP-/SQLite-integratie; uitsluitend fictieve gegevens en tijdelijke opslag."""
import base64,concurrent.futures,datetime as dt,json,sqlite3,unittest,urllib.request,urllib.error
from pathlib import Path
from support import LiveServer

class Enterprise(unittest.TestCase):
 def setUp(self):
  self.s=LiveServer();self.admin=self.s.login();self.emp=self.s.login('Bart van Aalde','Amocean2!');self.day='2030-02-04'
 def tearDown(self):self.s.close()
 def call(self,path,method='GET',body=None,token=None,status=200):
  code,data,headers=self.s.request('/api/'+path,method,body,token or self.admin)
  self.assertEqual(code,status,(path,code,data));return data
 def create(self,table,body):return self.call('v5/entities/'+table,'POST',body,status=201)
 def update(self,table,row,body):return self.call('v5/entities/'+table+'/'+str(row['id']),'PUT',{**body,'version':row['version']})
 def user(self,role,employee_id=None):
  self.call('users','POST',{'username':'Test '+role,'password':'Fictief-test-2030!','role':role,'employee_id':employee_id},status=201)
  return self.s.login('Test '+role,'Fictief-test-2030!')
 def chain(self):
  cust=self.create('customers',{'name':'Fictieve Ketentest BV','email':'test@fictief.invalid','status':'Actief'})
  loc=self.create('objects',{'name':'Fictieve fabriek','customer_id':str(cust['id']),'address':'Demoweg 10','city':'Teststad','region':'Zuid'})
  loc2=self.create('objects',{'name':'Fictieve tweede locatie','customer_id':str(cust['id'])})
  contract=self.create('contracts',{'name':'Fictief jaarcontract','customer_id':str(cust['id']),'object_id':str(loc['id']),'monthly_value':'1000','start_date':'2030-01-01','end_date':'2030-12-31','renewal_date':'2030-11-30','contract_number':'TEST-2030'})
  team=self.call('v5/resources/teams','POST',{'name':'Fictief team Zuid','department':'Industrieel'})
  employee=self.call('v5/entities/employees/1');employee=self.update('employees',employee,{'team_id':team['id'],'skills':'industrieel','department':'Industrieel','region':'Zuid'})
  cert=self.call('v5/resources/certifications','POST',{'employee_id':1,'name':'VCA','expires_on':'2031-12-31'})
  asset=self.create('assets',{'name':'Fictieve schrobmachine','object_id':str(loc['id']),'inspection_date':'2031-12-31','status':'Beschikbaar'})
  w=self.call('v5/workorders','POST',{'object_id':str(loc['id']),'description':'Fictieve periodieke reiniging','date':self.day,'start_time':'08:00','end_time':'12:00','team_id':team['id'],'required_skills':'industrieel','required_certifications':'VCA','required_assets':str(asset['id']),'capacity':1})
  task=self.call(f'v5/workorders/{w["id"]}/checklist','POST',{'title':'Vloer gereinigd en gecontroleerd'})
  return {'customer':cust,'location':loc,'location2':loc2,'contract':contract,'team':team,'employee':employee,'cert':cert,'asset':asset,'work':w,'task':task}
 def transition(self,w,state,token=None,**extra):return self.call(f'v5/workorders/{w["id"]}/transition','POST',{'version':w['version'],'state':state,**extra},token)
 def assign(self,w,eid=1,token=None):return self.call('v5/shifts','POST',{'workorder_id':w['id'],'object_id':w['object_id'],'employee_id':str(eid),'date':w['date'],'start_time':w['start_time'],'end_time':w['end_time']},token)
 def test_full_role_chain_persists_restart(self):
  x=self.chain();w=x['work'];planner=self.user('planner');supervisor=self.user('supervisor');finance=self.user('finance');director=self.user('director');other=self.user('employee')
  w=self.transition(w,'Gepland',planner)
  suggestion=self.call('v5/planning/suggest','POST',{'workorder_id':w['id'],'object_id':w['object_id'],'date':w['date'],'start_time':w['start_time'],'end_time':w['end_time']},planner)
  self.assertEqual(suggestion['candidates'][0]['id'],1);self.assertIn('reasons',suggestion['candidates'][0])
  shift=self.assign(w,token=planner);w=self.transition(w,'Toegewezen',planner);w=self.transition(w,'In uitvoering',self.emp)
  self.call(f'v5/workorders/{w["id"]}/checklist','POST',{'id':x['task']['id'],'version':1,'done':True},self.emp)
  file=self.call('v5/files','POST',{'name':'fictief-verslag.txt','content':base64.b64encode(b'Uitvoering fictieve reiniging.').decode(),'category':'Werkbon','workorder_id':w['id']},self.emp)
  self.call(f'v5/files/{file["id"]}',token=other,status=404)
  hour=self.call('v5/hours','POST',{'employee_id':1,'workorder_id':w['id'],'starts_at':self.day+'T08:00:00+01:00','ends_at':self.day+'T12:00:00+01:00','break_minutes':30},self.emp)
  self.assertEqual(hour['hours'],'3.50')
  w=self.transition(w,'Voltooid',self.emp,completion_notes='Fictieve controle geslaagd.',signed_by='Demo medewerker')
  w=self.transition(w,'Goedgekeurd',supervisor)
  self.call(f'v5/hours/{hour["id"]}/review','POST',{'version':hour['version'],'status':'Goedgekeurd'},supervisor)
  w=self.transition(w,'Factureerbaar',supervisor)
  inv=self.call('v5/invoices/prepare','POST',{'workorder_id':w['id'],'version':w['version'],'hourly_rate':'35.25','vat_rate':'21','lines':[{'description':'Fictieve materialen','quantity':'2','rate':'3.10','vat_rate':'21'}]},finance)
  self.assertEqual(inv['net_amount'],'129.58');self.assertEqual(inv['vat_amount'],'27.21');self.assertEqual(inv['amount'],'156.79')
  inv=self.call(f'v5/invoices/{inv["id"]}/review','POST',{'version':inv['version'],'status':'Goedgekeurd'},finance)
  report=self.call('v5/reports?from=2030-02-01&to=2030-02-28&customer_id='+str(x['customer']['id']),token=director)
  self.assertEqual(report['approved_hours'],'3.50');self.assertEqual(report['planned_hours'],4)
  code,pdf,_=self.s.request(f'/api/v5/invoices/{inv["id"]}/pdf',token=finance);self.assertEqual(code,200);self.assertTrue(pdf.startswith(b'%PDF-1.4'))
  self.call(f'v5/workorders/{w["id"]}',token=other,status=404)
  self.call('v5/invoices/prepare','POST',{'workorder_id':w['id'],'version':w['version'],'hourly_rate':'35'},self.emp,status=403)
  self.s.stop();self.s.start()
  self.assertEqual(self.call(f'v5/workorders/{w["id"]}')['workorder']['workflow'],'Factureerbaar')
  self.assertEqual(self.call(f'v5/invoices/{inv["id"]}/lines',token=finance)['invoice']['amount'],'156.79')
  code,content,_=self.s.request(f'/api/v5/files/{file["id"]}',token=self.emp);self.assertEqual(code,200);self.assertIn(b'fictieve',content)
  self.assertEqual(self.call('v5/reports?from=2030-02-01&to=2030-02-28',token=director)['approved_hours'],'3.50')
 def test_stale_versions_and_transactional_bulk(self):
  x=self.chain();w=x['work'];s=self.assign(w)
  self.call('v5/shifts/'+str(s['id']),'PUT',{'version':s['version'],'planner_notes':'Nieuwe notitie'})
  self.call('v5/shifts/'+str(s['id']),'PUT',{'version':s['version'],'planner_notes':'Verouderd'},status=409)
  self.call('v5/shifts/'+str(s['id']),'PUT',{'planner_notes':'Zonder versie'},status=428)
  before=len(self.call('records/shifts'))
  base={'object_id':w['object_id'],'employee_id':'1','date':'2030-02-05','start_time':'08:00','end_time':'12:00'}
  self.call('v5/planning/bulk','POST',{'shifts':[base,base]},status=409)
  self.assertEqual(len(self.call('records/shifts')),before)
 def test_mandatory_certification_equipment_and_capacity(self):
  x=self.chain();w=x['work'];self.call('v5/resources/certifications/'+str(x['cert']['id']),'PUT',{'version':1,'expires_on':'2029-01-01'})
  r=self.call('v5/planning/suggest','POST',{'workorder_id':w['id'],'object_id':w['object_id'],'date':w['date'],'start_time':w['start_time'],'end_time':w['end_time']})
  self.assertFalse(r['candidates']);self.assertIn('verlopen',' '.join(r['excluded'][0]['reasons']))
  self.call('v5/shifts','POST',{'workorder_id':w['id'],'object_id':w['object_id'],'employee_id':'1','date':w['date'],'start_time':w['start_time'],'end_time':w['end_time']},status=409)
  w=self.transition(w,'Gepland');self.call(f'v5/workorders/{w["id"]}/transition','POST',{'version':w['version'],'state':'Toegewezen'},status=409)
 def test_cookie_csrf_and_session_invalidation(self):
  code,data,headers=self.s.request('/api/login','POST',{'username':'Roefs','password':'Amocean1!'})
  cookie=headers['Set-Cookie'].split(';')[0];self.assertIn('HttpOnly',headers['Set-Cookie']);self.assertIn('SameSite=Strict',headers['Set-Cookie'])
  self.assertEqual(self.s.request('/api/me',headers={'Cookie':cookie})[0],200)
  self.assertEqual(self.s.request('/api/v5/preferences','PUT',{'tour_completed':1},headers={'Cookie':cookie})[0],403)
  self.assertEqual(self.s.request('/api/v5/preferences','PUT',{'tour_completed':1},headers={'Cookie':cookie,'X-CSRF-Token':data['csrf']})[0],200)
  self.assertEqual(self.s.request('/api/logout','POST',{},headers={'Cookie':cookie,'X-CSRF-Token':data['csrf']})[0],200)
  self.assertEqual(self.s.request('/api/me',headers={'Cookie':cookie})[0],401)
 def test_rbac_every_role_and_legacy_bypass(self):
  x=self.chain();w=x['work'];self.assign(w)
  for role in ('company_admin','director','operations','planner','supervisor','finance','auditor'):
   token=self.user(role);self.call('v5/metadata',token=token)
   if role!='company_admin':self.call('users','POST',{'username':'Forbidden','password':'ForbiddenTest!','role':'admin'},token,status=403)
   if role in ('director','auditor','finance'):
    self.call('v5/shifts','POST',{'object_id':w['object_id'],'date':self.day,'start_time':'13:00','end_time':'14:00'},token,status=403)
  self.call('records/workorders/'+str(w['id']),'PUT',{'status':'Afgerond'},status=409)
  self.call('v5/entities/workorders/'+str(w['id']),'DELETE',{'version':w['version']},status=409)
  auditor=self.s.login('Test auditor','Fictief-test-2030!')
  self.call(f'v5/workorders/{w["id"]}/checklist','POST',{'id':x['task']['id'],'version':1,'done':True},auditor,status=403)
 def test_upload_path_type_scope_and_deduplicated_notifications(self):
  x=self.chain();w=x['work'];self.assign(w)
  data={'name':'../unsafe.txt','content':base64.b64encode(b'Test').decode(),'category':'Test','workorder_id':w['id']}
  self.call('v5/files','POST',data,self.emp,status=400)
  self.call('v5/files','POST',{**data,'name':'test.html'},self.emp,status=400)
  self.call('v5/preferences','PUT',{'tour_step':2,'tour_completed':1},self.emp)
  self.s.stop();self.s.start();self.assertEqual(self.call('v5/preferences',token=self.emp)['tour_step'],2)
  self.call('v5/reminders/run','POST',{});first=self.call('v5/notifications');self.call('v5/reminders/run','POST',{});self.assertEqual(len(self.call('v5/notifications')),len(first))
  notice=self.call('v5/notifications',token=self.emp)[0];self.call('v5/notifications/read','POST',{'id':notice['id']},status=404)
 def test_time_dst_midnight_duplicates(self):
  x=self.chain();w=x['work'];self.assign(w)
  body={'employee_id':1,'workorder_id':w['id'],'starts_at':'2030-10-27T02:30:00+02:00','ends_at':'2030-10-27T02:30:00+01:00','break_minutes':0}
  hour=self.call('v5/hours','POST',body,self.emp);self.assertEqual(hour['hours'],'1.00')
  self.call('v5/hours','POST',body,self.emp,status=409)
  self.call('v5/hours','POST',{**body,'starts_at':'2030-03-31T02:30:00+01:00','ends_at':'2030-03-31T04:00:00+02:00'},self.emp,status=400)
  night=self.call('v5/hours','POST',{**body,'starts_at':'2030-02-05T23:00:00+01:00','ends_at':'2030-02-06T02:00:00+01:00'},self.emp);self.assertEqual(night['hours'],'3.00')
 def test_concurrent_assignment_exactly_one_success(self):
  x=self.chain();w=x['work'];body={'workorder_id':w['id'],'object_id':w['object_id'],'employee_id':'1','date':w['date'],'start_time':w['start_time'],'end_time':w['end_time']}
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:self.s.request('/api/v5/shifts','POST',body,self.admin)[0],range(2)))
  self.assertEqual(sorted(results),[200,409])
 def test_customer_import_all_or_nothing_and_number(self):
  self.call('v5/customers/import','POST',{'rows':[{'name':'Unieke fictieve klant'},{'name':'Unieke fictieve klant'}]},status=409)
  self.assertEqual(self.call('v5/entities/customers?q=Unieke')['total'],0)
  a=self.create('customers',{'name':'Nieuwe fictieve klant'});self.assertTrue(a['customer_number'].startswith('KL-'))
  timeline=self.call(f'v5/customers/{a["id"]}/timeline');self.assertEqual(timeline['customer']['id'],a['id'])

 def test_batch_report_detects_same_absence_conflict(self):
  x=self.chain();self.assign(x['work'])
  self.create('leave',{'employee_id':'1','start_date':self.day,'end_date':self.day,'type':'Verlof','status':'Goedgekeurd'})
  result=self.call('v5/reports?from='+self.day+'&to='+self.day)
  self.assertEqual(len(result['conflicts']),1);self.assertIn('verlof',' '.join(result['conflicts'][0]['reasons']))

 def test_home_counts_and_drilldown_scope(self):
  x=self.chain();home=self.call('v5/home');card=next(c for c in home['cards'] if c['tab']=='workorders');self.assertIn(x['work']['id'],card['ids']);self.assertEqual(card['count'],len(card['ids']))
  result=self.call('v5/entities/workorders?ids='+str(x['work']['id']));self.assertEqual(result['total'],1)
  employee_home=self.call('v5/home',token=self.emp);self.assertEqual([c['tab'] for c in employee_home['cards']],['calendar'])
  own=self.call('v5/planning/calendar?from=2030-02-04&to=2030-02-04',token=self.emp);self.assertEqual(own['history'],[]);self.assertEqual(own['reservations'],[])

 def test_restricted_roles_cannot_read_admin_messages_or_approve_hours(self):
  self.call('messages','POST',{'subject':'Privé fictief','body':'Bericht uitsluitend voor beheer'},self.emp,status=201)
  planner=self.user('planner');supervisor=self.user('supervisor');finance=self.user('finance');auditor=self.user('auditor')
  self.assertEqual(self.call('messages',token=planner),[])
  self.assertEqual(self.call('planning/overview',token=supervisor)['employees'],[])
  self.call('records/hours/1','PUT',{'status':'Afgewezen'},finance,status=403)
  self.call('smart/overview',token=auditor,status=403)
