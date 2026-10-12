"""Negatieve én positieve scopeproeven door de echte HTTP-server."""
import base64,datetime as dt,json,sqlite3,unittest
from support import LiveServer

class ScopeHTTP(unittest.TestCase):
 def setUp(self):
  self.s=LiveServer();self.admin=self.s.login();self.token=self.admin
  self.north={};self.south={}
  for region,data in [('Noord',self.north),('Zuid',self.south)]:
   for table,payload in [('customers',{'name':'Fictief '+region}),('employees',{'name':'Fictieve medewerker '+region,'contract_hours':'38'})]:
    data[table]=self.req('/entities/'+table,'POST',payload,201);self.classify(table,data[table]['id'],region)
   data['objects']=self.req('/entities/objects','POST',{'name':'Fictieve locatie '+region,'customer_id':str(data['customers']['id'])},201);self.classify('objects',data['objects']['id'],region)
   data['workorders']=self.req('/workorders','POST',{'object_id':str(data['objects']['id']),'employee_id':str(data['employees']['id']),'description':'Fictieve opdracht '+region,'date':'2030-02-04','start_time':'08:00','end_time':'09:00','capacity':1});self.classify('workorders',data['workorders']['id'],region)
   data['shifts']=self.req('/shifts','POST',{'object_id':str(data['objects']['id']),'employee_id':str(data['employees']['id']),'workorder_id':data['workorders']['id'],'date':'2030-02-04','start_time':'08:00','end_time':'09:00'});self.classify('shifts',data['shifts']['id'],region)
  code,user,_=self.s.request('/api/users','POST',{'username':'Fictieve scopebeheerder','password':'Fictief-test-2026!','role':'operations'},self.admin);self.assertEqual(code,201,user);self.uid=user['id']
  self.policy={'enabled':True,'departments':['Interieur'],'regions':['Noord'],'default_department':'Interieur','default_region':'Noord'}
  self.req('/security/scopes/'+str(self.uid),'PUT',{'version':0,**self.policy});self.token=self.s.login('Fictieve scopebeheerder','Fictief-test-2026!')
 def tearDown(self):self.s.close()
 def req(self,path,method='GET',body=None,status=200,token=None):
  code,data,_=self.s.request('/api/v5'+path,method,body,token or self.token);self.assertEqual(code,status,(path,data));return data
 def classify(self,table,rid,region):self.req('/security/classifications','POST',{'module':table,'ids':[rid],'department':'Interieur','region':region,'versions':{str(rid):0}})
 def test_lists_counts_lookup_detail_updates_delete_and_context_isolation(self):
  n=self.north['customers'];z=self.south['customers']
  result=self.req('/entities/customers?limit=1');self.assertEqual(result['total'],1);self.assertEqual(result['items'][0]['id'],n['id'])
  self.req('/entities/customers/'+str(z['id']),status=404)
  for method,body in [('PUT',{'version':z['version'],'name':'Onbevoegde wijziging'}),('DELETE',{'version':z['version']})]:self.req('/entities/customers/'+str(z['id']),method,body,404)
  code,lookups,_=self.s.request('/api/lookups',token=self.token);self.assertEqual(code,200);self.assertEqual([r['id'] for r in lookups['customers']],[n['id']])
  code,rows,_=self.s.request('/api/records/customers?limit=1',token=self.token);self.assertEqual(code,200);self.assertNotIn('Zuid',json.dumps(rows))
  new=self.req('/entities/customers','POST',{'name':'Fictieve nieuwe noordklant'},201)
  self.assertEqual(self.req('/entities/customers/'+str(new['id']))['name'],'Fictieve nieuwe noordklant')
  self.req('/entities/objects','POST',{'name':'Verboden koppeling','customer_id':str(z['id'])},404)
  self.assertGreater(self.req('/entities/customers',token=self.admin)['total'],self.req('/entities/customers')['total'])
  self.req('/security/scopes',status=403);self.req('/migration',status=403);self.req('/onboarding',status=403);self.req('/sync',status=403)
 def test_planning_reports_export_files_and_atomic_bulk(self):
  n=self.north;z=self.south
  calendar=self.req('/planning/calendar?from=2030-02-04&to=2030-02-04');self.assertEqual([r['id'] for r in calendar['shifts']],[n['shifts']['id']]);self.assertNotIn('Zuid',json.dumps(calendar))
  suggestions=self.req('/planning/suggest','POST',{'object_id':str(n['objects']['id']),'date':'2030-02-05','start_time':'08:00','end_time':'09:00'});self.assertEqual([x['id'] for x in suggestions['candidates']],[n['employees']['id']])
  report=self.req('/reports?from=2030-02-04&to=2030-02-04');self.assertEqual(report['planned_hours'],1);self.assertNotIn('Zuid',json.dumps(report))
  for path in ['/reports/csv?from=2030-02-04&to=2030-02-04','/reports/management/csv?from=2030-02-04&to=2030-02-04']:
   result=self.req(path);self.assertNotIn(b'Zuid',result)
  self.req('/workorders/'+str(z['workorders']['id'])+'/pdf',status=404)
  self.req('/planning/bulk','POST',{'shifts':[{'object_id':str(n['objects']['id']),'employee_id':str(n['employees']['id']),'date':'2030-02-05','start_time':'08:00','end_time':'09:00'},{'id':z['shifts']['id'],'version':z['shifts']['version'],'status':'Geannuleerd'}]},404)
  self.assertEqual(self.req('/entities/shifts')['total'],1)
  for data in (n,z):
   self.req('/files','POST',{'name':'fictief.txt','content':base64.b64encode(b'Fictieve bijlage').decode(),'workorder_id':data['workorders']['id']},token=self.admin)
  # Upload door globale beheerder is ongeclassificeerd en dus afgeschermd totdat beheer indeelt.
  self.assertEqual(self.req('/files'),[])
  self.req('/files','POST',{'name':'fictief.txt','content':base64.b64encode(b'Fictieve bijlage').decode(),'workorder_id':z['workorders']['id']},404)
 def test_policy_change_revokes_sessions_and_scoped_admin_is_rejected(self):
  self.req('/security/scopes/'+str(self.uid),'PUT',{'version':1,**self.policy,'regions':['Zuid'],'default_region':'Zuid'},token=self.admin)
  self.req('/entities/customers',status=401)
  self.token=self.s.login('Fictieve scopebeheerder','Fictief-test-2026!');self.assertEqual(self.req('/entities/customers')['items'][0]['id'],self.south['customers']['id'])
  with sqlite3.connect(self.s.db) as c:admin_id=c.execute("SELECT id FROM users WHERE username='Roefs'").fetchone()[0]
  self.req('/security/scopes/'+str(admin_id),'PUT',{'version':0,**self.policy},400,token=self.admin)
 def test_unclassified_records_all_operational_endpoints_are_closed(self):
  from server import MODULES
  for module in MODULES:
   with self.subTest(module=module):
    for prefix in ('/api/v5/entities/','/api/records/'):
     code,data,_=self.s.request(prefix+module+'/1',token=self.token);self.assertIn(code,(403,404),(prefix,module,data))
  home=self.req('/home');work=next(r for r in home['cards'] if r['tab']=='workorders');self.assertEqual(work['ids'],[self.north['workorders']['id']])
  # Een negatieve controle mag geen ACTOR-context achterlaten bij een volgende beheerrequest.
  self.req('/entities/customers/1',token=self.admin)
