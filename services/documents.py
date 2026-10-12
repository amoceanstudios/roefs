"""Private bestanden: gevalideerd, willekeurige bestandsnamen, geautoriseerde download."""
import base64,hashlib,secrets,os,re
from pathlib import Path
from domain import Problem,date_value
from .common import *
from .access import permitted,require
from .workorders import visible
MAX_BYTES=min(10_000_000,max(1024,int(os.environ.get('ROEFS_UPLOAD_MAX_BYTES','600000'))))

def authorized(c,user,row,write=False):
    from . import scopes
    scopes.check_payload(c,user,row)
    if row.get('id'):scopes.require_record(c,user,'files',row['id'])
    if user['role']=='employee':
        if row.get('employee_id') and row['employee_id']!=user.get('employee_id'):raise Problem('Bestand niet gevonden.',404)
        if row.get('workorder_id'):visible(c,user,row['workorder_id']);return
        if row.get('employee_id')==user.get('employee_id'):return
        raise Problem('Bestand niet gevonden.',404)
    require(user,'documents',write)
    if row.get('employee_id') and user['role'] not in {'admin','company_admin','operations'}:raise Problem('Personeelsdocument niet toegankelijk.',403)
    if row.get('workorder_id'):require(user,'workorders')
    if row.get('customer_id'):require(user,'customers')

def upload(c,user,body,db):
    name=text(body.get('name',''),180,True)
    if name in ('.','..') or '/' in name or '\\' in name or any(ord(x)<32 for x in name):raise Problem('Ongeldige bestandsnaam.')
    try:data=base64.b64decode(body.get('content',''),validate=True)
    except (ValueError,TypeError):raise Problem('Ongeldige bestandsinhoud.')
    if not 0<len(data)<=MAX_BYTES:raise Problem('Bestand is leeg of groter dan '+str(MAX_BYTES)+' bytes.',413)
    suffix=Path(name).suffix.lower();mime=None
    if suffix=='.png' and data.startswith(b'\x89PNG\r\n\x1a\n'):mime='image/png'
    elif suffix in ('.jpg','.jpeg') and data.startswith(b'\xff\xd8\xff') and data.endswith(b'\xff\xd9'):mime='image/jpeg'
    elif suffix=='.pdf' and data.startswith(b'%PDF-') and b'%%EOF' in data[-1024:]:mime='application/pdf'
    elif suffix=='.txt':
        try:data.decode('utf-8');mime='text/plain'
        except UnicodeDecodeError:pass
    if not mime:raise Problem('Gebruik een geldig PNG-, JPG-, PDF- of UTF-8-tekstbestand. Andere typen zijn niet toegestaan.')
    row={'name':name,'mime':mime,'size':len(data),'sha256':hashlib.sha256(data).hexdigest(),'category':text(body.get('category','Algemeen'),80,True),'created_by':user['id']}
    for f,table in [('customer_id','customers'),('employee_id','employees'),('workorder_id','workorders')]:
        row[f]=int(body[f]) if body.get(f) else None
        if row[f]:record(c,table,row[f])
    authorized(c,user,row,True)
    if not any(row[f] for f in ('customer_id','employee_id','workorder_id')):raise Problem('Koppel het bestand aan een klant, medewerker of werkopdracht.')
    if row['customer_id'] and row['workorder_id']:
        work=record(c,'workorders',row['workorder_id']);obj=record(c,'objects',work['object_id'])
        if str(row['customer_id'])!=obj['customer_id']:raise Problem('Klant en werkopdracht komen niet overeen.')
    row['retention_until']=body.get('retention_until') or None
    if row['retention_until']:date_value(row['retention_until'])
    else:
        setting=c.execute("SELECT value FROM settings WHERE key='retention_days'").fetchone()
        if setting:row['retention_until']=str(dt.date.today()+dt.timedelta(days=int(json.loads(setting[0]))))
    root=Path(db).parent/'uploads';root.mkdir(mode=0o700,exist_ok=True);row['storage_key']=secrets.token_hex(32)
    target=root/row['storage_key']
    fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as out:out.write(data)
    try:
        from .file_scanning import scan
        row['scan_status'],row['scan_detail']=scan(target,mime)
        rid=insert(c,'files',row);audit(c,user,'upload','files',rid);c.commit()
    except Exception:target.unlink(missing_ok=True);raise
    return {'id':rid,'name':name,'size':len(data),'scan_status':row['scan_status'],'scan_detail':row['scan_detail']}
