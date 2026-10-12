"""Contractdiensten: expliciete kalender en urenbudget; geen impliciete medewerkers of tijden."""
import datetime as dt,json
from decimal import Decimal
from domain import Problem,date_value,interval
from .common import record,version,text,money,insert,update,audit
from .access import require

def migrate(c):
 c.execute('CREATE TABLE IF NOT EXISTS contract_services(id INTEGER PRIMARY KEY,contract_id INTEGER NOT NULL REFERENCES contracts(id),name TEXT NOT NULL,definition TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1)')
 c.execute('CREATE TABLE IF NOT EXISTS contract_service_jobs(service_id INTEGER NOT NULL REFERENCES contract_services(id),date TEXT NOT NULL,workorder_id INTEGER NOT NULL UNIQUE REFERENCES workorders(id),PRIMARY KEY(service_id,date))')

def dates(values):
 if not isinstance(values,list) or len(values)>366:raise Problem('Gebruik een lijst met maximaal 366 datums.')
 result=[str(date_value(x)) for x in values]
 if len(set(result))!=len(result):raise Problem('Datums mogen niet dubbel voorkomen.')
 return sorted(result)

def definition(c,contract,body):
 if not isinstance(body,dict):raise Problem('Ongeldige dienstafspraken.')
 obj=record(c,'objects',int(body['object_id']))
 if str(obj['customer_id'])!=str(contract['customer_id']) or (str(obj['id'])!=str(contract['object_id']) and not c.execute('SELECT 1 FROM contract_locations WHERE contract_id=? AND object_id=?',(contract['id'],obj['id'])).fetchone()):raise Problem('Kies een locatie van dit contract.',409)
 kind=body.get('kind')
 if kind not in ('weekly','periodic'):raise Problem('Kies lesweken of periodiek werk.')
 tasks=body.get('tasks',[])
 if not isinstance(tasks,list) or not 1<=len(tasks)<=100:raise Problem('Leg 1 tot 100 bestektaken vast.')
 tasks=[text(x,300,True) for x in tasks]
 count=body.get('count')
 if type(count)!=int or not 1<=count<=53:raise Problem('Aantal weken/bezoeken moet tussen 1 en 53 liggen.')
 hours=body.get('hours',{})
 if not isinstance(hours,dict):raise Problem('Ongeldige daguren.')
 clean={}
 for k,v in hours.items():
  if k not in [str(i) for i in range(7)]:raise Problem('Ongeldige weekdag.')
  n=money(v)
  if not 0<n<=24 or n*60!=(n*60).to_integral_value():raise Problem('Daguren moeten positieve hele minuten zijn, maximaal 24 uur.')
  clean[k]=str(n)
 if kind=='weekly' and not clean:raise Problem('Vul minimaal één weekdag in.')
 weeks=dates(body.get('weeks',[]));visits=dates(body.get('dates',[]));exceptions=dates(body.get('exceptions',[]))
 if any(date_value(x).weekday()!=0 for x in weeks):raise Problem('Vul de maandag van iedere geselecteerde lesweek in.')
 if kind=='weekly' and (visits or len(weeks)>count) or kind=='periodic' and (weeks or clean or exceptions or len(visits)>count):raise Problem('Kalender past niet bij de gekozen dienst of het afgesproken aantal.')
 selected=sorted(str(date_value(w)+dt.timedelta(days=int(day))) for w in weeks for day in clean) if kind=='weekly' else visits
 if any(x not in selected for x in exceptions):raise Problem('Uitzonderingen moeten binnen de geselecteerde werkdagen vallen.')
 selected=[x for x in selected if x not in exceptions]
 if any(x<contract['start_date'] or contract['end_date'] and x>contract['end_date'] for x in selected):raise Problem('Alle werkdatums moeten binnen de contractduur liggen.')
 return {'object_id':obj['id'],'kind':kind,'count':count,'hours':clean,'weeks':weeks,'dates':visits,'exceptions':exceptions,'tasks':tasks,'selected':selected}

def detail(c,user,cid):
 from . import scopes
 require(user,'contracts');contract=record(c,'contracts',cid);items=[]
 for raw in c.execute('SELECT * FROM contract_services WHERE contract_id=? ORDER BY id',(cid,)):
  row=dict(raw);d=json.loads(row.pop('definition'));row['definition']=d
  if not scopes.allowed(c,user,'objects',d['object_id']):continue
  weekly=sum((Decimal(x) for x in d['hours'].values()),Decimal(0))
  row['weekly_hours']=str(weekly) if d['kind']=='weekly' else None
  row['agreed_hours']=str(weekly*d['count']) if d['kind']=='weekly' else None
  row['selected_hours']=str(sum((Decimal(d['hours'][str(date_value(x).weekday())]) for x in d['selected']),Decimal(0))) if d['kind']=='weekly' else None
  row['jobs']=[dict(x) for x in c.execute('SELECT j.date,j.workorder_id,w.workflow FROM contract_service_jobs j JOIN workorders w ON w.id=j.workorder_id WHERE service_id=? ORDER BY j.date',(row['id'],)) if scopes.allowed(c,user,'workorders',x['workorder_id'])];items.append(row)
 return {'contract':contract,'items':items}

