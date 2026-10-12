"""Gedeelde validatie en recordrechten; uitsluitend standaardbibliotheek."""
import datetime as dt
import re
from decimal import Decimal, InvalidOperation

class Problem(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status

REFERENCES = {'customer_id':'customers', 'object_id':'objects', 'contract_id':'contracts',
              'employee_id':'employees', 'shift_id':'shifts'}
REQUIRED = {
 'customers':['name'], 'objects':['name','customer_id'],
 'contracts':['name','customer_id','object_id','monthly_value','start_date'],
 'quotes':['name','customer_id','amount'], 'invoices':['number','customer_id','amount','due_date'],
 'ledger':['description','date','account','debit','credit'], 'payroll':['employee_id','period','hours','gross_amount'],
 'employees':['name','contract_hours'], 'shifts':['object_id','date','start_time','end_time'],
 'hours':['employee_id','date','hours'], 'inspections':['object_id','inspector','date','score'],
 'logbook':['object_id','author','date','message'], 'workorders':['object_id','description','date','hours'],
 'orders':['item','object_id','quantity','unit'], 'assets':['name','object_id'],
 'keys':['object_id','key_code','holder'], 'vehicles':['plate','model'],
 'documents':['name','category','reference'], 'leave':['employee_id','start_date','end_date','type'],
 'alerts':['title','severity','description'], 'availability':['employee_id','date','start_time','end_time']}
STATUSES = {
 'customers':['Actief','Inactief'], 'objects':['Actief','Inactief'],
 'contracts':['Actief','Concept','Beëindigd','Geannuleerd'], 'quotes':['Concept','Verzonden','Goedgekeurd','Afgewezen','Geannuleerd'],
 'invoices':['Concept','Open','Betaald','Geannuleerd'], 'ledger':['Concept','Geboekt','Geannuleerd'],
 'payroll':['Concept','Goedgekeurd','Verwerkt','Geannuleerd'], 'employees':['Actief','Inactief'],
 'shifts':['Gepland','Bevestigd','Afgerond','Geannuleerd'], 'hours':['Ingediend','Goedgekeurd','Akkoord','Afgewezen'],
 'inspections':['Gepland','Afgerond'], 'logbook':['Open','In behandeling','Afgerond'],
 'workorders':['Nieuw','In behandeling','Afgerond','Geannuleerd'], 'orders':['Aangevraagd','Besteld','Ontvangen','Geannuleerd'],
 'assets':['Beschikbaar','In gebruik','Onderhoud','Buiten gebruik'], 'keys':['Uitgegeven','Ingeleverd','Vermist'],
 'vehicles':['Actief','Onderhoud','Inactief'], 'documents':['Actief','Concept','Vervallen'],
 'leave':['Aangevraagd','Goedgekeurd','Afgewezen','Ziek','Ziekgemeld','Geannuleerd'],
 'alerts':['Open','In behandeling','Afgerond'], 'availability':['Beschikbaar','Niet beschikbaar']}
NUMBERS = {'monthly_value':(0,100000000), 'amount':(0,100000000), 'debit':(0,100000000),
 'credit':(0,100000000),'gross_amount':(0,100000000),'contract_hours':(0,168),
 'hours':(0,744),'quantity':(0,1000000),'score':(0,100)}
LABELS = {'employee_id':'Medewerker','object_id':'Object','customer_id':'Klant','contract_id':'Contract',
 'shift_id':'Dienst','name':'Naam','date':'Datum','start_time':'Begintijd','end_time':'Eindtijd',
 'hours':'Uren','status':'Status','number':'Factuurnummer','amount':'Bedrag','start_date':'Begindatum',
 'end_date':'Einddatum','monthly_value':'Maandbedrag','contract_hours':'Contracturen','quantity':'Aantal',
 'score':'Score','description':'Omschrijving','period':'Periode','email':'E-mailadres','title':'Titel',
 'severity':'Urgentie','message':'Bericht','author':'Auteur','due_date':'Vervaldatum','reference':'Referentie',
 'category':'Categorie','inspector':'Inspecteur','item':'Artikel','unit':'Eenheid','key_code':'Sleutelcode',
 'holder':'Sleutelhouder','plate':'Kenteken','model':'Model','type':'Type','account':'Grootboekrekening',
 'debit':'Debet','credit':'Credit','gross_amount':'Brutobedrag'}

def date_value(value):
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise Problem('Gebruik een geldige datum (JJJJ-MM-DD).')
    try: return dt.date.fromisoformat(value)
    except ValueError: raise Problem('De opgegeven datum bestaat niet.')

def time_value(value):
    if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value):
        raise Problem('Gebruik een geldige tijd (UU:MM).')
    h,m=map(int,value.split(':')); return h*60+m