def download(c,user,rid,db):
    row=record(c,'files',rid);authorized(c,user,row)
    if row.get('deleted_at'):raise Problem('Bestand is verwijderd.',410)
    if row.get('scan_status') not in ('Schoon','Tekstbijlage'):raise Problem('Bestand staat in quarantaine of is geblokkeerd. Een geslaagde malwarescan is vereist.',423)
    if not re.fullmatch('[a-f0-9]{64}',row['storage_key']):raise Problem('Ongeldige opslagreferentie.',409)
    target=Path(db).parent/'uploads'/row['storage_key']
    if not target.is_file() or target.is_symlink():raise Problem('Bestand ontbreekt in de opslag.',404)
    if target.stat().st_size!=row['size']:raise Problem('Bestandsgrootte wijkt af van de opslagregistratie.',409)
    data=target.read_bytes()
    if hashlib.sha256(data).hexdigest()!=row['sha256']:raise Problem('Integriteitscontrole van bestand mislukt.',409)
    audit(c,user,'download','files',rid);c.commit();return row,data


def rescan(c,user,rid,db):
    row=record(c,'files',rid);authorized(c,user,row,True)
    if row.get('deleted_at'):raise Problem('Bestand is verwijderd.',410)
    if not re.fullmatch('[a-f0-9]{64}',row['storage_key']):raise Problem('Ongeldige opslagreferentie.',409)
    path=Path(db).parent/'uploads'/row['storage_key']
    if path.is_symlink() or not path.is_file() or path.stat().st_size!=row['size'] or hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:raise Problem('Bestandsintegriteit mislukt.',409)
    from .file_scanning import scan
    status,detail=scan(path,row['mime']);update(c,'files',rid,{'scan_status':status,'scan_detail':detail,'version':row['version']+1});audit(c,user,'rescan','files',rid,status)
    return {'scan_status':status,'scan_detail':detail,'version':row['version']+1}

def delete(c,user,rid,body,db):
    if user['role'] not in ('admin','company_admin'):raise Problem('Alleen beheer mag documenten verwijderen.',403)
    row=record(c,'files',rid);authorized(c,user,row,True);version(row,body.get('version'));reason=text(body.get('reason',''),1000,True)
    if row.get('deleted_at'):raise Problem('Bestand is al verwijderd.',409)
    if not re.fullmatch('[a-f0-9]{64}',row['storage_key']):raise Problem('Ongeldige opslagreferentie.',409)
    update(c,'files',rid,{'deleted_at':dt.datetime.now(dt.timezone.utc).isoformat(),'version':row['version']+1});audit(c,user,'delete','files',rid,reason);c.commit()
    # Tombstone eerst duurzaam: een onderbroken verwijdering maakt nooit een verdwenen actief record.
    (Path(db).parent/'uploads'/row['storage_key']).unlink(missing_ok=True)
    return {'ok':True}

def retention(c,db):
    """Opt-in bewaarbeleid, begrensde batches; metadata/audit blijven behouden."""
    enabled=c.execute("SELECT value FROM settings WHERE key='document_retention_auto'").fetchone()
    if not enabled or json.loads(enabled[0]) is not True:return 0
    due=[dict(x) for x in c.execute('SELECT id,version FROM files WHERE deleted_at IS NULL AND retention_until IS NOT NULL AND retention_until<=? ORDER BY id LIMIT 25',(str(dt.date.today()),))]
    system={'id':0,'username':'Automatische documentretentie','role':'admin'}
    for row in due:
        c.execute('BEGIN IMMEDIATE')
        delete(c,system,row['id'],{'version':row['version'],'reason':'Ingeschakeld bewaarbeleid: opgeslagen bewaartermijn verstreken.'},db)
    # Hervat fysieke opruiming wanneer een vorige poging na de tombstone onderbrak.
    for row in c.execute('SELECT storage_key FROM files WHERE deleted_at IS NOT NULL ORDER BY id'):
        if re.fullmatch('[a-f0-9]{64}',row['storage_key']):(Path(db).parent/'uploads'/row['storage_key']).unlink(missing_ok=True)
    return len(due)
