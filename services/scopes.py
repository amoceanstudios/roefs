"""Optionele recordclassificatie boven op rollen; ongeclassificeerd is afgeschermd.
Requestgebonden beleid voor HTTP-routes, bedrijfsoperaties en rapportages.
Geen bedrijfsspecifieke indeling wordt automatisch verzonnen.
"""
import contextvars,json
from domain import Problem
ACTOR=contextvars.ContextVar('roefs_scope_actor',default=None)
BASE={'customers','objects','contracts','employees','shifts','workorders','hours','assets','vehicles','invoices','quotes','ledger','payroll','leave','availability','inspections','logbook','orders','keys','alerts','documents','teams','articles','files','planning_series','time_clocks','service_types'}
CHILDREN={'contacts':('customer_id','customers'),'communications':('customer_id','customers'),'certifications':('employee_id','employees'),'checklist':('workorder_id','workorders'),'workorder_events':('workorder_id','workorders'),'schedule_history':('shift_id','shifts'),'reservations':('workorder_id','workorders'),'invoice_lines':('invoice_id','invoices'),'contract_events':('contract_id','contracts'),'contract_locations':('contract_id','contracts')}
CHILDREN.update({'rooms':('object_id','objects'),'work_programs':('object_id','objects'),'work_instructions':('program_id','work_programs'),'contract_services':('contract_id','contracts')})
REFERENCES={'program_id':'work_programs','room_id':'rooms','service_type_id':'service_types','customer_id':'customers','object_id':'objects','employee_id':'employees','workorder_id':'workorders','contract_id':'contracts','shift_id':'shifts','asset_id':'assets','invoice_id':'invoices','team_id':'teams','manager_id':'employees','from_object':'objects','to_object':'objects'}

