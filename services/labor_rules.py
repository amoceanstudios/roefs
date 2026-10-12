"""Configureerbare operationele grenzen; geen juridische/CAO-certificering."""
import datetime as dt,json
from domain import Problem,interval,date_value
from zoneinfo import ZoneInfo
DEMO={'enabled':False,'label':'Fictieve demonstratieregels — juridisch niet gevalideerd','daily_hours':10,'weekly_hours':40,'minimum_rest_hours':11,'break_after_hours':5.5,'minimum_break_minutes':30}
def validate(value):
    if not isinstance(value,dict) or set(value)!=set(DEMO) or not isinstance(value['enabled'],bool):raise Problem('Vul alle arbeidstijdregels in met een expliciete aan/uit-keuze.')
    if not isinstance(value['label'],str) or not 1<=len(value['label'])<=200:raise Problem('Geef het regelprofiel een naam.')
    limits={'daily_hours':24,'weekly_hours':168,'minimum_rest_hours':48,'break_after_hours':24,'minimum_break_minutes':180}
    for k,maximum in limits.items():
        if isinstance(value[k],bool) or not isinstance(value[k],(int,float)) or not 0<=value[k]<=maximum:raise Problem('Arbeidstijdregel buiten bereik: '+k)
    return value

def issues(c,row,exclude=0):
    saved=c.execute("SELECT value FROM settings WHERE key='labor_rules'").fetchone()
    rules=json.loads(saved[0]) if saved else DEMO
    if not rules['enabled'] or not row.get('employee_id') or row.get('status')=='Geannuleerd':return []
    reasons=[];day=date_value(row['date']);week=day-dt.timedelta(days=day.weekday());span=interval(row);pause=int(row.get('break_minutes') or 0)
    start=dt.datetime.fromisoformat(row['date']+'T'+row['start_time']);end=dt.datetime.fromisoformat(row['date']+'T'+row['end_time'])
    shifts=[dict(x) for x in c.execute("SELECT * FROM shifts WHERE employee_id=? AND date BETWEEN ? AND ? AND id!=? AND status!='Geannuleerd'",(str(row['employee_id']),str(week-dt.timedelta(days=2)),str(week+dt.timedelta(days=8)),exclude))]
    daily=span-pause/60;weekly=daily
    for other in shifts:
        hours=interval(other)-int(other.get('break_minutes') or 0)/60
        if other['date']==row['date']:daily+=hours
        if str(week)<=other['date']<=str(week+dt.timedelta(days=6)):weekly+=hours
        a=dt.datetime.fromisoformat(other['date']+'T'+other['start_time']);b=dt.datetime.fromisoformat(other['date']+'T'+other['end_time'])
        # Pauzes tussen diensten op dezelfde dag zijn geen dagelijkse rust.
        if other['date']!=row['date']:
            utc=lambda t:t.replace(tzinfo=ZoneInfo('Europe/Amsterdam')).astimezone(dt.timezone.utc)
            gap=(utc(start)-utc(b)).total_seconds()/3600 if b<=start else (utc(a)-utc(end)).total_seconds()/3600
            if 0<=gap<rules['minimum_rest_hours']:reasons.append('Minimumrust tussen werkdagen niet gehaald.')
    if daily>rules['daily_hours']:reasons.append('Dagmaximum van het geconfigureerde regelprofiel overschreden.')
    if weekly>rules['weekly_hours']:reasons.append('Weekmaximum van het geconfigureerde regelprofiel overschreden.')
    if span>rules['break_after_hours'] and pause<rules['minimum_break_minutes']:reasons.append('Onvoldoende geplande pauze volgens het regelprofiel.')
    return list(dict.fromkeys(reasons))
