"""Aandachtspunten met dezelfde recordselectie voor teller en doorklik."""
import datetime as dt
from zoneinfo import ZoneInfo
from .access import permitted

def home(c,user):
    now=dt.datetime.now(ZoneInfo('Europe/Amsterdam'));day=str(now.date());time=now.strftime('%H:%M');end=str(now.date()+dt.timedelta(days=30));employee=user.get('employee_id');cards=[]
    def add(title,tab,rows):cards.append({'title':title,'tab':tab,'ids':[x[0] for x in rows],'count':len(rows)})
    own=" AND employee_id=?" if user['role']=='employee' else '';args=[day]+([str(employee or -1)] if own else [])
    add('Opdrachten vandaag','calendar',c.execute("SELECT id FROM shifts WHERE date=? AND status!='Geannuleerd'"+own,args).fetchall())
    if permitted(user,'workorders'):add('Nog in te plannen opdrachten','workorders',c.execute("SELECT id FROM workorders WHERE workflow IN ('Concept','Gepland')").fetchall())
    if permitted(user,'hours',True):add('Uren ter beoordeling','time',c.execute("SELECT id FROM hours WHERE status='Ingediend'").fetchall())
    if permitted(user,'employees'):
        add('Nu als beschikbaar opgegeven','employees',c.execute("""SELECT DISTINCT e.id FROM employees e JOIN availability a ON a.employee_id=e.id WHERE e.status='Actief' AND a.date=? AND a.status='Beschikbaar' AND a.start_time<=? AND a.end_time>? AND NOT EXISTS(SELECT 1 FROM shifts s WHERE s.employee_id=e.id AND s.date=? AND s.status!='Geannuleerd' AND s.start_time<=? AND s.end_time>?) AND NOT EXISTS(SELECT 1 FROM leave l WHERE l.employee_id=e.id AND l.status IN ('Goedgekeurd','Ziek','Ziekgemeld') AND l.start_date<=? AND l.end_date>=?) AND NOT EXISTS(SELECT 1 FROM availability n WHERE n.employee_id=e.id AND n.date=? AND n.status='Niet beschikbaar' AND n.start_time<=? AND n.end_time>?)""",(day,time,time,day,time,time,day,day,day,time,time)).fetchall())
        add('Certificaten binnen 30 dagen of verlopen','certifications',c.execute('SELECT id FROM certifications WHERE expires_on<=?',(end,)).fetchall())
    if permitted(user,'assets'):add('Keuring of onderhoud binnen 30 dagen','assets',c.execute("SELECT id FROM assets WHERE inspection_date!='' AND inspection_date<=? OR maintenance_date IS NOT NULL AND maintenance_date!='' AND maintenance_date<=?",(end,end)).fetchall())
    if permitted(user,'alerts'):add('Open operationele meldingen','alerts',c.execute("SELECT id FROM alerts WHERE status!='Afgerond'").fetchall())
    return {'date':day,'cards':cards}