def migrate(c):
    c.execute('CREATE TABLE IF NOT EXISTS access_scopes(user_id INTEGER PRIMARY KEY REFERENCES users(id),policy TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1)')
    c.execute('CREATE TABLE IF NOT EXISTS record_scopes(module TEXT NOT NULL,record_id INTEGER NOT NULL,department TEXT NOT NULL,region TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,PRIMARY KEY(module,record_id))')
    c.execute('CREATE INDEX IF NOT EXISTS record_scope_lookup ON record_scopes(module,department,region,record_id)')
    existing={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table in sorted(BASE & existing):
        c.execute("CREATE TRIGGER IF NOT EXISTS clear_scope_"+table+" AFTER DELETE ON "+table+" BEGIN DELETE FROM record_scopes WHERE module='"+table+"' AND record_id=OLD.id; END")

def attach(c,user):
    row=c.execute('SELECT policy FROM access_scopes WHERE user_id=?',(user['id'],)).fetchone()
    user.pop('scope',None)
    if row:
        policy=json.loads(row[0])
        if policy['enabled']:user['scope']=policy
    return user

def sql(user,table,alias=None):
    policy=user.get('scope') if user else None
    if not policy:return '1=1',[]
    if table not in BASE|set(CHILDREN)|{'travel_estimates'}:return '0=1',[]
    if alias is not None and (not alias.isidentifier() or not alias.isascii()):raise ValueError('Ongeldige tabelalias.')
    prefix=(alias or table)+'.'
    if table in CHILDREN:
        field,parent=CHILDREN[table];clause,args=sql(user,parent)
        return prefix+field+' IN (SELECT id FROM '+parent+' WHERE '+clause+')',args
    if table=='travel_estimates':
        clause,args=sql(user,'objects');return '('+prefix+'from_object IN (SELECT id FROM objects WHERE '+clause+') AND '+prefix+'to_object IN (SELECT id FROM objects WHERE '+clause+'))',args+args
    if table not in BASE:return '0=1',[]
    where=['rs.module=?','rs.record_id='+prefix+'id'];args=[table]
    for field,key in [('department','departments'),('region','regions')]:
        if policy[key]:where.append('rs.'+field+' IN ('+','.join('?' for _ in policy[key])+')');args.extend(policy[key])
    return 'EXISTS(SELECT 1 FROM record_scopes rs WHERE '+' AND '.join(where)+')',args

def allowed(c,user,table,rid):
    if not user or not user.get('scope'):return True
    if table not in BASE|set(CHILDREN)|{'travel_estimates'}:return False
    clause,args=sql(user,table)
    return bool(c.execute('SELECT 1 FROM '+table+' WHERE id=? AND '+clause,[rid]+args).fetchone())

def require_record(c,user,table,rid):
    if not allowed(c,user,table,rid):raise Problem('Gegevens vallen buiten je ingestelde afdeling of rayon.',404)

def filter_rows(c,user,table,rows):
    if not user or not user.get('scope'):return list(rows)
    if table=='contract_locations':return [r for r in rows if allowed(c,user,'contracts',r['contract_id']) and allowed(c,user,'objects',r['object_id'])]
    return [r for r in rows if allowed(c,user,table,r['id']) and references_allowed(c,user,dict(r))]

def references_allowed(c,user,row):
    return all(not row.get(field) or allowed(c,user,parent,row[field]) for field,parent in REFERENCES.items())

def count(c,user,table):
    clause,args=sql(user,table)
    return c.execute('SELECT COUNT(*) FROM '+table+' WHERE '+clause,args).fetchone()[0]

def select(c,user,table,where='1=1',args=(),order='id DESC',limit=None):
    clause,scope_args=sql(user,table)
    query='SELECT * FROM '+table+' WHERE ('+where+') AND '+clause+' ORDER BY '+order
    params=list(args)+scope_args
    if limit is not None:query+=' LIMIT ?';params.append(limit)
    return filter_rows(c,user,table,[dict(r) for r in c.execute(query,params)])

def notification_visible(c,user,row):
    if not user.get('scope'):return True
    # Meldingen bevatten vrije tekst: toon alleen expliciet herleidbare doelen.
    event=row.get('event_key','').split(':')
    module={'work':'workorders','shift':'shifts','contract-decision':'contracts'}.get(event[0])
    if module and len(event)>1 and event[1].isdigit():
        if module=='shifts':return allowed(c,user,module,int(event[1]))
        table,field=('workorder_events','workorder_id') if module=='workorders' else ('contract_events','contract_id')
        entry=c.execute('SELECT '+field+' FROM '+table+' WHERE id=?',(int(event[1]),)).fetchone()
        return bool(entry and allowed(c,user,module,entry[0]))
    target=row.get('target','');parts=target.strip('/').split('/')
    if len(parts)==2 and parts[0] in BASE and parts[1].isdigit():return allowed(c,user,parts[0],int(parts[1]))
    return False


def check_payload(c,user,body):
    if not user.get('scope'):return
    if isinstance(body,list):
        for row in body:check_payload(c,user,row)
    elif isinstance(body,dict):
        for field,value in body.items():
            if field=='object_ids' and isinstance(value,list):
                for rid in value:require_record(c,user,'objects',rid)
            elif field in REFERENCES and value not in ('',None):
                if isinstance(value,bool) or not str(value).isdigit():raise Problem('Ongeldig gekoppeld recordnummer.')
                require_record(c,user,REFERENCES[field],int(value))
            elif field=='required_assets' and value:
                for aid in str(value).split(','):require_record(c,user,'assets',int(aid.strip()))
            elif isinstance(value,(dict,list)):check_payload(c,user,value)

def classify_created(c,table,rid,values):
    user=ACTOR.get()
    if table not in BASE or not user or not user.get('scope'):return
    existing=c.execute('SELECT 1 FROM record_scopes WHERE module=? AND record_id=?',(table,rid)).fetchone()
    if existing:return
    policy=user['scope'];department=policy['default_department'];region=policy['default_region']
    for field in ('workorder_id','object_id','customer_id','employee_id'):
        if values.get(field):
            parent=c.execute('SELECT department,region FROM record_scopes WHERE module=? AND record_id=?',(REFERENCES[field],values[field])).fetchone()
            if parent:department,region=parent;break
    c.execute('INSERT INTO record_scopes(module,record_id,department,region) VALUES(?,?,?,?)',(table,rid,department,region))
    require_record(c,user,table,rid)

def guard(c,user,path,method,body=None):
    if not user.get('scope'):return
    # Deze organisatiebrede logboeken bevatten ongestructureerde details. Fail closed.
    if path in ('/api/v5/reminders/run','/api/v5/settings','/api/v5/security/audit-integrity') or path.startswith('/api/v5/sync') or path in ('/api/audit','/api/v5/audit') or path.endswith('/timeline'):raise Problem('Dit organisatiebrede overzicht is niet beschikbaar binnen een afdelings- of rayonbeperking.',403)
    parts=path.strip('/').split('/')
    if len(parts)>=4 and parts[:2]==['api','records'] and parts[2] in BASE and parts[3].isdigit():require_record(c,user,parts[2],int(parts[3]))
    if method!='GET':check_payload(c,user,body)

def validate(policy):
    keys={'enabled','departments','regions','default_department','default_region'}
    if not isinstance(policy,dict) or set(policy)!=keys or not isinstance(policy['enabled'],bool):raise Problem('Vul het volledige scopebeleid in.')
    for key in ('departments','regions'):
        if not isinstance(policy[key],list) or len(policy[key])>50 or any(not isinstance(v,str) or not v.strip() or len(v)>100 for v in policy[key]):raise Problem('Afdelingen/rayons: maximaal 50 niet-lege namen van 100 tekens.')
        policy[key]=list(dict.fromkeys(v.strip() for v in policy[key]))
    for field,key in [('default_department','departments'),('default_region','regions')]:
        value=policy[field]
        if not isinstance(value,str) or len(value)>100 or policy[key] and value not in policy[key]:raise Problem('Standaardindeling moet binnen de toegestane afdelingen/rayons vallen.')
    if policy['enabled'] and not policy['departments'] and not policy['regions']:raise Problem('Een actieve beperking vereist minstens één afdeling of rayon.')
    return policy

def route(c,user,parts,method,body):
    from .common import audit,version
    if user['role'] not in ('admin','company_admin'):raise Problem('Alleen beheer kan scopebeleid en indeling beheren.',403)
    if parts==['security','scopes'] and method=='GET':return {'users':[dict(r) for r in c.execute('SELECT id,username,role FROM users ORDER BY id')],'policies':[{'user_id':r['user_id'],'version':r['version'],**json.loads(r['policy'])} for r in c.execute('SELECT * FROM access_scopes')],'modules':sorted(BASE)}
    if parts[:2]==['security','scopes'] and len(parts)==3 and method=='PUT':
        uid=int(parts[2]);target=c.execute('SELECT role FROM users WHERE id=?',(uid,)).fetchone()
        if not target:raise Problem('Gebruiker ontbreekt.',404)
        if target['role'] in ('admin','company_admin'):raise Problem('Beheeraccounts beheren de indeling en kunnen niet zelf beperkt worden.')
        previous=c.execute('SELECT version FROM access_scopes WHERE user_id=?',(uid,)).fetchone();old=dict(previous) if previous else {'version':0};version(old,body.get('version'));policy=validate({k:v for k,v in body.items() if k!='version'})
        c.execute('INSERT INTO access_scopes(user_id,policy,version) VALUES(?,?,1) ON CONFLICT(user_id) DO UPDATE SET policy=excluded.policy,version=access_scopes.version+1',(uid,json.dumps(policy)))
        c.execute('DELETE FROM sessions WHERE user_id=?',(uid,));audit(c,user,'scope_policy','users',uid);return {'ok':True}
    if parts==['security','classifications'] and method=='GET':return {'items':[dict(r) for r in c.execute('SELECT * FROM record_scopes ORDER BY module,record_id')]}
    if parts==['security','classifications'] and method=='POST':
        module=body.get('module');ids=body.get('ids');department=body.get('department','');region=body.get('region','')
        if module not in BASE or not isinstance(ids,list) or not 1<=len(ids)<=1000 or any(type(x)!=int or x<=0 for x in ids):raise Problem('Kies een bekende module en 1–1000 recordnummers.')
        if any(not isinstance(x,str) or len(x)>100 for x in (department,region)):raise Problem('Indelingsnaam maximaal 100 tekens.')
        if len(set(ids))!=len(ids):raise Problem('Recordnummers mogen niet dubbel voorkomen.')
        expected=body.get('versions',{})
        if not isinstance(expected,dict):raise Problem('Verwacht een versienummer per record.')
        for rid in ids:
            if not c.execute('SELECT 1 FROM '+module+' WHERE id=?',(rid,)).fetchone():raise Problem('Record ontbreekt.',404)
            old=c.execute('SELECT version FROM record_scopes WHERE module=? AND record_id=?',(module,rid)).fetchone();version(dict(old) if old else {'version':0},expected.get(str(rid)))
            c.execute('INSERT INTO record_scopes VALUES(?,?,?,?,1) ON CONFLICT(module,record_id) DO UPDATE SET department=excluded.department,region=excluded.region,version=record_scopes.version+1',(module,rid,department,region));audit(c,user,'classify',module,rid,department+' / '+region)
        return {'ok':True,'count':len(ids)}
    raise Problem('Scopehandeling niet gevonden.',404)
