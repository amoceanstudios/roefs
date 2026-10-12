"""Importcontract uit bestaande doelmodellen en bestaande bedrijfsvalidatie."""
import datetime as dt,re
from domain import Problem,REFERENCES,REQUIRED,LABELS,STATUSES,validate
from .common import record,insert,update,audit,text
from .migrations import EXTRA
from .migration_models import MODELS,REFS as MODEL_REFS,REQUIRED as MODEL_REQUIRED

EXCLUDED={'invoices','ledger','payroll'}
REFS={**REFERENCES,**MODEL_REFS,'team_id':'teams','manager_id':'employees','workorder_id':'workorders','from_object':'objects','to_object':'objects'}
LABEL={**LABELS,'external_id':'Externe sleutel','existing_id':'Bestaand intern nummer (optioneel)','name':'Naam','description':'Omschrijving','instructions':'Werkinstructies','contract_hours':'Contracturen per week','monthly_value':'Maandbedrag','phone':'Telefoon','email':'E-mail','status':'Status','date':'Datum','starts_at':'Start met tijdzone','ends_at':'Einde met tijdzone','team_id':'Teamnummer','program_id':'Werkprogrammanummer','room_id':'Ruimtenummer','service_type_id':'Diensttypenummer','start_time':'Begintijd','end_time':'Eindtijd','hours':'Uren','contact':'Contactpersoon','city':'Plaats','region':'Rayon','department':'Afdeling','floor':'Verdieping','area':'Oppervlakte','frequency':'Frequentie','severity':'Ernst','title':'Titel','notes':'Notities','billing_address':'Factuuradres','customer_number':'Klantnummer','contract_number':'Contractnummer','start_date':'Begindatum','end_date':'Einddatum','address':'Adres','type':'Type','role':'Functie','score':'Score','inspector':'Inspecteur','capacity':'Teamgrootte'}

LABEL.update({'service_categories':'Dienstcategorieën','renewal_date':'Verlengdatum','service':'Dienst','manager_id':'Leidinggevende','skills':'Vaardigheden','emergency_available':'Noodbeschikbaarheid (0 of 1)','workorder_id':'Werkopdrachtnummer','planner_notes':'Planningsnotities','break_minutes':'Pauze in minuten','reason':'Reden','priority':'Prioriteit','serial':'Serienummer','inspection_date':'Keuringsdatum','maintenance_date':'Onderhoudsdatum','issued_at':'Uitgiftedatum','driver':'Bestuurder','subject':'Onderwerp','code':'Artikelcode','rate':'Tarief','vat_rate':'Btw-percentage'})

def registry(modules):
 from .routes import RESOURCES
 result={}
 for table,(label,fields) in modules.items():
  if table in EXCLUDED:continue
  fields=fields+list(EXTRA.get(table,{}));fields=[f for f in fields if f not in ('approved_by','workflow')]
  if table=='workorders':fields=['object_id','employee_id','description','date','start_time','end_time','capacity','contract_id','service','priority'];required=['object_id','description','date','start_time','end_time','capacity']
  elif table=='shifts':fields+=['break_minutes'];required=REQUIRED[table]
  else:required=REQUIRED[table]
  result[table]={'label':label,'fields':list(dict.fromkeys(['external_id','existing_id']+fields)),'required':['external_id']+required,'statuses':STATUSES[table] if table!='workorders' else ['Concept']}
 for table,(label,permission,fields) in RESOURCES.items():
  if table in ('certifications','travel_estimates'):continue
  required=MODEL_REQUIRED.get(table,{'contacts':['customer_id','name'],'communications':['customer_id','date','subject'],'teams':['name'],'articles':['code','name']}.get(table,['name']))
  result[table]={'label':label,'fields':['external_id','existing_id']+fields,'required':['external_id']+required,'statuses':['Actief','Inactief'] if table in MODELS else []}
 for table,meta in result.items():
  meta['relations']={k:v for k,v in REFS.items() if k in meta['fields']};meta['dependencies']=sorted(set(meta['relations'].values()));meta['labels']={f:LABEL.get(f,f.replace('_',' ')) for f in meta['fields']}
 return result

