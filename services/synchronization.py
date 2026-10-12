"""Duurzame pull/push met leases, outbox, versies en expliciete conflicten.
Netwerkverzoeken vinden buiten SQLite-schrijftransacties plaats.
"""
import logging
import datetime as dt,hashlib,json,os,re,sqlite3,threading,time,uuid
from domain import Problem,validate
from .common import record,insert,update,audit,text,notify
from .connectors.generic import Connector,RemoteError,validate_url
CATEGORIES={'customers':'Klantgegevens','employees':'Medewerkersgegevens','articles':'Artikelen en materialen','objects':'Werklocaties','contracts':'Contracten','workorders':'Opdrachten','shifts':'Diensten','hours':'Urenregistratie','invoices':'Factuurgegevens'}
PROVIDERS={'generic':{'name':'Generieke JSON-connector','prepared':True,'notice':'Vereist roefs-sync-v1 API-contract; daadwerkelijke doelsystemen afzonderlijk valideren.'},'afas':{'name':'AFAS','prepared':False,'notice':'Niet actief: omgevings-URL, token en Get/UpdateConnector-schema ontbreken.'},'exact':{'name':'Exact Online','prepared':False,'notice':'Niet actief: OAuth-app, administratie-ID, veldmapping en API-toegang ontbreken.'},'dynamics':{'name':'Microsoft Dynamics 365','prepared':False,'notice':'Niet actief: tenant, OAuth-app, entiteiten en API-toegang ontbreken.'}}
POLICIES={'roefs':'ROEFS ONE leidend (export)','external':'Extern systeem leidend (import)','both':'Beide systemen; gelijktijdige wijzigingen handmatig beoordelen','off':'Niet synchroniseren'}
REFERENCES={'customer_id':'customers','employee_id':'employees','object_id':'objects','contract_id':'contracts','shift_id':'shifts'}
ART_FIELDS=['code','name','unit','rate','vat_rate','status']
SYSTEM={'id':0,'username':'Automatische synchronisatie','role':'admin'}

def now():return dt.datetime.now(dt.timezone.utc)
def stamp(value=None):return (value or now()).isoformat()
def connect(db):
    c=sqlite3.connect(db,timeout=15);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');c.execute('PRAGMA journal_mode=WAL');return c