def interval(row):
    date_value(str(row.get('date','')))
    start=time_value(str(row.get('start_time',''))); end=time_value(str(row.get('end_time','')))
    if end<=start: raise Problem('Een dienst of beschikbaarheid moet dezelfde dag na de begintijd eindigen.')
    return (end-start)/60

def schedule_issues(c, row, exclude=0, extended=True):
    """Dezelfde regels gelden voor CRUD, suggesties, SOS en werkstromen."""
    interval(row)
    eid=str(row.get('employee_id',''))
    if not eid or row.get('status')=='Geannuleerd': return []
    issues=[]
    emp=c.execute("SELECT 1 FROM employees WHERE id=? AND status='Actief'",(eid,)).fetchone()
    if not emp: return ['Medewerker ontbreekt of is niet actief.']
    args=(eid,row['date'],exclude,row['end_time'],row['start_time'])
    clash=c.execute("SELECT id FROM shifts WHERE employee_id=? AND date=? AND id!=? AND status!='Geannuleerd' AND start_time<? AND end_time>?",args).fetchone()
    if clash:
        from services import scopes
        issues.append('Roosterconflict met dienst #'+str(clash['id']) if scopes.allowed(c,scopes.ACTOR.get(),'shifts',clash['id']) else 'Medewerker is al ingepland buiten je toegangsbereik.')
    if c.execute("SELECT 1 FROM leave WHERE employee_id=? AND status IN ('Goedgekeurd','Ziek','Ziekgemeld') AND start_date<=? AND end_date>=?",(eid,row['date'],row['date'])).fetchone():
        issues.append('Medewerker heeft goedgekeurd verlof of geregistreerd verzuim.')
    entries=c.execute('SELECT * FROM availability WHERE employee_id=? AND date=?',(eid,row['date'])).fetchall()
    if any(x['status']=='Niet beschikbaar' and x['start_time']<row['end_time'] and x['end_time']>row['start_time'] for x in entries):
        issues.append('Medewerker heeft zich voor deze tijd niet beschikbaar gemeld.')
    windows=sorted((x['start_time'],x['end_time']) for x in entries if x['status']=='Beschikbaar')
    if windows:
        covered=row['start_time']
        for start,end in windows:
            if start<=covered: covered=max(covered,end)
        if covered<row['end_time']: issues.append('Dienst valt buiten de opgegeven beschikbaarheid.')
    from services.labor_rules import issues as labor_issues
    issues.extend(labor_issues(c,row,exclude))
    if extended and row.get('workorder_id'):
        from services.planning import issues as extended_issues
        return extended_issues(c,row,exclude,issues)
    return issues

def role_predicate(module,user):
    from services.access import permitted
    if permitted(user,module):return '1=1',[]
    eid=str(user.get('employee_id') or -1)
    if module in ('shifts','hours','workorders','leave','availability'):return 'employee_id=?',[eid]
    objects="SELECT object_id FROM shifts WHERE employee_id=? AND status!='Geannuleerd' UNION SELECT object_id FROM workorders WHERE employee_id=? AND status!='Geannuleerd'"
    if module=='objects':return 'CAST(id AS TEXT) IN ('+objects+')',[eid,eid]
    if module in ('logbook','orders','assets','inspections'):return 'object_id IN ('+objects+')',[eid,eid]
    if module=='documents':return "status='Actief'",[]
    return '0=1',[]

