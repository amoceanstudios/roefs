"""Atomaire reeksen van dagsegmenten; ieder segment blijft een gewone dienst."""
import datetime as dt,json
from domain import Problem,date_value
from .common import record,insert,update,version,text,audit
from .access import require
from . import planning

def create(c,user,body):
    require(user,'shifts',True)
    title=text(body.get('title',''),150,True);template=body.get('template')
    if not isinstance(template,dict) or template.get('workorder_id'):raise Problem('Gebruik een losse dienst of een opdrachtsjabloon voor de reeks.')
    start=date_value(body.get('start',''));end=date_value(body.get('end',''))
    if not 0<=(end-start).days<=366:raise Problem('Een reeks beslaat maximaal 367 dagen.')
    weekdays=body.get('weekdays',list(range(7)));every=body.get('every_weeks',1);exceptions=body.get('exceptions',[])
    if not isinstance(weekdays,list) or not weekdays or any(type(x)!=int or x not in range(7) for x in weekdays):raise Problem('Kies weekdagen 0 (maandag) tot 6 (zondag).')
    if type(every)!=int or not 1<=every<=52:raise Problem('Herhaal iedere 1 tot 52 weken.')
    if not isinstance(exceptions,list) or len(exceptions)>367:raise Problem('Ongeldige uitzonderingen.')
    exceptions={str(date_value(x)) for x in exceptions}
    if any(x<str(start) or x>str(end) for x in exceptions):raise Problem('Uitzonderingen moeten binnen de reeks vallen.')
    days=[start+dt.timedelta(days=i) for i in range((end-start).days+1)]
    days=[d for d in days if d.weekday() in weekdays and ((d-start).days//7)%every==0 and str(d) not in exceptions]
    if not 1<=len(days)<=100:raise Problem('Maak 1 tot 100 dagsegmenten per reeks.')
    work_template=body.get('work_template')
    if work_template is not None and not isinstance(work_template,dict):raise Problem('Ongeldig opdrachtsjabloon.')
    sid=insert(c,'planning_series',{'title':title,'definition':json.dumps(body,ensure_ascii=False)})
    items=[]
    for day in days:
        row={**template,'date':str(day)}
        if work_template is not None:
            from .workorders import save
            work=save(c,user,{**work_template,'date':str(day),'object_id':row['object_id'],'start_time':row['start_time'],'end_time':row['end_time']})
            row['workorder_id']=work['id']
        shift=planning.save(c,user,row)
        insert(c,'planning_occurrences',{'series_id':sid,'shift_id':shift['id']});items.append(shift)
    audit(c,user,'create','planning_series',sid)
    return {**record(c,'planning_series',sid),'items':items}

def change(c,user,sid,body):
    require(user,'shifts',True);series=record(c,'planning_series',sid);version(series,body.get('version'));reason=text(body.get('reason',''),1000,True)
    action=body.get('action');items=[]
    if action=='cancel' and series['status']=='Actief':
        expected=body.get('versions',{});snapshot=[]
        for entry in c.execute('SELECT shift_id FROM planning_occurrences WHERE series_id=?',(sid,)).fetchall():
            row=record(c,'shifts',entry['shift_id']);version(row,expected.get(str(row['id'])))
            if row['status']=='Afgerond':raise Problem('Een afgerond segment kan niet met de reeks worden geannuleerd.',409)
            if row['status']=='Geannuleerd':continue
            changed=planning.save(c,user,{'status':'Geannuleerd','version':row['version']},row['id']);snapshot.append({'id':row['id'],'status':row['status'],'version':changed['version']});items.append(changed)
        update(c,'planning_series',sid,{'snapshot':json.dumps(snapshot),'status':'Geannuleerd','version':series['version']+1})
    elif action=='restore' and series['status']=='Geannuleerd':
        for item in json.loads(series['snapshot']):
            row=record(c,'shifts',item['id']);version(row,item['version']);items.append(planning.save(c,user,{'status':item['status'],'version':row['version']},row['id']))
        update(c,'planning_series',sid,{'status':'Actief','snapshot':'[]','version':series['version']+1})
    else:raise Problem('Deze reeksactie past niet bij de actuele status.',409)
    audit(c,user,action,'planning_series',sid,reason)
    return {**record(c,'planning_series',sid),'items':items}

def listing(c,user):
    require(user,'shifts')
    from . import scopes
    rows=scopes.select(c,user,'planning_series',limit=100)
    for row in rows:
        row.pop('definition',None);row.pop('snapshot',None)
    for row in rows:row['items']=[dict(x) for x in c.execute('SELECT s.* FROM shifts s JOIN planning_occurrences o ON o.shift_id=s.id WHERE o.series_id=? ORDER BY s.date,s.id',(row['id'],))]
    for row in rows:row['items']=scopes.filter_rows(c,user,'shifts',row['items'])
    return {'items':rows,'limit':100}