def save(c,user,cid,body,sid=None):
 require(user,'contracts',True);contract=record(c,'contracts',cid)
 if contract['status'] not in ('Concept','Actief'):raise Problem('Contract is afgesloten.',409)
 if sid:
  old=record(c,'contract_services',sid)
  if old['contract_id']!=cid:raise Problem('Dienst niet gevonden.',404)
  version(old,body.get('version'))
  if c.execute('SELECT 1 FROM contract_service_jobs WHERE service_id=?',(sid,)).fetchone():raise Problem('Dienst heeft werkbonnen. Bestaande afspraken blijven behouden; maak een nieuwe dienst voor een volgende periode.',409)
 d=definition(c,contract,body.get('definition'));values={'name':text(body.get('name',''),150,True),'definition':json.dumps(d,ensure_ascii=False)}
 if sid:values['version']=old['version']+1;update(c,'contract_services',sid,values)
 else:sid=insert(c,'contract_services',{'contract_id':cid,**values})
 audit(c,user,'service_save','contracts',cid);return detail(c,user,cid)

def generate(c,user,cid,sid,body):
 require(user,'contracts',True);require(user,'workorders',True)
 service=record(c,'contract_services',sid)
 if service['contract_id']!=cid:raise Problem('Dienst niet gevonden.',404)
 version(service,body.get('version'));contract=record(c,'contracts',cid);d=definition(c,contract,json.loads(service['definition']))
 if contract['status']!='Actief':raise Problem('Activeer eerst het contract.',409)
 if len(d['weeks'] if d['kind']=='weekly' else d['dates'])!=d['count']:raise Problem('Selecteer eerst precies het afgesproken aantal lesweken of bezoekdatums.',409)
 slots=body.get('slots')
 if not isinstance(slots,dict):raise Problem('Vul expliciete tijdvakken en teamgrootte in.')
 from .workorders import save as work_save
 created=[];existing=0
 for day in d['selected']:
  if c.execute('SELECT 1 FROM contract_service_jobs WHERE service_id=? AND date=?',(sid,day)).fetchone():existing+=1;continue
  slot=slots.get(str(date_value(day).weekday()) if d['kind']=='weekly' else day,{})
  capacity=slot.get('capacity')
  if type(capacity)!=int or not 1<=capacity<=100:raise Problem('Kies expliciet de teamgrootte per tijdvak.')
  times={'date':day,'start_time':slot.get('start_time',''),'end_time':slot.get('end_time','')}
  duration=Decimal(str(interval(times)))
  if d['kind']=='weekly' and abs(duration*capacity-Decimal(d['hours'][str(date_value(day).weekday())]))>Decimal('0.000001'):raise Problem('Tijdvak × teamgrootte moet gelijk zijn aan het afgesproken dagurenbudget.')
  work=work_save(c,user,{'contract_id':cid,'object_id':d['object_id'],'description':service['name'],'service':service['name'],'capacity':capacity,**times})
  for task in d['tasks']:insert(c,'checklist',{'workorder_id':work['id'],'title':task})
  insert(c,'contract_service_jobs',{'service_id':sid,'date':day,'workorder_id':work['id']});created.append(work['id'])
 audit(c,user,'service_generate','contracts',cid,str(len(created))+' conceptwerkbonnen');return {'created':created,'existing':existing}

def demo(c,user,modules):
 if user['role'] not in ('admin','company_admin'):raise Problem('Alleen beheer mag een demonstratie toevoegen.',403)
 previous=c.execute("SELECT value FROM settings WHERE key='school_demo_contract'").fetchone()
 if previous and c.execute('SELECT 1 FROM contracts WHERE id=?',(json.loads(previous[0]),)).fetchone():return detail(c,user,json.loads(previous[0]))
 from .routes import entity_save
 year=dt.date.today().year+1
 customer=entity_save(c,user,'customers',{'name':'FICTIEF — Onderwijsstichting Voorbeeld','billing_address':'Fictieve Factuurstraat 1, Demostad','email':'administratie@voorbeeld.invalid'},modules)
 obj=entity_save(c,user,'objects',{'name':'FICTIEF — Basisschool Zonnewijzer','customer_id':customer['id'],'address':'Fictieve Schoolstraat 2','city':'Demostad'},modules)
 contract=entity_save(c,user,'contracts',{'name':'FICTIEF — Schoolcontract met twee diensten','customer_id':customer['id'],'object_id':obj['id'],'monthly_value':'0','start_date':f'{year}-01-01','end_date':f'{year}-12-31','status':'Actief'},modules)
 first=dt.date(year,1,1);first+=dt.timedelta(days=(-first.weekday())%7)
 weeks=[str(first+dt.timedelta(weeks=i)) for i in range(40)]
 save(c,user,contract['id'],{'name':'FICTIEF — Interieurverzorging','definition':{'object_id':obj['id'],'kind':'weekly','count':40,'hours':{'0':'2','1':'2','2':'3','3':'2','4':'2.5'},'weeks':weeks,'tasks':['Fictieve bestektaak: vloeren reinigen','Fictieve bestektaak: sanitair controleren']}})
 result=save(c,user,contract['id'],{'name':'FICTIEF — Glasbewassing','definition':{'object_id':obj['id'],'kind':'periodic','count':4,'dates':[],'tasks':['Buitenzijde gevelglas','Binnenzijde gevelglas','Separatieglas']}})
 c.execute("INSERT INTO settings(key,value) VALUES('school_demo_contract',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(json.dumps(contract['id']),));return result