def scoped_predicate(module,user):
    from services.scopes import sql
    clause,args=role_predicate(module,user);scope,params=sql(user,module)
    return '('+clause+') AND ('+scope+')',args+params

def scoped_rows(c,module,user,rid=None):
    clause,args=scoped_predicate(module,user)
    if rid is not None:clause+=' AND id=?';args.append(rid)
    return [dict(x) for x in c.execute('SELECT * FROM '+module+' WHERE '+clause+' ORDER BY id DESC',args)]

def scoped_page(c,module,user,fields,query):
    clause,args=scoped_predicate(module,user)
    limit=min(100,max(1,int(query.get('limit',['25'])[0])));offset=max(0,int(query.get('offset',['0'])[0]));q=query.get('q',[''])[0]
    if len(q)>200:raise Problem('Zoektekst maximaal 200 tekens.')
    if q:
        clause+=' AND ('+' OR '.join('instr(lower(COALESCE('+f+",'')),lower(?))>0" for f in fields)+')';args.extend([q]*len(fields))
    total=c.execute('SELECT COUNT(*) FROM '+module+' WHERE '+clause,args).fetchone()[0]
    return {'items':[dict(x) for x in c.execute('SELECT * FROM '+module+' WHERE '+clause+' ORDER BY id DESC LIMIT ? OFFSET ?',args+[limit,offset])],'total':total,'limit':limit,'offset':offset}

def validate(c, module, body, fields, previous=None):
    previous=previous or {}
    if not body or any(k not in fields for k in body): raise Problem('Geen geldige velden opgegeven of onbekend veld.')
    for value in body.values():
        if isinstance(value,(dict,list,bool)) or value is None: raise Problem('Velden moeten tekst of een getal bevatten.')
        if len(str(value))>2000: raise Problem('Een veld mag maximaal 2000 tekens bevatten.')
    row={f:str(body.get(f,previous.get(f,''))).strip() for f in fields}
    if not row.get('status'): row['status']=STATUSES[module][0]
    for f in REQUIRED[module]:
        if not row[f]: raise Problem(LABELS.get(f,f)+' is verplicht.')
    if row['status'] not in STATUSES[module]: raise Problem('Kies een geldige status.')
    for f,target in REFERENCES.items():
        if row.get(f):
            if not row[f].isdigit() or not c.execute('SELECT 1 FROM '+target+' WHERE id=?',(row[f],)).fetchone():
                raise Problem(LABELS[f]+' bestaat niet.')
            row[f]=str(int(row[f]))
    for f,(lo,hi) in NUMBERS.items():
        if row.get(f):
            try: n=Decimal(row[f].replace(',','.'))
            except InvalidOperation: raise Problem(LABELS.get(f,f)+' moet een getal zijn.')
            if not n.is_finite() or not lo<=n<=hi: raise Problem(LABELS.get(f,f)+' valt buiten het toegestane bereik.')
            if f=='hours' and module in ('hours','workorders') and n>24: raise Problem('Maximaal 24 uur per registratie.')
            row[f]=str(n)
    for f,v in row.items():
        if v and (f=='date' or f.endswith('_date') or f=='issued_at'): date_value(v)
    if row.get('start_date') and row.get('end_date') and row['end_date']<row['start_date']: raise Problem('Einddatum ligt vóór begindatum.')
    if row.get('email') and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',row['email']): raise Problem('Ongeldig e-mailadres.')
    if row.get('period'):
        date_value(row['period']+'-01')
    if module in ('shifts','availability'): interval(row)
    if module=='shifts':
        issues=schedule_issues(c,row,previous.get('id',0))
        if issues: raise Problem(' '.join(issues),409)
    if module=='contracts':
        obj=c.execute('SELECT customer_id FROM objects WHERE id=?',(row['object_id'],)).fetchone()
        if obj['customer_id']!=row['customer_id']: raise Problem('Object hoort niet bij deze klant.')
    if module=='invoices':
        if c.execute('SELECT 1 FROM invoices WHERE number=? AND id!=?',(row['number'],previous.get('id',0))).fetchone(): raise Problem('Factuurnummer bestaat al.',409)
        if row['contract_id']:
            contract=c.execute('SELECT customer_id FROM contracts WHERE id=?',(row['contract_id'],)).fetchone()
            if contract['customer_id']!=row['customer_id']: raise Problem('Contract hoort niet bij deze klant.')
    if module=='hours':
        if row['shift_id']:
            sh=c.execute('SELECT * FROM shifts WHERE id=?',(row['shift_id'],)).fetchone()
            if sh['employee_id']!=row['employee_id'] or sh['date']!=row['date']: raise Problem('Dienst, medewerker en datum komen niet overeen.')
            if c.execute("SELECT 1 FROM hours WHERE shift_id=? AND employee_id=? AND status!='Afgewezen' AND id!=?",(row['shift_id'],row['employee_id'],previous.get('id',0))).fetchone() and row['status']!='Afgewezen':
                raise Problem('Voor deze dienst zijn al uren geregistreerd.',409)
        total=sum(Decimal(x[0]) for x in c.execute("SELECT hours FROM hours WHERE employee_id=? AND date=? AND status!='Afgewezen' AND id!=?",(row['employee_id'],row['date'],previous.get('id',0))) if x[0])
        if row['status']!='Afgewezen' and total+Decimal(row['hours'])>24: raise Problem('Meer dan 24 geregistreerde uren op dezelfde dag.',409)
    if module=='availability':
        if c.execute('SELECT 1 FROM availability WHERE employee_id=? AND date=? AND id!=? AND start_time<? AND end_time>?',(row['employee_id'],row['date'],previous.get('id',0),row['end_time'],row['start_time'])).fetchone():
            raise Problem('Beschikbaarheidsblokken overlappen; pas het bestaande blok aan.',409)
    return row

