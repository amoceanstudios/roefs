"""Connectorcontract tegen een echte lokale HTTP-testserver; geen echte ERP-claims."""
import copy,json,os,sqlite3,threading,time,unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch
from support import LiveServer
from services import synchronization as sync

class ExternalAPI:
 def __init__(self):
  self.records={k:{} for k in sync.CATEGORIES};self.idempotency={};self.writes=0;self.fail_after_write=False;self.fail_get=False;self.reject_revision=False;self.lock=threading.Lock();parent=self
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def response(self,data,code=200):
    raw=json.dumps(data).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
   def do_GET(self):
    if self.headers.get('Authorization')!='Bearer fictief-test-token':return self.response({'error':'unauthorized'},401)
    if self.path=='/capabilities':return self.response({'protocol':'roefs-sync-v1','categories':list(sync.CATEGORIES),'write':True,'conditional_updates':True,'idempotency':True})
    if parent.fail_get:return self.response({'error':'fictieve storing'},503)
    category=self.path.split('/')[2].split('?')[0]
    with parent.lock:self.response({'items':list(parent.records[category].values()),'next_cursor':None})
   def do_POST(self):self.write_record()
   def do_PUT(self):self.write_record()
   def write_record(self):
    if self.headers.get('Authorization')!='Bearer fictief-test-token':return self.response({},401)
    data=json.loads(self.rfile.read(int(self.headers['Content-Length'])));parts=self.path.split('/');category=parts[2];eid=parts[3] if len(parts)>3 else 'ext-'+str(len(parent.records[category])+1);key=self.headers.get('Idempotency-Key')
    with parent.lock:
     if key in parent.idempotency:return self.response(parent.idempotency[key])
     old=parent.records[category].get(eid)
     if self.command=='PUT' and (parent.reject_revision or not old or self.headers.get('If-Match')!=old['revision']):return self.response({},412)
     if not key:return self.response({},400)
     record={'id':eid,'revision':str(int(old['revision'])+1 if old else 1),'fields':data['fields'],'roefs_id':data.get('roefs_id','')};parent.records[category][eid]=record;parent.idempotency[key]=record;parent.writes+=1
     if parent.fail_after_write:parent.fail_after_write=False;return self.response({'error':'antwoord verloren na opslaan'},503)
     return self.response(record)
  self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.url='http://127.0.0.1:'+str(self.server.server_port)
 def close(self):self.server.shutdown();self.server.server_close();self.thread.join()
 def add(self,category,eid,fields):self.records[category][eid]={'id':eid,'revision':'1','fields':fields}
 def modify(self,category,eid,**fields):
  row=self.records[category][eid];row['fields'].update(fields);row['revision']=str(int(row['revision'])+1)

