"""Mockadapterproeven; geen live boekhoudintegratie."""
import json,sqlite3,unittest
from support import LiveServer
from services import accounting

class MockAdapter:
 def __init__(self):self.calls={};self.fail=True;self.paid=False
 def test_connection(self,config):return {'ok':True}
 def upsert_debtor(self,customer,idempotency_key):return 'MOCK-DEBTOR-'+str(customer['id'])
 def export_invoice(self,invoice,debtor_reference,idempotency_key):
  self.calls.setdefault(idempotency_key,'MOCK-INVOICE-'+str(len(self.calls)+1))
  if self.fail:self.fail=False;raise TimeoutError('Fictieve timeout ná externe ontvangst')
  return self.calls[idempotency_key]
 def invoice_status(self,reference):return {'invoice_status':'Geboekt','payment_status':'Betaald' if self.paid else 'Open'}
class Accounting(unittest.TestCase):
 def setUp(self):
  self.s=LiveServer();self.token=self.s.login();self.user={'id':1,'username':'Fictieve adaptertest','role':'admin'}
  self.c=sqlite3.connect(self.s.db,isolation_level=None);self.c.row_factory=sqlite3.Row;self.c.execute('PRAGMA foreign_keys=ON')
 def tearDown(self):self.c.close();self.s.close()
 def req(self,path='',method='GET',body=None,status=200,token=None):
  code,data,_=self.s.request('/api/v5/accounting'+path,method,body,token or self.token);self.assertEqual(code,status,data);return data
 def invoice(self):
  # Fictieve goedgekeurde doelmodel-fixture; procesketen wordt in test_enterprise getest.
  rid=self.c.execute("INSERT INTO invoices(number,customer_id,amount,due_date,status,review_status,net_amount,vat_amount) VALUES('FICTIEF-ACCOUNTING','1','121','2030-02-01','Concept','Goedgekeurd','100','21')").lastrowid
  self.c.execute("INSERT INTO invoice_lines(invoice_id,description,quantity,rate,vat_rate,net,vat) VALUES(?,'Fictieve reiniging','1','100','21','100','21')",(rid,));return rid
 def test_configuration_inactive_authz_and_version(self):
  data=self.req();self.assertFalse(data['adapter_available'])
  self.req('', 'PUT',{'version':data['config']['version'],'provider':'exact','administration':'Fictief','credential_env':'ROEFS_ACCOUNTING_TOKEN'})
  self.assertFalse(self.req('/test','POST',{})['ok']);self.req('/run','POST',{},409)
  self.req('', 'PUT',{'version':1,'provider':'afas'},409)
  employee=self.s.login('Bart van Aalde','Amocean2!');self.req(status=403,token=employee);self.req('/queue','POST',{},403,employee)
  self.s.stop();self.s.start();self.assertEqual(self.req()['config']['provider'],'exact')
 def test_outbox_retry_idempotency_payment_status_restart(self):
  rid=self.invoice();self.req('/queue','POST',{'invoice_ids':[rid],'confirm':False},400)
  self.req('/queue','POST',{'invoice_ids':[rid],'confirm':True});self.req('/queue','POST',{'invoice_ids':[rid],'confirm':True});self.assertEqual(len(self.req()['jobs']),1)
  adapter=MockAdapter();self.assertTrue(accounting.test_connection(self.c,self.user,adapter)['ok'])
  accounting.run(self.c,self.user,adapter);job=self.req()['jobs'][0];self.assertEqual(job['state'],'Fout');self.assertEqual(len(adapter.calls),1)
  self.s.stop();self.s.start();self.req('/'+str(job['id'])+'/retry','POST',{})
  accounting.run(self.c,self.user,adapter);job=self.req()['jobs'][0];self.assertEqual(job['state'],'Verwerkt');self.assertEqual(len(adapter.calls),1);self.assertEqual(job['payment_status'],'Open')
  self.c.execute("UPDATE accounting_config SET last_sync='2000-01-01T00:00:00+00:00'")
  adapter.paid=True;accounting.run(self.c,self.user,adapter);self.assertNotEqual(self.req()['config']['last_sync'],'2000-01-01T00:00:00+00:00');self.assertEqual(self.req()['jobs'][0]['payment_status'],'Betaald');self.assertEqual(self.c.execute('SELECT status FROM invoices WHERE id=?',(rid,)).fetchone()[0],'Concept')
  self.assertTrue(self.req()['events'])
 def test_changed_invoice_blocks_export_and_unapproved_rejected(self):
  rid=self.invoice();self.req('/queue','POST',{'invoice_ids':[rid],'confirm':True})
  self.c.execute("UPDATE invoices SET amount='242' WHERE id=?",(rid,));adapter=MockAdapter();accounting.run(self.c,self.user,adapter);self.assertEqual(adapter.calls,{});self.assertIn('gewijzigd',self.req()['jobs'][0]['last_error'])
  self.c.execute("UPDATE invoices SET review_status='Te beoordelen' WHERE id=?",(rid,));self.c.execute('DELETE FROM accounting_events');self.c.execute('DELETE FROM accounting_outbox');self.req('/queue','POST',{'invoice_ids':[rid],'confirm':True},409)
 def test_automatic_cycle_requires_activation_and_restore_pauses(self):
  import tempfile
  from pathlib import Path
  from manage import backup,restore
  rid=self.invoice();adapter=MockAdapter();adapter.fail=False
  self.assertFalse(accounting.cycle(self.c,self.user,adapter)['active']);self.assertEqual(adapter.calls,{})
  self.c.execute('UPDATE accounting_config SET enabled=1')
  accounting.cycle(self.c,self.user,adapter);self.assertEqual(self.req()['jobs'][0]['state'],'Verwerkt')
  with tempfile.TemporaryDirectory() as tmp:
   archive=Path(tmp)/'backup.zip';target=Path(tmp)/'restored';backup(self.s.db,archive);restore(archive,target)
   with sqlite3.connect(target/'roefs.db') as restored:self.assertEqual(restored.execute('SELECT enabled FROM accounting_config').fetchone()[0],0);self.assertEqual(restored.execute('SELECT COUNT(*) FROM accounting_outbox').fetchone()[0],1)
