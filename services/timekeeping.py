"""Tijdintervallen met expliciete UTC-offset; DST wordt niet gegokt."""
import datetime as dt
from decimal import Decimal
from zoneinfo import ZoneInfo
from domain import Problem
from .common import *
from .access import require,permitted
from .workorders import visible

def timestamp(value):
    try:value=dt.datetime.fromisoformat(value)
    except (ValueError,TypeError):raise Problem('Gebruik datum en tijd met tijdzone-offset.')
    if value.utcoffset() is None:raise Problem('Een tijdzone-offset is verplicht, ook tijdens zomer- en wintertijd.')
    local=value.astimezone(ZoneInfo('Europe/Amsterdam'))
    if local.replace(tzinfo=None)!=value.replace(tzinfo=None) or local.utcoffset()!=value.utcoffset():raise Problem('Tijd en UTC-offset passen niet bij Europe/Amsterdam.')
    return value.astimezone(dt.timezone.utc)
def save(c,user,body,rid=None):
    old=record(c,'hours',rid) if rid else {}
    if old:version(old,body.get('version'))
    if set(body)-{'employee_id','workorder_id','starts_at','ends_at','break_minutes','reason','version'}:raise Problem('Onbekend urenveld.')
    values={k:body.get(k,old.get(k)) for k in ('employee_id','workorder_id','starts_at','ends_at','break_minutes','reason')}
    eid=int(values['employee_id']);work=visible(c,user,int(values['workorder_id']))
    if user['role']=='employee':
        if eid!=user['employee_id'] or old.get('status') in ('Goedgekeurd','Akkoord'):raise Problem('Geen toegang tot deze urenregistratie.',403)
    else:require(user,'hours',True)
    record(c,'employees',eid)
    if work.get('workflow') in ('Factureerbaar','Geannuleerd') or c.execute('SELECT 1 FROM invoices WHERE workorder_id=?',(work['id'],)).fetchone():raise Problem('De opdracht is afgesloten voor urenwijzigingen.',409)
    if not c.execute("SELECT 1 FROM shifts WHERE employee_id=? AND workorder_id=? AND status!='Geannuleerd'",(str(eid),work['id'])).fetchone():raise Problem('Medewerker is niet aan de opdracht toegewezen.',403)
    start=timestamp(values['starts_at']);end=timestamp(values['ends_at']);br=int(values['break_minutes'] or 0)
    minutes=int((end-start).total_seconds()/60)
    if not 0<minutes<=24*60 or not 0<=br<minutes:raise Problem('Ongeldig tijdvak of ongeldige pauze (maximaal 24 uur).')
    for other in c.execute("SELECT * FROM hours WHERE employee_id=? AND id!=? AND status!='Afgewezen' AND starts_at IS NOT NULL",(str(eid),rid or 0)):
        if timestamp(other['starts_at'])<end and timestamp(other['ends_at'])>start:raise Problem('Urenregistraties overlappen.',409)
    reason=text(values['reason'] or '')
    if old and not reason:raise Problem('Bij correcties is een reden verplicht.')
    row={**values,'employee_id':str(eid),'workorder_id':work['id'],'date':values['starts_at'][:10],'hours':eur(Decimal(minutes-br)/60),'break_minutes':br,'reason':reason,'status':'Ingediend','approved_by':None,'shift_id':''}
    if rid:update(c,'hours',rid,row)
    else:rid=insert(c,'hours',row)
    audit(c,user,'update' if old else 'create','hours',rid,reason)
    notify(c,f'hours:{rid}:{record(c,"hours",rid)["version"]}','Uren wachten op beoordeling.','hours',roles={'admin','company_admin','supervisor','operations'})
    return record(c,'hours',rid)
def review(c,user,rid,body):
    if user['role'] not in {'admin','company_admin','operations','supervisor'}:raise Problem('Alleen leidinggevenden mogen uren beoordelen.',403)
    row=record(c,'hours',rid);version(row,body.get('version'))
    if row['status']!='Ingediend':raise Problem('Deze registratie is al beoordeeld.',409)
    status=body.get('status');reason=text(body.get('reason',''))
    if status not in ('Goedgekeurd','Afgewezen') or (status=='Afgewezen' and not reason):raise Problem('Kies een beoordeling en geef bij afwijzing een reden.')
    update(c,'hours',rid,{'status':status,'reason':reason,'approved_by':user['id']});audit(c,user,'review','hours',rid,status+' '+reason)
    notify(c,f'review:{rid}:{row["version"]}','Je uren zijn '+status.lower()+'.','hours',employee_id=row['employee_id'])
    return record(c,'hours',rid)