def protect_delete(c,module,rid,modules):
    if c.execute("SELECT 1 FROM sqlite_master WHERE name='migration_links'").fetchone() and c.execute('SELECT 1 FROM migration_links WHERE category=? AND local_id=?',(module,rid)).fetchone():raise Problem('Record heeft een migratie-identiteit. Archiveer via de status; verwijderen verbreekt bronrelaties.',409)
    if c.execute("SELECT 1 FROM sqlite_master WHERE name='sync_links'").fetchone() and c.execute('SELECT 1 FROM sync_links WHERE category=? AND local_id=?',(module,rid)).fetchone():
        raise Problem('Dit record is extern gekoppeld. Archiveer via de status; verwijder de gegevens niet.',409)
    for source,(_,fields) in modules.items():
        for field,target in REFERENCES.items():
            if target==module and field in fields and c.execute('SELECT 1 FROM '+source+' WHERE '+field+'=?',(str(rid),)).fetchone():
                raise Problem('Verwijderen niet mogelijk: gekoppelde gegevens in '+modules[source][0]+'. Archiveer via de status of pas eerst de koppelingen aan.',409)
    if module=='employees':
        for source,field in [('users','employee_id'),('employee_cao_profiles','employee_id'),('employee_contract_terms','employee_id')]:
            if c.execute('SELECT 1 FROM '+source+' WHERE '+field+'=?',(rid,)).fetchone(): raise Problem('Medewerker heeft een gekoppeld account of personeelsdossier; kies Inactief.',409)
    kinds={'shifts':'shift_replacement','logbook':'workorder_from_log','contracts':'invoice_from_contract'}
    if module in kinds and c.execute("SELECT 1 FROM autopilot_jobs WHERE kind=? AND source_id=? AND status='Wacht op goedkeuring'",(kinds[module],rid)).fetchone():
        raise Problem('Beoordeel eerst het openstaande werkstroomvoorstel.',409)