class Sync(unittest.TestCase):
 def setUp(self):
  self.external=ExternalAPI();self.env=patch.dict(os.environ,{'ROEFS_SYNC_ALLOWED_HOSTS':'127.0.0.1','ROEFS_SYNC_ALLOW_LOOPBACK_TEST':'1','ROEFS_SYNC_TOKEN_TEST':'fictief-test-token'});self.env.start();self.server=LiveServer();self.admin=self.server.login();meta=self.server.request('/api/modules',token=self.admin)[1];self.modules={k:(v['label'],v['fields']) for k,v in meta.items()};self.db=self.server.db
 def tearDown(self):self.server.close();self.external.close();self.env.stop()
 def config(self,policies,automatic=False):
  code,config,_=self.server.request('/api/v5/sync/connections','POST',{'name':'Fictieve API-koppeling','base_url':self.external.url,'secret_env':'ROEFS_SYNC_TOKEN_TEST','policies':policies,'enabled':automatic,'interval_seconds':30},self.admin);self.assertEqual(code,200,config)
  if not automatic:
   self.server.stop()
   with sync.connect(self.db) as c:c.execute('UPDATE sync_connections SET enabled=1 WHERE id=?',(config['id'],))
  return config['id']
 def rows(self,table):
  with sync.connect(self.db) as c:return [dict(x) for x in c.execute('SELECT * FROM '+table)]
 def run_sync(self,cid):return sync.run_connection(self.db,cid,self.modules,force=True)
 def customer(self,name='Fictieve externe klant'):return {'name':name,'contact':'Demo contact','email':'sync@fictief.invalid','phone':'000','city':'Teststad','status':'Actief'}
 def test_import_repeat_and_updates_no_duplicates(self):
  self.external.add('customers','klant-1',self.customer());cid=self.config({'customers':'external'});r=self.run_sync(cid);self.assertEqual(r['status'],'Geslaagd',r);self.assertEqual(r['imported'],1)
  self.assertEqual(self.run_sync(cid)['imported'],0);self.assertEqual(len(self.rows('customers')),2)
  self.external.modify('customers','klant-1',city='Nieuwe teststad');self.assertEqual(self.run_sync(cid)['imported'],1);self.assertEqual(self.rows('customers')[-1]['city'],'Nieuwe teststad');self.assertEqual(len(self.rows('sync_links')),1)
 def test_bidirectional_and_simultaneous_changes_conflict(self):
  self.external.add('customers','klant-1',self.customer());cid=self.config({'customers':'both'});r=self.run_sync(cid);self.assertEqual(r['status'],'Geslaagd',r);link=next(x for x in self.rows('sync_links') if x['external_id']=='klant-1')
  with sync.connect(self.db) as c:c.execute('UPDATE customers SET city=? WHERE id=?',('Lokale plaats',link['local_id']))
  r=self.run_sync(cid);self.assertEqual(r['exported'],1,r);self.assertEqual(self.external.records['customers']['klant-1']['fields']['city'],'Lokale plaats')
  with sync.connect(self.db) as c:c.execute('UPDATE customers SET city=? WHERE id=?',('Nog een lokale plaats',link['local_id']))
  self.external.modify('customers','klant-1',city='Gelijktijdig extern');r=self.run_sync(cid);self.assertEqual(r['conflicts'],1,r);self.assertEqual(self.rows('customers')[-1]['city'],'Nog een lokale plaats');self.assertEqual(self.external.records['customers']['klant-1']['fields']['city'],'Gelijktijdig extern');self.assertEqual(self.run_sync(cid)['conflicts'],0)
 def test_durable_outbox_retry_after_remote_commit_no_duplicate(self):
  cid=self.config({'customers':'roefs'});self.external.fail_after_write=True;first=self.run_sync(cid);self.assertEqual(first['status'],'Mislukt');self.assertEqual(len(self.external.records['customers']),1);self.assertEqual(self.rows('sync_outbox')[0]['status'],'Wacht')
  second=self.run_sync(cid);self.assertEqual(second['status'],'Geslaagd',second);self.assertEqual(len(self.external.records['customers']),1);self.assertEqual(self.external.writes,1);self.assertEqual(self.rows('sync_outbox')[0]['status'],'Verwerkt')
 def test_conditional_update_refuses_external_overwrite(self):
  cid=self.config({'customers':'roefs'});self.assertEqual(self.run_sync(cid)['status'],'Geslaagd')
  with sync.connect(self.db) as c:c.execute("UPDATE customers SET city='Lokale testwijziging' WHERE id=1")
  self.external.reject_revision=True;r=self.run_sync(cid);self.assertEqual(r['status'],'Mislukt');self.assertEqual(len(self.rows('sync_conflicts')),1);self.assertNotEqual(self.external.records['customers']['ext-1']['fields']['city'],'Lokale testwijziging')
 def test_dependency_order_external_ids_and_hours_materials_invoice(self):
  self.external.add('customers','c',self.customer());self.external.add('employees','e',{'name':'Fictieve externe medewerker','role':'Schoonmaak','email':'extern@fictief.invalid','phone':'000','contract_hours':'32','status':'Actief'})
  self.external.add('articles','a',{'code':'DEMO-A','name':'Fictief reinigingsmiddel','unit':'liter','rate':'3.25','vat_rate':'21','status':'Actief'})
  self.external.add('objects','o',{'name':'Fictieve externe locatie','customer_id':'c','address':'Demo 1','city':'Teststad','type':'Kantoor','frequency':'Dagelijks','status':'Actief'})
  self.external.add('workorders','w',{'object_id':'o','employee_id':'e','description':'Fictieve externe opdracht','date':'2030-01-02','hours':'2','status':'Nieuw','signed_by':''})
  self.external.add('hours','h',{'employee_id':'e','shift_id':'','date':'2030-01-02','hours':'2','status':'Ingediend'})
  self.external.add('invoices','i',{'number':'EXTERN-DEMO-001','customer_id':'c','contract_id':'','amount':'78.65','due_date':'2030-02-01','status':'Concept'})
  cid=self.config({k:'external' for k in ('customers','employees','articles','objects','workorders','hours','invoices')});r=self.run_sync(cid);self.assertEqual(r['status'],'Geslaagd',r);self.assertEqual(r['imported'],7);obj=self.rows('objects')[-1];self.assertEqual(obj['customer_id'],str(self.rows('customers')[-1]['id']));self.assertEqual(self.rows('articles')[0]['rate'],'3.25');self.assertEqual(self.run_sync(cid)['imported'],0)
 def test_deleted_and_duplicate_records_preserved(self):
  self.external.add('customers','c',self.customer());cid=self.config({'customers':'external'});self.run_sync(cid);self.external.records['customers']['c']['deleted']=True;self.external.records['customers']['c']['revision']='2';r=self.run_sync(cid);self.assertEqual(r['conflicts'],1);self.assertEqual(len(self.rows('customers')),2)
 def test_lease_only_one_worker_and_recovery(self):
  cid=self.config({'customers':'external'})
  with sync.connect(self.db) as c:c.execute('UPDATE sync_connections SET lease_owner=?,lease_until=? WHERE id=?',('other',sync.stamp(sync.now()+sync.dt.timedelta(minutes=1)),cid))
  self.assertEqual(self.run_sync(cid)['status'],'Al bezig')
  with sync.connect(self.db) as c:c.execute('UPDATE sync_connections SET lease_until=? WHERE id=?',('2000-01-01',cid))
  self.assertEqual(self.run_sync(cid)['status'],'Geslaagd')
 def test_prepared_connector_inactive_missing_api_and_ssrf(self):
  token=self.server.login('Bart van Aalde','Amocean2!');self.assertEqual(self.server.request('/api/v5/sync',token=token)[0],403)
  result=self.server.request('/api/v5/sync/connections','POST',{'name':'AFAS voorbereid','provider':'afas','enabled':False,'policies':{}},self.admin);self.assertEqual(result[0],200);self.assertEqual(result[1]['state'],'Niet actief')
  bad=self.server.request('/api/v5/sync/connections','POST',{'name':'Onveilig','base_url':'http://169.254.169.254','secret_env':'ROEFS_SYNC_TOKEN_TEST','enabled':True,'policies':{'customers':'both'}},self.admin);self.assertEqual(bad[0],400)
  with patch.dict(os.environ,{'ROEFS_SYNC_ALLOW_LOOPBACK_TEST':'0'}):
   with self.assertRaises(Exception):sync.validate_url(self.external.url)
  self.assertNotIn('fictief-test-token',json.dumps(self.server.request('/api/v5/sync',token=self.admin)[1]))
 def test_automatic_worker_without_manual_run_and_restart(self):
  self.external.add('customers','auto',self.customer('Fictieve automatische klant'));cid=self.config({'customers':'external'},automatic=True)
  deadline=time.monotonic()+10
  while time.monotonic()<deadline:
   if any(r['name']=='Fictieve automatische klant' for r in self.rows('customers')):break
   time.sleep(.1)
  self.assertTrue(any(r['name']=='Fictieve automatische klant' for r in self.rows('customers')))
  self.server.stop();self.external.modify('customers','auto',city='Na herstart')
  with sync.connect(self.db) as c:c.execute('UPDATE sync_connections SET next_run=NULL WHERE id=?',(cid,))
  self.server.start();deadline=time.monotonic()+10
  while time.monotonic()<deadline:
   if any(r['city']=='Na herstart' for r in self.rows('customers')):break
   time.sleep(.1)
  self.assertTrue(any(r['city']=='Na herstart' for r in self.rows('customers')))
 def test_outage_history_backoff_and_conflict_resolution(self):
  self.external.add('customers','c',self.customer());cid=self.config({'customers':'external'});self.run_sync(cid);link=self.rows('sync_links')[0]
  with sync.connect(self.db) as c:c.execute("UPDATE customers SET city='Lokale correctie' WHERE id=?",(link['local_id'],))
  self.run_sync(cid);conflict=self.rows('sync_conflicts')[0]
  with sync.connect(self.db) as c:
   c.execute('BEGIN IMMEDIATE');sync.resolve(c,{'id':1,'username':'Roefs','role':'admin'},conflict['id'],{'action':'external','local_version':conflict['local_version'],'reason':'Extern is leidend; fictieve correctie beoordeeld.'},self.modules);c.commit()
  self.assertEqual(self.rows('customers')[-1]['city'],'Teststad');self.external.fail_get=True;self.assertEqual(self.run_sync(cid)['status'],'Mislukt');connection=self.rows('sync_connections')[0];self.assertEqual(connection['failures'],1);self.assertGreater(connection['next_run'],connection['last_run']);self.assertEqual(self.rows('sync_runs')[-1]['status'],'Mislukt')
