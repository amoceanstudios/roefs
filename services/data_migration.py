"""Beheerimport met bronidentiteiten, teruggedraaide proefrun en hervatbare batches."""
import base64,collections,datetime as dt,hashlib,json,sqlite3,time,threading
from domain import Problem,NUMBERS,STATUSES
from decimal import Decimal,InvalidOperation
from .common import record,version,text,audit
from .migration_registry import registry,suggest,convert,write
from . import spreadsheets
BATCH=100
PREVIEW_LOCK=threading.Lock()

def migrate(c):
 statements='''
 CREATE TABLE IF NOT EXISTS migration_jobs(id INTEGER PRIMARY KEY,source TEXT NOT NULL,category TEXT NOT NULL,filename TEXT NOT NULL,sha256 TEXT NOT NULL,headers TEXT NOT NULL,mapping TEXT NOT NULL DEFAULT '{}',policy TEXT NOT NULL DEFAULT 'reject',status TEXT NOT NULL DEFAULT 'Geüpload',created_by INTEGER NOT NULL REFERENCES users(id),created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,version INTEGER NOT NULL DEFAULT 1,total INTEGER NOT NULL,cursor INTEGER NOT NULL DEFAULT 0,summary TEXT NOT NULL DEFAULT '{}',elapsed REAL NOT NULL DEFAULT 0,confirmed_by INTEGER REFERENCES users(id),last_error TEXT NOT NULL DEFAULT '');
 CREATE TABLE IF NOT EXISTS migration_rows(job_id INTEGER NOT NULL REFERENCES migration_jobs(id),ordinal INTEGER NOT NULL,line INTEGER NOT NULL,raw TEXT NOT NULL,preview TEXT,result TEXT,PRIMARY KEY(job_id,ordinal));
 CREATE TABLE IF NOT EXISTS migration_links(source TEXT NOT NULL,category TEXT NOT NULL,external_id TEXT NOT NULL,local_id INTEGER NOT NULL,PRIMARY KEY(source,category,external_id),UNIQUE(source,category,local_id));
 CREATE TABLE IF NOT EXISTS migration_profiles(id INTEGER PRIMARY KEY,source TEXT NOT NULL,category TEXT NOT NULL,name TEXT NOT NULL,headers TEXT NOT NULL,mapping TEXT NOT NULL,UNIQUE(source,category,name));
 CREATE INDEX IF NOT EXISTS migration_target ON migration_links(category,local_id);
 '''
 for statement in statements.split(';'):
  if statement.strip():c.execute(statement)

def admin(user):
 if user['role'] not in ('admin','company_admin') or user.get('scope'):raise Problem('Datamigratie is uitsluitend toegankelijk voor onbeperkte beheerders.',403)

def load(c,jid):return record(c,'migration_jobs',jid)
def decoded(job):
 return {**job,**{k:json.loads(job[k]) for k in ('headers','mapping','summary')}}
def detail(c,jid,offset=0):
 job=decoded(load(c,jid));job['username']=c.execute('SELECT username FROM users WHERE id=?',(job['created_by'],)).fetchone()[0];job['results']={r[0]:r[1] for r in c.execute("SELECT json_extract(result,'$.action'),COUNT(*) FROM migration_rows WHERE job_id=? AND result IS NOT NULL GROUP BY json_extract(result,'$.action')",(jid,))};job['rows']=[{'line':r['line'],'values':json.loads(r['raw']),'preview':json.loads(r['preview']) if r['preview'] else None,'result':json.loads(r['result']) if r['result'] else None} for r in c.execute('SELECT * FROM migration_rows WHERE job_id=? ORDER BY ordinal LIMIT 50 OFFSET ?',(jid,max(0,offset)))];return job