def norm(value):return re.sub(r'[^a-z0-9]','',value.casefold())
def suggest(headers,table,meta,rows=None):
 synonyms={'external_id':['externid','externalid','bronid','bronnummer','id'],'name':['naam','bedrijfsnaam','klantnaam','medewerkernaam','objectnaam'],'customer_id':['klantnummer','debiteurnummer','klantid'],'employee_id':['personeelsnummer','medewerkernummer'],'object_id':['objectnummer','locatienummer'],'contract_id':['contractnummer'],'phone':['telefoonnummer'],'contract_hours':['contracturen'],'monthly_value':['maandbedrag']}
 synonyms['external_id']+= {'customers':['klantnummer','debiteurnummer'],'employees':['personeelsnummer','medewerkernummer'],'objects':['objectnummer','locatienummer'],'contracts':['contractnummer'],'shifts':['planningnummer'],'workorders':['opdrachtnummer'],'hours':['urennummer']}.get(table,[])
 candidates={}
 for field in meta['fields']:
  for name in [field,meta['labels'][field]]+synonyms.get(field,[]):candidates.setdefault(norm(name),set()).add(field)
 result={};used=set()
 for header in headers:
  matches=candidates.get(norm(header),set())
  if table in ('customers','contracts') and norm(header) in ('klantnummer','debiteurnummer','contractnummer'):matches={'external_id'}
  if len(matches)==1:
   field=next(iter(matches))
   if field not in used:result[header]=field;used.add(field)
 # Alleen een eenduidig inhoudstype vult een onbekende kolom aan; nummers/datums
 # zijn zonder betekenisvolle kop te ambigu en worden nooit geraden.
 for index,header in enumerate(headers):
  if header in result or norm(header) in candidates:continue
  sample=[r['values'][index].strip() for r in (rows or [])[:100] if r['values'][index].strip()]
  if sample and 'email' in meta['fields'] and 'email' not in used and all(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',x) for x in sample):result[header]='email';used.add('email')
 return result

def convert(field,value):
 value=value.strip()
 if not value:return ''
 if field=='date' or field.endswith('_date') or field in ('issued_at','expires_on'):
  for fmt in ('%Y-%m-%d','%d-%m-%Y','%d/%m/%Y','%d.%m.%Y'):
   try:return dt.datetime.strptime(value,fmt).date().isoformat()
   except ValueError:pass
  raise Problem(LABEL.get(field,field)+': gebruik JJJJ-MM-DD of DD-MM-JJJJ.')
 return value

def write(c,user,table,values,modules,rid=None):
 from .routes import entity_save,resource_save,RESOURCES
 from . import planning,workorders
 old=record(c,table,rid) if rid else {}
 payload={**values,**({'version':old['version']} if old else {})}
 if table=='shifts':return planning.save(c,user,payload,rid)
 if table=='workorders':return workorders.save(c,user,payload,rid)
 if table in RESOURCES:return resource_save(c,user,table,payload,rid)
 if table=='hours':
  # Historische uren met dagtotalen blijven ondersteund; nieuwe registraties volgen bestaande tijdvakvalidatie.
  if values.get('starts_at') or values.get('ends_at'):
   from .timekeeping import save,review
   status=values.get('status','Ingediend');result=save(c,user,{k:v for k,v in payload.items() if k in ('employee_id','workorder_id','starts_at','ends_at','break_minutes','reason','version')},rid)
   from decimal import Decimal
   if values.get('hours') and Decimal(str(values['hours']).replace(',','.'))!=Decimal(result['hours']):raise Problem('Bronuren komen niet overeen met tijdvak en pauze.')
   if values.get('date') and values['date']!=result['date']:raise Problem('Brondatum komt niet overeen met de start van het tijdvak.')
   if status in ('Goedgekeurd','Afgewezen'):result=review(c,user,result['id'],{'version':result['version'],'status':status,'reason':values.get('reason','')})
   elif status!='Ingediend':raise Problem('Ongeldige urenstatus.')
   return result
  fields=modules[table][1];row=validate(c,table,{k:v for k,v in values.items() if k in fields},fields,old)
  if values.get('workorder_id'):
   work=record(c,'workorders',values['workorder_id'])
   if str(work['employee_id'])!=str(row['employee_id']) and not c.execute("SELECT 1 FROM shifts WHERE workorder_id=? AND employee_id=? AND status!='Geannuleerd'",(work['id'],row['employee_id'])).fetchone():raise Problem('Urenmedewerker is niet aan de opdracht gekoppeld.')
   if row.get('shift_id') and str(record(c,'shifts',row['shift_id'])['workorder_id'])!=str(work['id']):raise Problem('Dienst en werkopdracht komen niet overeen.')
   row['workorder_id']=work['id']
  if any(values.get(k) for k in ('break_minutes','reason')):raise Problem('Pauze/redenen vereisen een volledig tijdvak met tijdzone.')
  if rid:update(c,table,rid,row)
  else:rid=insert(c,table,row)
  audit(c,user,'migration_write',table,rid);return record(c,table,rid)
 return entity_save(c,user,table,payload,modules,rid)
