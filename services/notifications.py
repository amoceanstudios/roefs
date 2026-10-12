"""Dagelijkse lokale deadlinecontrole; deduplicerend, geen externe aflevering."""
import datetime as dt
from .common import notify,audit
from .access import permitted

def deadlines(c,user=None):
    end=str(dt.date.today()+dt.timedelta(days=30))
    rules=[('certifications','expires_on','Certificaat verloopt','employees'),('contracts','end_date','Contract verloopt','contracts'),('contracts','renewal_date','Contractverlenging beoordelen','contracts'),('assets','inspection_date','Materieelkeuring verloopt','assets'),('assets','maintenance_date','Materieelonderhoud gepland','assets'),('vehicles','inspection_date','Voertuigkeuring verloopt','vehicles'),('vehicles','maintenance_date','Voertuigonderhoud gepland','vehicles')]
    for table,field,title,target in rules:
        roles={role for role in ('admin','company_admin','operations','planner','supervisor','finance') if permitted({'role':role},target)}
        for row in c.execute(f"SELECT * FROM {table} WHERE {field} IS NOT NULL AND {field}!='' AND {field}<=?",(end,)).fetchall():notify(c,f'reminder:{table}:{field}:{row["id"]}:{row[field]}',title+' op '+row[field],target,roles=roles)
    audit(c,user or {'username':'Automatische deadlinecontrole'},'reminders','notifications',0)

def daily(c):
    day=str(dt.date.today());c.execute('BEGIN IMMEDIATE')
    previous=c.execute("SELECT value FROM settings WHERE key='last_deadline_scan'").fetchone()
    if not previous or previous[0]!=day:
        deadlines(c);c.execute("INSERT INTO settings(key,value) VALUES('last_deadline_scan',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(day,))
    c.commit()