def upload(c,user,body,modules):
 meta=registry(modules);category=body.get('category')
 if category not in meta:raise Problem('Kies een ondersteunde gegevenscategorie.')
 source=text(body.get('source',''),100,True);name=text(body.get('filename',''),180,True)
 if '/' in name or '\\' in name or any(ord(x)<32 for x in name):raise Problem('Ongeldige bestandsnaam.')
 try:data=base64.b64decode(body.get('content',''),validate=True)
 except (ValueError,TypeError):raise Problem('Ongeldige bestandsoverdracht.')
 headers,rows=spreadsheets.read(name,data);mapping=suggest(headers,category,meta[category],rows)
 profile=c.execute('SELECT mapping FROM migration_profiles WHERE source=? AND category=? AND headers=? ORDER BY id DESC LIMIT 1',(source,category,json.dumps(headers))).fetchone()
 if profile:mapping=json.loads(profile[0])
 jid=c.execute('INSERT INTO migration_jobs(source,category,filename,sha256,headers,mapping,created_by,total) VALUES(?,?,?,?,?,?,?,?)',(source,category,name,hashlib.sha256(data).hexdigest(),json.dumps(headers),json.dumps(mapping),user['id'],len(rows))).lastrowid
 c.executemany('INSERT INTO migration_rows(job_id,ordinal,line,raw) VALUES(?,?,?,?)',[(jid,i,row['line'],json.dumps(row['values'])) for i,row in enumerate(rows)])
 audit(c,user,'migration_upload','migration_jobs',jid,category);return detail(c,jid)

def mapped(c,job,raw,meta):
 values={target:convert(target,raw[job['headers'].index(source)]) for source,target in job['mapping'].items() if target}
 external=text(values.pop('external_id',''),120,True);explicit=values.pop('existing_id','')
 target=c.execute('SELECT local_id FROM migration_links WHERE source=? AND category=? AND external_id=?',(job['source'],job['category'],external)).fetchone();rid=target[0] if target else None
 if explicit:
  if not explicit.isdigit() or int(explicit)<=0:raise Problem('Bestaand intern nummer moet een positief getal zijn.')
  if rid and rid!=int(explicit):raise Problem('Externe sleutel is al aan een ander intern record gekoppeld.',409)
  rid=int(explicit)
 for field,parent in meta['relations'].items():
  if values.get(field):
   link=c.execute('SELECT local_id FROM migration_links WHERE source=? AND category=? AND external_id=?',(job['source'],parent,values[field])).fetchone()
   if not link:raise Problem(f'{field}: ontbrekende relatie met {parent}, bronsleutel {values[field]}. Importeer de ouder eerst.',409)
   record(c,parent,link[0]);values[field]=str(link[0])
 return external,rid,values

def apply_row(c,user,job,raw,modules,expected=None):
 meta=registry(modules)[job['category']];external,rid,values=mapped(c,job,raw,meta);table=job['category'];old=record(c,table,rid) if rid else None
 if expected is not None and (expected.get('target')!=rid or expected.get('version')!=(old.get('version') if old else None)):raise Problem('Doelrecord gewijzigd sinds de proefrun. Stop en voer een nieuwe proefrun uit.',409)
 if 'status' in values and not values['status']:values['status']=STATUSES.get(table,['Actief'])[0]
 if table=='employees' and values.get('emergency_available')=='':values['emergency_available']='0'
 if table=='customers' and values.get('customer_number')=='':values.pop('customer_number')
 if table in ('shifts','hours') and values.get('break_minutes')=='' and (table=='shifts' or values.get('starts_at')):values['break_minutes']='0'
 if table=='articles':
  for key,default in [('rate','0'),('vat_rate','21')]:
   if key in values and not values[key]:values[key]=default
 def equal(field,a,b):
  if str(a if a is not None else '')==str(b):return True
  if field in set(NUMBERS)|{'capacity','break_minutes','rate','vat_rate','area'}:
   try:return Decimal(str(a).replace(',','.'))==Decimal(str(b).replace(',','.'))
   except (InvalidOperation,ValueError):pass
  return False
 if old:
  changed=any(not equal(k,old.get(k),v) for k,v in values.items())
  if not changed:action='Ongewijzigd';result=old
  elif job['policy']=='skip':action='Overgeslagen';result=old
  elif job['policy']=='update':action='Bijgewerkt';result=write(c,user,table,values,modules,rid)
  else:raise Problem('Bestaand record wijkt af. Kies expliciet bijwerken of overslaan.',409)
 else:action='Nieuw';result=write(c,user,table,values,modules)
 c.execute('INSERT INTO migration_links(source,category,external_id,local_id) VALUES(?,?,?,?) ON CONFLICT(source,category,external_id) DO NOTHING',(job['source'],table,external,result['id']))
 return {'action':action,'external_id':external,'target':rid,'version':old.get('version') if old else None,'local_id':result['id']}

def preview(c,user,jid,body,modules):
 if not PREVIEW_LOCK.acquire(blocking=False):raise Problem('Er loopt al een testmigratie. Probeer het na afronding opnieuw.',429)
 try:return _preview(c,user,jid,body,modules)
 finally:PREVIEW_LOCK.release()