def canonical(fields):return json.dumps(fields,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def digest(fields):return hashlib.sha256(canonical(fields).encode()).hexdigest()
def fields_for(category,modules):return ART_FIELDS if category=='articles' else modules[category][1]
def local_payload(row,category,modules):return {k:row.get(k,'') for k in fields_for(category,modules)}

def validate_remote(item,category,modules):
    if not isinstance(item,dict) or set(item)-{'id','revision','fields','deleted','roefs_id'}:raise RemoteError('Onbekende velden in externe record-envelop.',False)
    eid=text(item.get('id',''),200,True);revision=text(item.get('revision',''),200,True)
    if eid in ('.','..') or '/' in eid or '\\' in eid or any(ord(ch)<32 for ch in eid):raise RemoteError('Ongeldige externe recordidentiteit.',False)
    if '\r' in revision or '\n' in revision:raise RemoteError('Ongeldige externe versie.',False)
    fields=item.get('fields',{})
    if not isinstance(fields,dict) or set(fields)-set(fields_for(category,modules)):raise RemoteError('Externe velden passen niet bij de geconfigureerde categorie.',False)
    if len(canonical(fields))>30000:raise RemoteError('Extern record overschrijdt de veldlimiet.',False)
    return eid,revision,fields

def event(c,cid,run,category,action,detail,local_id=None,external_id=None):
    insert(c,'sync_events',{'run_id':run,'connection_id':cid,'category':category,'action':action,'detail':detail,'local_id':local_id,'external_id':external_id})
def conflict(c,cid,run,category,item,local,reason):
    eid=str(item['id']);rev=str(item['revision']);lv=local['version'] if local else 0
    c.execute('INSERT OR IGNORE INTO sync_conflicts(connection_id,category,local_id,external_id,remote_revision,remote_json,local_version,reason) VALUES(?,?,?,?,?,?,?,?)',(cid,category,local['id'] if local else None,eid,rev,canonical(item),lv,reason))
    event(c,cid,run,category,'Conflict',reason,local['id'] if local else None,eid)
    notify(c,f'sync:{cid}:{category}:{eid}:{rev}:{lv}','Synchronisatieconflict: '+CATEGORIES[category],'integrations',roles={'admin','company_admin'})
    return 'conflicts'

def translate(c,cid,fields,outbound):
    result=dict(fields)
    for f,category in REFERENCES.items():
        if not fields.get(f):continue
        key='local_id' if outbound else 'external_id'
        link=c.execute(f'SELECT * FROM sync_links WHERE connection_id=? AND category=? AND {key}=?',(cid,category,fields[f])).fetchone()
        if not link:raise Problem('Koppeling ontbreekt voor '+category+'; synchroniseer eerst de afhankelijkheid.')
        result[f]=link['external_id'] if outbound else str(link['local_id'])
    return result

def save_import(c,cid,category,fields,modules,local=None):
    data=translate(c,cid,fields,False)
    if category=='articles':
        from .common import money
        for k in ART_FIELDS:data[k]=text(data.get(k,(local or {}).get(k,'')))
        if not data['code'] or not data['name'] or data['status'] not in ('Actief','Inactief'):raise Problem('Artikelcode, naam en geldige status zijn verplicht.')
        data['rate']=str(money(data['rate']));data['vat_rate']=str(money(data['vat_rate']))
        if data['vat_rate'] not in ('0','9','21'):raise Problem('Ongeldig btw-percentage.')
        if local:data['version']=local['version']+1
    else:
        if local and (local.get('workflow') or local.get('workorder_id')):raise Problem('Gekoppelde procesgegevens vereisen beoordeling in ROEFS ONE; geen externe overschrijving.')
        data=validate(c,category,data,modules[category][1],local)
    # Semantische duplicaten worden niet automatisch gekoppeld: voorleggen aan beheer.
    if not local:
        keys={'customers':'name','employees':'email','articles':'code','invoices':'number'}.get(category)
        if keys and data.get(keys) and c.execute('SELECT 1 FROM '+category+' WHERE lower(trim('+keys+'))=lower(trim(?))',(data[keys],)).fetchone():raise Problem('Mogelijk dubbel record; maak eerst een expliciete recordkoppeling.')
    if local:update(c,category,local['id'],data);rid=local['id']
    else:rid=insert(c,category,data)
    audit(c,SYSTEM,'sync_import',category,rid,'Koppeling #'+str(cid));return record(c,category,rid)

def link_state(c,cid,category,eid,local,revision,fields):
    c.execute('INSERT INTO sync_links(connection_id,category,external_id,local_id,local_version,remote_revision,remote_hash) VALUES(?,?,?,?,?,?,?) ON CONFLICT(connection_id,category,external_id) DO UPDATE SET local_version=excluded.local_version,remote_revision=excluded.remote_revision,remote_hash=excluded.remote_hash',(cid,category,eid,local['id'],local['version'],revision,digest(fields)))

def pull_item(c,cid,run,category,policy,item,modules):
    eid,revision,fields=validate_remote(item,category,modules);c.execute('BEGIN IMMEDIATE')
    try:
        link=c.execute('SELECT * FROM sync_links WHERE connection_id=? AND category=? AND external_id=?',(cid,category,eid)).fetchone()
        local=dict(c.execute('SELECT * FROM '+category+' WHERE id=?',(link['local_id'],)).fetchone() or {}) if link else None
        open_conflict=c.execute("SELECT * FROM sync_conflicts WHERE connection_id=? AND category=? AND external_id=? AND status='Open' ORDER BY id DESC LIMIT 1",(cid,category,eid)).fetchone()
        if open_conflict:
            if local and (local['version']!=open_conflict['local_version'] or revision!=open_conflict['remote_revision']):
                c.execute('UPDATE sync_conflicts SET remote_revision=?,remote_json=?,local_version=? WHERE id=?',(revision,canonical(item),local['version'],open_conflict['id']))
            c.commit();return None
        if item.get('deleted'):result=conflict(c,cid,run,category,item,local,'Extern record verwijderd. Lokale gegevens blijven behouden; beoordeel archivering handmatig.')
        elif link and not local:result=conflict(c,cid,run,category,item,None,'Lokale record ontbreekt; herstel of koppel expliciet opnieuw.')
        elif link:
            local_changed=local['version']!=link['local_version'];remote_changed=digest(fields)!=link['remote_hash']
            if local_changed and remote_changed:result=conflict(c,cid,run,category,item,local,'Beide systemen hebben het record gewijzigd; geen automatische overschrijving.')
            elif remote_changed and policy=='roefs':result=conflict(c,cid,run,category,item,local,'Extern gewijzigd terwijl ROEFS ONE leidend is.')
            elif local_changed and policy=='external':result=conflict(c,cid,run,category,item,local,'Lokaal gewijzigd terwijl het externe systeem leidend is.')
            elif remote_changed:
                try:local=save_import(c,cid,category,fields,modules,local)
                except Problem as exc:result=conflict(c,cid,run,category,item,local,str(exc))
                else:link_state(c,cid,category,eid,local,revision,fields);event(c,cid,run,category,'Import','Bestaand record bijgewerkt.',local['id'],eid);result='imported'
            else:
                c.execute('UPDATE sync_links SET remote_revision=? WHERE id=?',(revision,link['id']));result=None
        elif policy=='roefs':result=conflict(c,cid,run,category,item,None,'Extern record is nog niet gekoppeld; ROEFS ONE is leidend. Koppel het bestaande record expliciet.')
        else:
            try:local=save_import(c,cid,category,fields,modules)
            except Problem as exc:result=conflict(c,cid,run,category,item,None,str(exc))
            else:link_state(c,cid,category,eid,local,revision,fields);event(c,cid,run,category,'Import','Nieuw record opgeslagen.',local['id'],eid);result='imported'
        c.commit();return result
    except Exception:c.rollback();raise

def enqueue(c,cid,category,modules):
    c.execute('BEGIN IMMEDIATE')
    try:
        for raw in c.execute('SELECT * FROM '+category+' ORDER BY id').fetchall():
            row=dict(raw);link=c.execute('SELECT * FROM sync_links WHERE connection_id=? AND category=? AND local_id=?',(cid,category,row['id'])).fetchone()
            if link and row['version']==link['local_version']:continue
            if c.execute("SELECT 1 FROM sync_conflicts WHERE connection_id=? AND category=? AND (local_id=? OR local_id IS NULL) AND status='Open'",(cid,category,row['id'])).fetchone():continue
            # Eerst een onzekere eerdere poging afmaken, ook wanneer lokaal daarna is gewijzigd.
            if c.execute("SELECT 1 FROM sync_outbox WHERE connection_id=? AND category=? AND local_id=? AND status IN ('Wacht','Uitval')",(cid,category,row['id'])).fetchone():continue
            payload=translate(c,cid,local_payload(row,category,modules),True)
            key=hashlib.sha256(f'{cid}:{category}:{row["id"]}:{row["version"]}'.encode()).hexdigest()
            c.execute('INSERT OR IGNORE INTO sync_outbox(connection_id,category,local_id,local_version,external_id,remote_revision,payload,idempotency_key) VALUES(?,?,?,?,?,?,?,?)',(cid,category,row['id'],row['version'],link['external_id'] if link else None,link['remote_revision'] if link else None,canonical({'fields':payload,'roefs_id':str(row['id'])}),key))
        c.commit()
    except Exception:c.rollback();raise

def push_pending(c,cid,run,category,adapter,modules,owner=None):
    exported=0
    for raw in c.execute("SELECT * FROM sync_outbox WHERE connection_id=? AND category=? AND status='Wacht' ORDER BY id",(cid,category)).fetchall():
        job=dict(raw)
        if owner:
            changed=c.execute('UPDATE sync_connections SET lease_until=? WHERE id=? AND lease_owner=?',(stamp(now()+dt.timedelta(seconds=120)),cid,owner)).rowcount;c.commit()
            if not changed:raise RemoteError('Workerlease verloren; verwerking wordt hervat door de actieve worker.')
        if c.execute("SELECT 1 FROM sync_conflicts WHERE connection_id=? AND category=? AND local_id=? AND status='Open'",(cid,category,job['local_id'])).fetchone():continue
        try:
            response=adapter.put(category,json.loads(job['payload']),job['idempotency_key'],job['external_id'],job['remote_revision']);eid,revision,fields=validate_remote(response,category,modules)
            if job['external_id'] and eid!=job['external_id']:raise RemoteError('API wijzigde de externe recordidentiteit.',False)
            if digest(fields)!=digest(json.loads(job['payload'])['fields']):raise RemoteError('API bevestigt andere veldwaarden dan verzonden; handmatige controle vereist.',False)
        except RemoteError as exc:
            c.execute('BEGIN IMMEDIATE');c.execute('UPDATE sync_outbox SET attempts=attempts+1,last_error=? WHERE id=?',(str(exc),job['id']))
            if exc.status in (409,412):
                local=record(c,category,job['local_id']);conflict(c,cid,run,category,{'id':job['external_id'] or 'onbekend-'+str(job['id']),'revision':job['remote_revision'] or 'onbekend','fields':json.loads(job['payload'])['fields']},local,'Externe versie veranderde tijdens verzenden. Vernieuw extern en beoordeel het conflict.');c.execute("UPDATE sync_outbox SET status='Conflict' WHERE id=?",(job['id'],))
            elif exc.status not in (401,403) and (not exc.retryable or job['attempts']+1>=10):
                c.execute("UPDATE sync_outbox SET status='Uitval' WHERE id=?",(job['id'],));event(c,cid,run,category,'Uitval','Verzending vereist handmatige beoordeling; oorspronkelijke sleutel blijft behouden.',job['local_id'],job['external_id'])
            c.commit();raise
        c.execute('BEGIN IMMEDIATE')
        try:
            local=record(c,category,job['local_id']);saved={**local,'version':job['local_version']}
            link_state(c,cid,category,eid,saved,revision,fields);c.execute("UPDATE sync_outbox SET status='Verwerkt',attempts=attempts+1,last_error=NULL WHERE id=?",(job['id'],));event(c,cid,run,category,'Export','Extern bevestigd met idempotentiesleutel.',job['local_id'],eid);c.commit();exported+=1
        except Exception:c.rollback();raise
    return exported

def run_connection(db,cid,modules,force=False):
    """Eén worker per koppeling; SQL-lease werkt ook tussen meerdere processen."""
    c=connect(db);owner=uuid.uuid4().hex;run=None;counts={'imported':0,'exported':0,'conflicts':0}
    try:
        c.execute('BEGIN IMMEDIATE');config=record(c,'sync_connections',cid)
        if not config['enabled']:c.rollback();return {'status':'Niet actief'}
        if config['lease_until'] and config['lease_until']>stamp():c.rollback();return {'status':'Al bezig'}
        if not force and config['next_run'] and config['next_run']>stamp():c.rollback();return {'status':'Nog niet gepland'}
        c.execute('UPDATE sync_connections SET lease_owner=?,lease_until=? WHERE id=?',(owner,stamp(now()+dt.timedelta(seconds=120)),cid))
        run=insert(c,'sync_runs',{'connection_id':cid,'started_at':stamp()});c.commit()
        if config['provider']!='generic':raise RemoteError('Providerconnector is voorbereid maar nog niet geconfigureerd of gevalideerd.',False)
        adapter=Connector(config);caps=adapter.capabilities();policies=json.loads(config['policies'])
        categories=caps.get('categories',[])
        for category in CATEGORIES:
            policy=policies.get(category,'off')
            if policy=='off':continue
            if category not in categories:raise RemoteError('Externe API ondersteunt categorie '+category+' niet.',False)
            if policy in ('roefs','both') and not all(caps.get(k) is True for k in ('idempotency','conditional_updates','write')):raise RemoteError('Externe API mist veilige tweerichtingsvoorwaarden: schrijfondersteuning, idempotentie of versiecontrole.',False)
            # Een mogelijk wel verwerkte vorige verzending wordt met dezelfde sleutel hervat vóór import.
            if policy in ('roefs','both'):counts['exported']+=push_pending(c,cid,run,category,adapter,modules,owner)
            saved_cursor=c.execute('SELECT cursor FROM sync_cursors WHERE connection_id=? AND category=?',(cid,category)).fetchone()
            incremental=caps.get('delta_tokens') is True
            for items in adapter.list_records(category,saved_cursor[0] if saved_cursor and incremental else None):
                c.execute('UPDATE sync_connections SET lease_until=? WHERE id=? AND lease_owner=?',(stamp(now()+dt.timedelta(seconds=120)),cid,owner));c.commit()
                for item in items:
                    result=pull_item(c,cid,run,category,policy,item,modules)
                    if result:counts[result]+=1
            if incremental and adapter.checkpoint is not None:
                c.execute('INSERT INTO sync_cursors VALUES(?,?,?) ON CONFLICT(connection_id,category) DO UPDATE SET cursor=excluded.cursor',(cid,category,adapter.checkpoint));c.commit()
            if policy in ('roefs','both'):
                enqueue(c,cid,category,modules);counts['exported']+=push_pending(c,cid,run,category,adapter,modules,owner)
        c.execute('BEGIN IMMEDIATE');finished=stamp();open_count=c.execute("SELECT COUNT(*) FROM sync_conflicts WHERE connection_id=? AND status='Open'",(cid,)).fetchone()[0];dead=c.execute("SELECT COUNT(*) FROM sync_outbox WHERE connection_id=? AND status='Uitval'",(cid,)).fetchone()[0];status='Uitval' if dead else 'Conflicten' if open_count else 'Geslaagd'
        update(c,'sync_runs',run,{**counts,'status':status,'finished_at':finished});c.execute('UPDATE sync_connections SET last_run=?,last_success=?,last_error=NULL,failures=0,next_run=?,lease_owner=NULL,lease_until=NULL WHERE id=? AND lease_owner=?',(finished,finished if status in ('Geslaagd','Conflicten') else config['last_success'],stamp(now()+dt.timedelta(seconds=config['interval_seconds'])),cid,owner));c.commit();return {'status':status,**counts}
    except Exception as exc:
        c.rollback()
        # Geen externe responsebody, toegangsgegevens of stacktrace in het gebruikerslogboek.
        detail=str(exc) if isinstance(exc,(Problem,RemoteError)) else 'Synchronisatie afgebroken door een interne validatie- of databasefout. Controleer het technische proceslog.'
        if run:
            counts={key:c.execute('SELECT COUNT(*) FROM sync_events WHERE run_id=? AND action=?',(run,action)).fetchone()[0] for key,action in [('imported','Import'),('exported','Export'),('conflicts','Conflict')]}
            c.execute('BEGIN IMMEDIATE');config=record(c,'sync_connections',cid);failures=config['failures']+1;delay=min(3600,max(30,config['interval_seconds'])*2**min(failures-1,6));update(c,'sync_runs',run,{**counts,'status':'Mislukt','error':detail,'finished_at':stamp()});event(c,cid,run,None,'Fout',detail)
            if isinstance(exc,RemoteError) and exc.status in (401,403):
                c.execute('UPDATE sync_connections SET enabled=0 WHERE id=?',(cid,));notify(c,f'sync-auth:{cid}:{run}','Koppeling gepauzeerd: controleer API-toegang.','integrations',roles={'admin','company_admin'})
            c.execute('UPDATE sync_connections SET last_run=?,last_error=?,failures=?,next_run=?,lease_owner=NULL,lease_until=NULL WHERE id=? AND lease_owner=?',(stamp(),detail,failures,stamp(now()+dt.timedelta(seconds=delay)),cid,owner));c.commit()
        return {'status':'Mislukt','error':detail,**counts}
    finally:c.close()

def start_worker(db,modules,stop=None):
    stop=stop or threading.Event()
    def loop():
        while not stop.is_set():
            try:
                with connect(db) as c:
                    from .notifications import daily
                    daily(c)
                    from .documents import retention
                    retention(c,db)
                    ids=[x[0] for x in c.execute('SELECT id FROM sync_connections WHERE enabled=1 AND (next_run IS NULL OR next_run<=?) ORDER BY id',(stamp(),))]
                c.close()
                for cid in ids:
                    if stop.is_set():break
                    run_connection(db,cid,modules)
            except Exception as exc:logging.error('Achtergrondcyclus mislukt (%s); volgende cyclus probeert opnieuw.',type(exc).__name__) # Geen persoonsgegevens of secrets loggen.
            stop.wait(2)
    worker=threading.Thread(target=loop,name='roefs-automatic-sync',daemon=True);worker.start();return stop,worker

def safe_config(row):
    result=dict(row);result['policies']=json.loads(result['policies']);result['secret_available']=bool(os.environ.get(result['secret_env'],'')) if result['secret_env'] else False
    result['state']='Actief' if result['enabled'] else 'Niet actief';result['external_verified']=bool(result['last_success']);return result

def save_config(c,user,body,cid=None):
    from .common import version
    if user['role'] not in {'admin','company_admin'}:raise Problem('Alleen beheer kan koppelingen configureren.',403)
    old=record(c,'sync_connections',cid) if cid else {}
    if old:version(old,body.get('version'))
    if old.get('lease_until') and old['lease_until']>stamp():raise Problem('Synchronisatie is bezig. Wacht tot deze is afgerond voordat je de configuratie wijzigt.',409)
    allowed={'name','provider','base_url','secret_env','enabled','interval_seconds','policies','version'}
    if set(body)-allowed:raise Problem('Onbekend configuratieveld. Bewaar tokens uitsluitend in omgevingsvariabelen.')
    name=text(body.get('name',old.get('name','')),100,True);provider=body.get('provider',old.get('provider','generic'));url=text(body.get('base_url',old.get('base_url','')),1000);ref=text(body.get('secret_env',old.get('secret_env','')),100)
    if provider not in PROVIDERS:raise Problem('Onbekende provider.')
    if ref and not re.fullmatch('ROEFS_SYNC_TOKEN_[A-Z0-9_]+',ref):raise Problem('Gebruik een geheime variabele met naam ROEFS_SYNC_TOKEN_<KOPPELING>.')
    if url:
        from urllib.parse import urlsplit
        parsed=urlsplit(url)
        if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.scheme not in ('https','http'):raise Problem('API-basisadres bevat onveilige gegevens.')
    enabled=body.get('enabled',bool(old.get('enabled',False)))
    if not isinstance(enabled,bool):raise Problem('Ongeldige activatiestatus.')
    interval=int(body.get('interval_seconds',old.get('interval_seconds',300)))
    if not 30<=interval<=86400:raise Problem('Synchronisatie-interval moet tussen 30 en 86400 seconden liggen.')
    policies=body.get('policies',json.loads(old['policies']) if old else {})
    if not isinstance(policies,dict) or set(policies)-set(CATEGORIES) or any(v not in POLICIES for v in policies.values()):raise Problem('Kies een geldig leidend systeem per categorie.')
    if old and (url!=old['base_url'] or provider!=old['provider']) and c.execute('SELECT 1 FROM sync_links WHERE connection_id=?',(cid,)).fetchone():raise Problem('Maak voor een ander doelsysteem een nieuwe koppeling; bestaande recordidentiteiten blijven behouden.',409)
    if enabled:
        if provider!='generic':raise Problem(PROVIDERS[provider]['notice'])
        if not any(v!='off' for v in policies.values()):raise Problem('Selecteer minimaal één gegevenscategorie.')
        validate_url(url)
        if not ref or not os.environ.get(ref):raise Problem('API-token ontbreekt in de ingestelde geheime omgevingsvariabele.')
    values={'name':name,'provider':provider,'base_url':url,'secret_env':ref,'enabled':int(enabled),'interval_seconds':interval,'policies':canonical(policies),'next_run':stamp(),'version':old.get('version',0)+1}
    if cid:update(c,'sync_connections',cid,values)
    else:cid=insert(c,'sync_connections',values)
    audit(c,user,'sync_config','sync_connections',cid,'Geconfigureerd; '+('automatisch actief' if enabled else 'niet actief'));return safe_config(record(c,'sync_connections',cid))

def resolve(c,user,conflict_id,body,modules):
    from .common import version
    if user['role'] not in {'admin','company_admin'}:raise Problem('Alleen beheer mag conflicten oplossen.',403)
    row=record(c,'sync_conflicts',conflict_id);config=record(c,'sync_connections',row['connection_id'])
    if config['lease_until'] and config['lease_until']>stamp():raise Problem('Wacht tot de lopende synchronisatie is afgerond.',409)
    if row['status']!='Open':raise Problem('Dit conflict is al afgehandeld.',409)
    reason=text(body.get('reason',''),1000,True);action=body.get('action');item=json.loads(row['remote_json']);category=row['category'];cid=row['connection_id'];local=record(c,category,row['local_id']) if row['local_id'] else None
    if local:
        version(local,body.get('local_version'))
        if local['version']!=row['local_version']:raise Problem('Lokaal record is opnieuw gewijzigd; vernieuw eerst het conflict.',409)
    if item.get('deleted') and action!='dismiss':raise Problem('Verwijderingen worden niet automatisch doorgezet. Archiveer handmatig en kies Beoordeeld.')
    if local:insert(c,'sync_resolution_snapshots',{'conflict_id':conflict_id,'local_json':canonical(local)})
    if action=='external':
        # Snapshot wordt geïmporteerd; een nieuwere externe wijziging wordt volgende cyclus opnieuw ontdekt.
        local=save_import(c,cid,category,item['fields'],modules,local);link_state(c,cid,category,row['external_id'],local,row['remote_revision'],item['fields'])
    elif action=='local':
        if not local:raise Problem('Koppel eerst een lokaal record.')
        if json.loads(config['policies']).get(category) not in ('roefs','both'):raise Problem('Uitgaand synchroniseren staat voor deze categorie niet aan.')
        # Geen blind overwrite: uitgaande opdracht gebruikt de laatst waargenomen externe revisie.
        payload=translate(c,cid,local_payload(local,category,modules),True);key=uuid.uuid4().hex
        c.execute("UPDATE sync_outbox SET status='Vervangen' WHERE connection_id=? AND category=? AND local_id=? AND status IN ('Wacht','Conflict')",(cid,category,local['id']))
        c.execute('INSERT INTO sync_outbox(connection_id,category,local_id,local_version,external_id,remote_revision,payload,idempotency_key) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(connection_id,category,local_id,local_version) DO UPDATE SET status=\'Wacht\',remote_revision=excluded.remote_revision,payload=excluded.payload,idempotency_key=excluded.idempotency_key',(cid,category,local['id'],local['version'],row['external_id'],row['remote_revision'],canonical({'fields':payload,'roefs_id':str(local['id'])}),key))
    elif action=='link':
        if local:raise Problem('Dit record is al gekoppeld.')
        local=record(c,category,int(body['local_id']))
        local_fields=translate(c,cid,local_payload(local,category,modules),True)
        if digest(local_fields)!=digest(item['fields']):raise Problem('De records verschillen. Vergelijk en maak de velden eerst gelijk; expliciet koppelen overschrijft niets.')
        link_state(c,cid,category,row['external_id'],local,row['remote_revision'],item['fields'])
    elif action=='dismiss':
        # Stop de categorie zodat een genegeerd conflict nooit onzichtbaar tot overschrijven leidt.
        policies=json.loads(config['policies']);policies[category]='off';update(c,'sync_connections',cid,{'policies':canonical(policies),'version':config['version']+1})
    else:raise Problem('Kies extern overnemen, lokaal verzenden, expliciet koppelen of categorie pauzeren.')
    update(c,'sync_conflicts',conflict_id,{'status':'Beoordeeld','resolution':action+': '+reason,'resolved_by':user['id']});audit(c,user,'sync_resolve','sync_conflicts',conflict_id,action+': '+reason);update(c,'sync_connections',cid,{'next_run':stamp()});return {'ok':True}

def route(h,c,user,path,method,body,modules,db):
    if user['role'] not in {'admin','company_admin','auditor'} or (method!='GET' and user['role']=='auditor'):raise Problem('Geen toegang tot integratiebeheer.',403)
    parts=path.split('/')
    if path=='sync' and method=='GET':return {'outbox':[dict(x) for x in c.execute("SELECT id,connection_id,category,local_id,attempts,status,last_error FROM sync_outbox WHERE status='Uitval' ORDER BY id LIMIT 100")],'providers':PROVIDERS,'categories':CATEGORIES,'policy_labels':POLICIES,'connections':[safe_config(x) for x in c.execute('SELECT * FROM sync_connections ORDER BY id')],'runs':[dict(x) for x in c.execute('SELECT * FROM sync_runs ORDER BY id DESC LIMIT 100')],'conflicts':[dict(x) for x in c.execute("SELECT * FROM sync_conflicts WHERE status='Open' ORDER BY id DESC LIMIT 200")],'events':[dict(x) for x in c.execute('SELECT * FROM sync_events ORDER BY id DESC LIMIT 200')]}
    if len(parts)==4 and parts[:2]==['sync','outbox'] and parts[3]=='retry' and method=='POST':
        job=record(c,'sync_outbox',int(parts[2]));config=record(c,'sync_connections',job['connection_id']);reason=text(body.get('reason',''),1000,True)
        if config['lease_until'] and config['lease_until']>stamp():raise Problem('Wacht tot de actieve synchronisatie is afgerond.',409)
        if job['status']!='Uitval':raise Problem('Deze verzending wacht niet op handmatige beoordeling.',409)
        c.execute("UPDATE sync_outbox SET status='Wacht',attempts=0 WHERE id=?",(job['id'],));c.execute('UPDATE sync_connections SET next_run=? WHERE id=?',(stamp(),config['id']));audit(c,user,'retry','sync_outbox',job['id'],reason);return {'ok':True,'status':'In wachtrij; bestaande idempotentiesleutel behouden.'}
    if path=='sync/connections' and method=='POST':return save_config(c,user,body)
    if len(parts)==3 and parts[:2]==['sync','connections'] and method=='PUT':return save_config(c,user,body,int(parts[2]))
    if len(parts)==4 and parts[:2]==['sync','connections'] and parts[3]=='schedule' and method=='POST':
        row=record(c,'sync_connections',int(parts[2]))
        if not row['enabled']:raise Problem('Koppeling is niet actief; configureer en activeer eerst.')
        update(c,'sync_connections',row['id'],{'next_run':stamp()});audit(c,user,'sync_schedule','sync_connections',row['id']);return {'status':'In wachtrij; de automatische worker verwerkt de koppeling.'}
    if len(parts)==3 and parts[:2]==['sync','conflicts'] and method=='POST':return resolve(c,user,int(parts[2]),body,modules)
    raise Problem('Integratieroute niet gevonden.',404)
