"""Persistente inklokregistratie; definitieve uren volgen de bestaande validatie."""
import datetime as dt
from zoneinfo import ZoneInfo
from domain import Problem
from .common import record,insert,update,audit,text,version
from .access import require
from .workorders import visible
from . import timekeeping

def employee(user,body):
    if user['role']=='employee':
        if body.get('employee_id') and str(body['employee_id'])!=str(user['employee_id']):raise Problem('Alleen eigen tijdklok toegestaan.',403)
        return user['employee_id']
    require(user,'hours',True)
    try:return int(body['employee_id'])
    except (KeyError,ValueError,TypeError):raise Problem('Kies een medewerker.')

def start(c,user,body):
    eid=employee(user,body);work=visible(c,user,int(body['workorder_id']))
    if work['workflow'] not in ('Toegewezen','In uitvoering','Correctie'):raise Problem('Klok in bij een toegewezen of lopende opdracht.',409)
    if not c.execute("SELECT 1 FROM shifts WHERE workorder_id=? AND employee_id=? AND status!='Geannuleerd'",(work['id'],str(eid))).fetchone():raise Problem('Medewerker niet ingepland op deze opdracht.',403)
    if c.execute("SELECT 1 FROM time_clocks WHERE employee_id=? AND state='Actief'",(eid,)).fetchone():raise Problem('Er loopt al een tijdklok voor deze medewerker.',409)
    rid=insert(c,'time_clocks',{'employee_id':eid,'workorder_id':work['id'],'starts_at':dt.datetime.now(ZoneInfo('Europe/Amsterdam')).isoformat(timespec='seconds'),'created_by':user['id']});audit(c,user,'clock_in','time_clocks',rid);return record(c,'time_clocks',rid)

def finish(c,user,rid,body):
    row=record(c,'time_clocks',rid)
    if user['role']=='employee':
        if row['employee_id']!=user.get('employee_id'):raise Problem('Tijdklok niet gevonden.',404)
    else:require(user,'hours',True)
    version(row,body.get('version'))
    if row['state']!='Actief':raise Problem('Tijdklok is al afgesloten.',409)
    if body.get('cancel'):
        reason=text(body.get('reason',''),1000,True);update(c,'time_clocks',rid,{'state':'Geannuleerd','reason':reason,'version':row['version']+1});audit(c,user,'clock_cancel','time_clocks',rid,reason)
    else:
        result=timekeeping.save(c,user,{'employee_id':row['employee_id'],'workorder_id':row['workorder_id'],'starts_at':row['starts_at'],'ends_at':dt.datetime.now(ZoneInfo('Europe/Amsterdam')).isoformat(timespec='seconds'),'break_minutes':body.get('break_minutes',0),'reason':body.get('reason','')})
        update(c,'time_clocks',rid,{'state':'Afgesloten','hours_id':result['id'],'version':row['version']+1});audit(c,user,'clock_out','time_clocks',rid)
    return record(c,'time_clocks',rid)

def listing(c,user):
    from . import scopes
    if user['role']=='employee':return scopes.select(c,user,'time_clocks',"employee_id=? AND state='Actief'",(user['employee_id'],))
    from . import scopes
    require(user,'hours');return scopes.select(c,user,'time_clocks',"state='Actief'",order='id',limit=500)