def _preview(c,user,jid,body,modules):
 rawjob=load(c,jid);version(rawjob,body.get('version'))
 if rawjob['status']=='Bezig' or rawjob['cursor'] and rawjob['status']!='Onderbroken':raise Problem('Pauzeer een begonnen import vóór een nieuwe proefrun.',409)
 mapping=body.get('mapping');meta=registry(modules)[rawjob['category']];headers=json.loads(rawjob['headers']);policy=body.get('policy','reject')
 if not isinstance(mapping,dict) or any(k not in headers or v not in meta['fields'] for k,v in mapping.items()) or len(set(mapping.values()))!=len(mapping):raise Problem('Koppel iedere doelkolom hoogstens één keer aan een bekende bronkolom.')
 if set(meta['required'])-set(mapping.values()):raise Problem('Verplichte velden ontbreken: '+', '.join(meta['labels'][f] for f in meta['required'] if f not in mapping.values()))
 if rawjob['cursor'] and mapping!=json.loads(rawjob['mapping']):raise Problem('Kolomkoppelingen van een gedeeltelijk uitgevoerde import mogen niet wijzigen.',409)
 if policy not in ('reject','skip','update'):raise Problem('Kies een geldig conflictbeleid.')
 job={**decoded(rawjob),'mapping':mapping,'policy':policy};rows=c.execute('SELECT ordinal,line,raw FROM migration_rows WHERE job_id=? AND ordinal>=? ORDER BY ordinal',(jid,rawjob['cursor'])).fetchall();counts=collections.Counter();results=[];ids=set();started=time.monotonic()
 main=c;c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
 try:main.backup(c);c.execute('PRAGMA foreign_keys=ON')
 except Exception:c.close();raise
 c.execute('SAVEPOINT migration_preview')
 try:
  for row in rows:
   c.execute('SAVEPOINT migration_row')
   try:
    values=json.loads(row['raw']);eid=values[headers.index(next(k for k,v in mapping.items() if v=='external_id'))].strip()
    if eid in ids:raise Problem('Dubbele externe sleutel in dit bestand: '+eid,409)
    ids.add(eid);result=apply_row(c,user,job,values,modules);c.execute('RELEASE migration_row')
   except (Problem,sqlite3.IntegrityError,ValueError,TypeError,KeyError) as error:
    c.execute('ROLLBACK TO migration_row');c.execute('RELEASE migration_row');result={'action':'Fout','error':str(error) if isinstance(error,Problem) else 'Ongeldige veldwaarde of conflicterende relatie.','missing_relation':'ontbrekende relatie' in str(error),'duplicate':eid in ids and 'Dubbele externe sleutel' in str(error)}
   results.append((json.dumps(result,ensure_ascii=False),jid,row['ordinal']));counts[result['action']]+=1
 finally:
  c.execute('ROLLBACK TO migration_preview');c.execute('RELEASE migration_preview');c.close();c=main
 if not c.in_transaction:c.execute('BEGIN IMMEDIATE')
 version(load(c,jid),body.get('version'))
 c.executemany('UPDATE migration_rows SET preview=?,result=NULL WHERE job_id=? AND ordinal=?',results)
 summary={k:counts[k] for k in ('Nieuw','Bijgewerkt','Ongewijzigd','Overgeslagen','Fout')};summary['Ontbrekende_relaties']=sum(json.loads(x[0]).get('missing_relation',False) for x in results);summary['Reeds_verwerkt']=rawjob['cursor'];summary['Duplicaten']=sum(json.loads(x[0]).get('duplicate',False) for x in results)
 status='Geblokkeerd' if summary['Fout'] else 'Gecontroleerd'
 c.execute("UPDATE migration_jobs SET mapping=?,policy=?,status=?,summary=?,version=version+1,last_error='',elapsed=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(json.dumps(mapping),policy,status,json.dumps(summary),time.monotonic()-started,jid))
 profile=text(body.get('profile_name',''),100)
 if profile and not summary['Fout']:c.execute('INSERT INTO migration_profiles(source,category,name,headers,mapping) VALUES(?,?,?,?,?) ON CONFLICT(source,category,name) DO UPDATE SET headers=excluded.headers,mapping=excluded.mapping',(job['source'],job['category'],profile,json.dumps(headers),json.dumps(mapping)))
 audit(c,user,'migration_preview','migration_jobs',jid,status);return detail(c,jid)

def begin(c,user,jid,body):
 job=load(c,jid);version(job,body.get('version'))
 if job['status']!='Gecontroleerd' or json.loads(job['summary']).get('Fout'):raise Problem('Voer eerst een geslaagde proefrun uit.',409)
 if body.get('confirm') is not True:raise Problem('Bevestig de definitieve import expliciet.')
 c.execute("UPDATE migration_jobs SET status='Bezig',confirmed_by=?,version=version+1,elapsed=0,updated_at=CURRENT_TIMESTAMP WHERE id=?",(user['id'],jid));audit(c,user,'migration_confirm','migration_jobs',jid);return detail(c,jid)

def batch(c,user,jid,body,modules):
 job=decoded(load(c,jid));version(job,body.get('version'))
 if job['status']=='Voltooid':return detail(c,jid)
 if job['status'] not in ('Bezig','Onderbroken'):raise Problem('Import is niet bevestigd of niet hervatbaar.',409)
 rows=c.execute('SELECT ordinal,raw,preview FROM migration_rows WHERE job_id=? AND ordinal>=? ORDER BY ordinal LIMIT ?',(jid,job['cursor'],BATCH)).fetchall();started=time.monotonic();results=[];error=None
 c.execute('SAVEPOINT migration_batch')
 try:
  for row in rows:
   result=apply_row(c,user,job,json.loads(row['raw']),modules,json.loads(row['preview']));results.append((json.dumps(result),jid,row['ordinal']))
  c.executemany('UPDATE migration_rows SET result=? WHERE job_id=? AND ordinal=?',results);c.execute('RELEASE migration_batch')
 except (Problem,sqlite3.IntegrityError,ValueError,TypeError,KeyError) as exc:
  c.execute('ROLLBACK TO migration_batch');c.execute('RELEASE migration_batch');error=str(exc) if isinstance(exc,Problem) else 'Importbatch bevat conflicterende of ongeldige gegevens.'
 cursor=job['cursor']+(len(results) if not error else 0);status='Onderbroken' if error else 'Voltooid' if cursor==job['total'] else 'Bezig'
 c.execute('UPDATE migration_jobs SET cursor=?,status=?,last_error=?,version=version+1,elapsed=elapsed+?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(cursor,status,error or '',time.monotonic()-started,jid))
 audit(c,user,'migration_batch','migration_jobs',jid,f'{status}: {cursor}/{job["total"]}')
 result=detail(c,jid)
 if error:result['error_detail']=error
 return result

def route(h,c,user,parts,method,body,query,modules):
 admin(user)
 if len(parts)==1 and method=='GET':
  jobs=[decoded(dict(r)) for r in c.execute('SELECT j.*,u.username FROM migration_jobs j JOIN users u ON u.id=j.created_by ORDER BY j.id DESC LIMIT 100')]
  totals=dict(c.execute("SELECT status,COUNT(*) FROM migration_jobs GROUP BY status"));return {'jobs':jobs,'totals':totals,'record_totals':{r[0]:r[1] for r in c.execute("SELECT json_extract(result,'$.action'),COUNT(*) FROM migration_rows WHERE result IS NOT NULL GROUP BY json_extract(result,'$.action')")},'category_status':[dict(r) for r in c.execute('SELECT category,status,COUNT(*) AS imports,SUM(cursor) AS processed FROM migration_jobs GROUP BY category,status')],'categories':registry(modules),'limits':{'bytes':spreadsheets.MAX_BYTES,'rows':spreadsheets.MAX_ROWS,'batch':BATCH},'profiles':[dict(r) for r in c.execute('SELECT id,source,category,name FROM migration_profiles ORDER BY id DESC')]}
 if parts==['migration','uploads'] and method=='POST':return upload(c,user,body,modules)
 if len(parts)>=2 and parts[1].isdigit():
  jid=int(parts[1])
  if len(parts)==2 and method=='GET':return detail(c,jid,int(query.get('offset','0')))
  if len(parts)==3 and method=='POST':
   if parts[2]=='pause':
    job=load(c,jid);version(job,body.get('version'))
    if job['status']!='Bezig':raise Problem('Alleen een actieve import kan worden gepauzeerd.',409)
    c.execute("UPDATE migration_jobs SET status='Onderbroken',version=version+1,last_error='Gepauzeerd door beheer' WHERE id=?",(jid,));audit(c,user,'migration_pause','migration_jobs',jid);return detail(c,jid)
   if parts[2]=='preview':return preview(c,user,jid,body,modules)
   if parts[2]=='confirm':return begin(c,user,jid,body)
   if parts[2]=='batch':return batch(c,user,jid,body,modules)
 raise Problem('Migratiehandeling niet gevonden.',404)

def template(category,modules,format):
 from .migration_registry import LABEL
 from .reporting import csv_bytes
 meta=registry(modules).get(category)
 if not meta:raise Problem('Onbekende templatecategorie.',404)
 defaults={'external_id':'DEMO-001','name':'Fictief voorbeeld '+meta['label'],'description':'Fictieve voorbeeldomschrijving','instructions':'Fictieve werkinstructie','email':'voorbeeld@fictief.invalid','date':'2030-02-04','start_date':'2030-01-01','end_date':'2030-12-31','start_time':'08:00','end_time':'09:00','hours':'1','contract_hours':'38','monthly_value':'100','capacity':'1','score':'8','title':'Fictieve melding','severity':'Normaal','subject':'Fictief contact','code':'DEMO-001','quantity':'1','item':'Fictief artikel','unit':'stuk','plate':'DEMO-01','model':'Fictief model','category':'Fictief','reference':'DEMO-001','author':'Fictieve medewerker','message':'Fictief bericht','inspector':'Fictieve inspecteur','key_code':'DEMO-001','holder':'Fictieve medewerker','type':'Fictief','amount':'100'}
 example={field:('DEMO-001' if field in meta['relations'] else defaults.get(field,'Fictief voorbeeld')) if field in meta['required'] else '' for field in meta['fields']}
 if 'status' in example and meta['statuses']:example['status']=meta['statuses'][0]
 if format=='csv':return csv_bytes([example],meta['fields']),'text/csv; charset=utf-8'
 if format!='xlsx':raise Problem('Kies csv of xlsx.')
 explanation=[['Veld','Betekenis','Verplicht','Formaat / toegestane waarden']]
 for field in meta['fields']:
  description=meta['labels'][field];fmt='Tekst; maximaal 2000 tekens'
  if field in meta['relations']:fmt='Externe sleutel uit '+meta['relations'][field]+' binnen hetzelfde bronsysteem; ouder eerst importeren'
  elif field=='external_id':fmt='Unieke bronidentiteit, tekst; maximaal 120 tekens; voorloopnullen behouden'
  elif field=='existing_id':fmt='Optioneel bestaand intern nummer; alleen invullen om expliciet een bestaand record te koppelen'
  elif field=='status':fmt=', '.join(meta['statuses'])
  elif field=='date' or field.endswith('_date'):fmt='JJJJ-MM-DD of DD-MM-JJJJ'
  elif field.endswith('_time'):fmt='UU:MM'
  elif field in ('starts_at','ends_at'):fmt='ISO-datum/tijd met Europe/Amsterdam-offset; voorbeeld 2030-02-04T08:00:00+01:00'
  explanation.append([field,description,'Ja' if field in meta['required'] else 'Nee',fmt])
 return spreadsheets.xlsx([('Gegevens',[meta['fields'],[example[x] for x in meta['fields']]]),('Uitleg',explanation)]),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

def report(c,jid):
 from .reporting import csv_bytes
 job=decoded(load(c,jid));rows=[]
 administrator=c.execute('SELECT username FROM users WHERE id=?',(job['created_by'],)).fetchone()[0]
 for row in c.execute('SELECT * FROM migration_rows WHERE job_id=? ORDER BY ordinal',(jid,)):
  predicted=json.loads(row['preview']) if row['preview'] else {};actual=json.loads(row['result']) if row['result'] else {}
  rows.append({'Migratie':jid,'Beheerder':administrator,'Aangemaakt':job['created_at'],'Bijgewerkt':job['updated_at'],'Uitvoeringstijd seconden':job['elapsed'],'Bestand':job['filename'],'Bron':job['source'],'Categorie':job['category'],'Rij':row['line'],'Externe sleutel':actual.get('external_id',predicted.get('external_id','')),'Proefrun':predicted.get('action',''),'Resultaat':actual.get('action','Nog niet geïmporteerd'),'Intern nummer':actual.get('local_id',''),'Fout':predicted.get('error',''),'Importstatus':job['status'],'Laatst gemelde fout':job['last_error']})
 return csv_bytes(rows,list(rows[0]) if rows else ['Geen rijen'])
