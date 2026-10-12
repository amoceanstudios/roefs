"""Providerneutraal boekhoudcontract en duurzame factuur-outbox.
Geen live provideradapter geïnstalleerd. Testadapters worden uitsluitend in tests geïnjecteerd.
Externe methoden moeten idempotentiesleutels ondersteunen; netwerk buiten schrijftransacties.
"""
import datetime as dt,json,time,uuid
from typing import Protocol
from domain import Problem
from .common import record,version,text,audit
from .data_migration import admin
PROVIDERS={'none':'Nog niet gekozen','exact':'Exact Online','afas':'AFAS','unit4':'Unit4','eboekhouden':'e-Boekhouden.nl'}
ADAPTERS={}
class Adapter(Protocol):
 def test_connection(self,config:dict)->dict:...
 def upsert_debtor(self,customer:dict,idempotency_key:str)->str:...
 def export_invoice(self,invoice:dict,debtor_reference:str,idempotency_key:str)->str:...
 def invoice_status(self,reference:str)->dict:...

def migrate(c):
 c.execute("CREATE TABLE IF NOT EXISTS accounting_config(id INTEGER PRIMARY KEY CHECK(id=1),provider TEXT NOT NULL DEFAULT 'none',administration TEXT NOT NULL DEFAULT '',credential_env TEXT NOT NULL DEFAULT '',version INTEGER NOT NULL DEFAULT 1,status TEXT NOT NULL DEFAULT 'Niet actief',last_sync TEXT,last_error TEXT NOT NULL DEFAULT '')")
 if 'enabled' not in {r[1] for r in c.execute('PRAGMA table_info(accounting_config)')}:c.execute('ALTER TABLE accounting_config ADD COLUMN enabled INTEGER NOT NULL DEFAULT 0')
 c.execute('INSERT OR IGNORE INTO accounting_config(id) VALUES(1)')
 c.execute("CREATE TABLE IF NOT EXISTS accounting_outbox(id INTEGER PRIMARY KEY,invoice_id INTEGER NOT NULL UNIQUE REFERENCES invoices(id),snapshot TEXT NOT NULL,idempotency_key TEXT NOT NULL UNIQUE,state TEXT NOT NULL DEFAULT 'Wachtend',attempts INTEGER NOT NULL DEFAULT 0,retry_at REAL NOT NULL DEFAULT 0,lease TEXT,lease_until REAL,external_reference TEXT,debtor_reference TEXT,invoice_status TEXT,payment_status TEXT,last_error TEXT NOT NULL DEFAULT '',updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
 c.execute('CREATE TABLE IF NOT EXISTS accounting_events(id INTEGER PRIMARY KEY,job_id INTEGER REFERENCES accounting_outbox(id),action TEXT NOT NULL,detail TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')

def config(c):return dict(c.execute('SELECT * FROM accounting_config WHERE id=1').fetchone())
def event(c,action,detail,jid=None):c.execute('INSERT INTO accounting_events(job_id,action,detail) VALUES(?,?,?)',(jid,action,text(detail,2000)))
def overview(c,user):
 admin(user);cfg=config(c)
 return {'config':cfg,'providers':PROVIDERS,'adapter_available':cfg['provider'] in ADAPTERS,'notice':'Niet actief zolang provider, API-contract, toegang en integratietest ontbreken. NoCore is uitsluitend migratiebron.','eligible':[dict(r) for r in c.execute("SELECT id,number,amount FROM invoices WHERE review_status='Goedgekeurd' AND NOT EXISTS(SELECT 1 FROM accounting_outbox a WHERE a.invoice_id=invoices.id) ORDER BY id LIMIT 100")],'jobs':[dict(r) for r in c.execute('SELECT id,invoice_id,state,attempts,external_reference,debtor_reference,invoice_status,payment_status,last_error,updated_at FROM accounting_outbox ORDER BY id DESC LIMIT 100')],'events':[dict(r) for r in c.execute('SELECT * FROM accounting_events ORDER BY id DESC LIMIT 100')]}
def save(c,user,body):
 admin(user);old=config(c);version(old,body.get('version'));provider=body.get('provider')
 if provider not in PROVIDERS:raise Problem('Kies een bekende boekhoudprovider.')
 if (provider!=old['provider'] or str(body.get('administration','')).strip()!=old['administration']) and c.execute('SELECT 1 FROM accounting_outbox').fetchone():raise Problem('Er bestaat een factuur-outbox. Providerwissel vereist eerst gecontroleerde aansluiting; geen automatische herexport.',409)
 administration=text(body.get('administration',''),150);env=text(body.get('credential_env',''),100)
 if env and (not env.isidentifier() or not env.isascii() or not env.startswith('ROEFS_ACCOUNTING_')):raise Problem('Gebruik een omgevingsvariabelenaam met prefix ROEFS_ACCOUNTING_. Plaats geen wachtwoord of token in dit veld.')
 enabled=body.get('enabled',False)
 if not isinstance(enabled,bool):raise Problem('Kies expliciet aan of uit voor automatische synchronisatie.')
 if enabled and (provider not in ADAPTERS or old['status'] not in ('Verbinding getest','Actief') or (provider,administration,env)!=(old['provider'],old['administration'],old['credential_env'])):raise Problem('Configureer en test eerst een geïnstalleerde adapter; daarna kan automatische synchronisatie aan.',409)
 c.execute("UPDATE accounting_config SET provider=?,administration=?,credential_env=?,enabled=?,version=version+1,status=?,last_error='' WHERE id=1",(provider,administration,env,int(enabled),'Actief' if enabled else 'Niet actief'));audit(c,user,'accounting_config','settings',0);return overview(c,user)
def snapshot(c,rid):
 inv=record(c,'invoices',rid)
 if inv.get('review_status')!='Goedgekeurd':raise Problem('Alleen expliciet goedgekeurde facturen mogen naar de boekhouding.',409)
 customer=record(c,'customers',inv['customer_id']);lines=[dict(r) for r in c.execute('SELECT * FROM invoice_lines WHERE invoice_id=? ORDER BY id',(rid,))]
 if not lines:raise Problem('Factuur heeft geen gekoppelde factuurregels.',409)
 invoice_fields=('id','version','number','customer_id','amount','net_amount','vat_amount','due_date','review_status','credit_of')
 debtor_fields=('id','version','name','customer_number','billing_address','address','city','email','phone')
 return {'invoice':{k:inv.get(k) for k in invoice_fields},'customer':{k:customer.get(k) for k in debtor_fields},'lines':lines}
def queue(c,user,body):
 admin(user)
 if body.get('confirm') is not True:raise Problem('Bevestig het klaarzetten van de goedgekeurde facturen.')
 ids=body.get('invoice_ids')
 if not isinstance(ids,list) or not 1<=len(ids)<=100 or any(type(x)!=int or x<=0 for x in ids):raise Problem('Kies 1 tot 100 facturen.')
 for rid in dict.fromkeys(ids):
  if c.execute('SELECT 1 FROM accounting_outbox WHERE invoice_id=?',(rid,)).fetchone():continue
  data=snapshot(c,rid);cur=c.execute('INSERT INTO accounting_outbox(invoice_id,snapshot,idempotency_key) VALUES(?,?,?)',(rid,json.dumps(data,sort_keys=True),str(uuid.uuid4())));event(c,'Klaargezet','Goedgekeurde factuur vastgelegd; nog niet extern geboekt.',cur.lastrowid)
 audit(c,user,'accounting_queue','invoices',0);return overview(c,user)
def adapter_for(c,adapter=None):
 if adapter is not None:return adapter
 cfg=config(c);factory=ADAPTERS.get(cfg['provider'])
 if not factory:raise Problem('Niet actief: er is nog geen gevalideerde adapter voor de gekozen boekhoudprovider.',409)
 return factory(cfg)
def test_connection(c,user,adapter=None):
 admin(user);cfg=config(c)
 try:
  result=adapter_for(c,adapter).test_connection(cfg)
  if not isinstance(result,dict) or result.get('ok') is not True:raise Problem('Verbindingstest geeft geen bevestigde toegang.',409)
 except Exception as exc:
  detail=str(exc) if isinstance(exc,Problem) else 'Verbindingstest mislukt; controleer toegang en providerlog.'
  c.execute('BEGIN IMMEDIATE');c.execute("UPDATE accounting_config SET enabled=0,status='Niet actief',last_error=? WHERE id=1",(detail,));event(c,'Verbindingstest mislukt',detail);c.commit();return {'ok':False,'status':'Niet actief','error':detail}
 c.execute('BEGIN IMMEDIATE');c.execute("UPDATE accounting_config SET status='Verbinding getest',last_error='' WHERE id=1");event(c,'Verbindingstest geslaagd','API-toegang getest; dit is geen volledige integratieacceptatie.');c.commit();return {'ok':True,'status':'Verbinding getest'}
def run(c,user,adapter=None):
 admin(user);adapter=adapter_for(c,adapter);processed=0
 for _ in range(25):
  now=time.time();lease=str(uuid.uuid4());c.execute('BEGIN IMMEDIATE')
  row=c.execute("SELECT * FROM accounting_outbox WHERE attempts<8 AND retry_at<=? AND (state IN ('Wachtend','Fout') OR state='Bezig' AND lease_until<?) ORDER BY id LIMIT 1",(now,now)).fetchone()
  if not row:c.commit();break
  row=dict(row);jid=row['id'];c.execute("UPDATE accounting_outbox SET state='Bezig',attempts=attempts+1,lease=?,lease_until=? WHERE id=?",(lease,now+120,jid));c.commit()
  try:
   data=json.loads(row['snapshot'])
   if snapshot(c,row['invoice_id'])!=data:raise Problem('Factuur of debiteurgegevens gewijzigd na klaarzetten. Beoordeel handmatig; geen automatische overschrijving.',409)
   debtor=text(adapter.upsert_debtor(data['customer'],'debtor:'+str(data['customer']['id'])),200,True)
   reference=text(adapter.export_invoice(data,debtor,row['idempotency_key']),200,True)
   status=adapter.invoice_status(reference);inv=text(status['invoice_status'],100,True);payment=text(status['payment_status'],100,True)
   c.execute('BEGIN IMMEDIATE')
   if not c.execute('SELECT 1 FROM accounting_outbox WHERE id=? AND lease=?',(jid,lease)).fetchone():c.rollback();continue
   c.execute("UPDATE accounting_outbox SET state='Verwerkt',external_reference=?,debtor_reference=?,invoice_status=?,payment_status=?,last_error='',lease=NULL,lease_until=NULL,updated_at=CURRENT_TIMESTAMP WHERE id=? AND lease=?",(reference,debtor,inv,payment,jid,lease));event(c,'Verwerkt','Externe referentie en statussen ontvangen.',jid);c.execute("UPDATE accounting_config SET last_sync=?,last_error='' WHERE id=1",(dt.datetime.now(dt.timezone.utc).isoformat(),));c.commit();processed+=1
  except Exception as exc:
   if c.in_transaction:c.rollback()
   detail=str(exc) if isinstance(exc,Problem) else 'Providerverzoek mislukt; opnieuw proberen met dezelfde idempotentiesleutel.'
   c.execute('BEGIN IMMEDIATE')
   if not c.execute('SELECT 1 FROM accounting_outbox WHERE id=? AND lease=?',(jid,lease)).fetchone():c.rollback();continue
   c.execute("UPDATE accounting_outbox SET state='Fout',retry_at=?,last_error=?,lease=NULL,lease_until=NULL,updated_at=CURRENT_TIMESTAMP WHERE id=? AND lease=?",(time.time()+min(3600,30*2**row['attempts']),detail,jid,lease));event(c,'Fout',detail,jid);c.execute('UPDATE accounting_config SET last_error=? WHERE id=1',(detail,));c.commit()
 # Statusinformatie wordt afzonderlijk bewaard: geen verzonnen lokale betaling.
 for row in c.execute("SELECT id,external_reference FROM accounting_outbox WHERE state='Verwerkt' ORDER BY id LIMIT 100").fetchall():
  try:
   status=adapter.invoice_status(row['external_reference']);inv=text(status['invoice_status'],100,True);payment=text(status['payment_status'],100,True)
   c.execute('BEGIN IMMEDIATE');c.execute('UPDATE accounting_outbox SET invoice_status=?,payment_status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(inv,payment,row['id']));event(c,'Status opgehaald','Factuur- en betalingsstatus bijgewerkt.',row['id']);c.execute('UPDATE accounting_config SET last_sync=? WHERE id=1',(dt.datetime.now(dt.timezone.utc).isoformat(),));c.commit()
  except Exception:
   if c.in_transaction:c.rollback()
   c.execute('BEGIN IMMEDIATE');event(c,'Statusfout','Status kon niet worden opgehaald; bestaande status behouden.',row['id']);c.commit()
 return {'processed':processed}
def retry(c,user,jid):
 admin(user);row=c.execute('SELECT state FROM accounting_outbox WHERE id=?',(jid,)).fetchone()
 if not row:raise Problem('Boekhoudtaak ontbreekt.',404)
 if row['state']!='Fout':raise Problem('Alleen een mislukte taak kan opnieuw worden aangeboden.',409)
 c.execute('UPDATE accounting_outbox SET retry_at=0,attempts=0 WHERE id=?',(jid,));event(c,'Herhaling aangevraagd','Dezelfde idempotentiesleutel blijft behouden.',jid);audit(c,user,'accounting_retry','settings',jid);return overview(c,user)


def cycle(c,user,adapter=None):
 """Alleen expliciet geactiveerde configuratie; goedkeuring van facturen blijft vereist."""
 cfg=config(c)
 if not cfg['enabled']:return {'active':False}
 adapter=adapter_for(c,adapter)
 ids=[r[0] for r in c.execute("SELECT id FROM invoices WHERE review_status='Goedgekeurd' AND NOT EXISTS(SELECT 1 FROM accounting_outbox a WHERE a.invoice_id=invoices.id) ORDER BY id LIMIT 100")]
 if ids:
  c.execute('BEGIN IMMEDIATE')
  try:queue(c,user,{'confirm':True,'invoice_ids':ids});c.commit()
  except Exception:c.rollback();raise
 return run(c,user,adapter)
