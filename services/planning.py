"""Deterministische kwalificaties, teamcontrole, reserveringen en transacties."""
import datetime as dt,json
from domain import Problem,schedule_issues,interval,date_value
from .common import record,version,words,text,update,insert,audit,notify
from .access import require

def qualification_issues(c,employee,work,day):
    reasons=[]
    missing=words(work.get('required_skills'))-words(employee.get('skills'))
    if missing:reasons.append('Vaardigheden ontbreken: '+', '.join(sorted(missing)))
    for name in sorted(words(work.get('required_certifications'))):
        cert=c.execute('SELECT expires_on FROM certifications WHERE employee_id=? AND lower(name)=?',(employee['id'],name)).fetchone()
        if not cert:reasons.append('Certificaat ontbreekt: '+name)
        elif cert['expires_on']<day:reasons.append('Certificaat verlopen: '+name)
    if work.get('team_id') and employee.get('team_id')!=work['team_id']:reasons.append('Medewerker behoort niet tot het vereiste team.')
    return reasons

def issues(c,row,exclude=0,base_issues=None):
    reasons=schedule_issues(c,row,exclude,False) if base_issues is None else base_issues
    if row.get('workorder_id'):
        work=record(c,'workorders',row['workorder_id'])
        if str(work['object_id'])!=str(row['object_id']):reasons.append('Locatie komt niet overeen met werkopdracht.')
        if work['workflow'] not in ('Concept','Gepland','Toegewezen','In uitvoering'):reasons.append('Werkopdracht kan in deze status niet worden ingepland.')
        if row.get('employee_id'):
            reasons+=qualification_issues(c,record(c,'employees',row['employee_id']),work,row['date'])
        for aid in asset_ids(work):
            asset=record(c,'assets',aid)
            if asset['status'] in ('Onderhoud','Buiten gebruik'):reasons.append('Materieel niet beschikbaar: '+asset['name'])
            if asset['inspection_date'] and asset['inspection_date']<row['date']:reasons.append('Keuring verlopen: '+asset['name'])
            if asset.get('maintenance_date') and asset['maintenance_date']==row['date']:reasons.append('Onderhoud gepland: '+asset['name'])
            if c.execute('SELECT 1 FROM reservations WHERE asset_id=? AND workorder_id!=? AND date=? AND start_time<? AND end_time>?',(aid,work['id'],row['date'],row['end_time'],row['start_time'])).fetchone():reasons.append('Materieel al gereserveerd: '+asset['name'])
    if row.get('employee_id'):
        for other in c.execute("SELECT * FROM shifts WHERE employee_id=? AND date=? AND id!=? AND status!='Geannuleerd'",(str(row['employee_id']),row['date'],exclude)):
            before=other['end_time']<=row['start_time'];after=row['end_time']<=other['start_time']
            if not before and not after:continue
            pair=(other['object_id'],row['object_id']) if before else (row['object_id'],other['object_id'])
            travel=c.execute('SELECT minutes FROM travel_estimates WHERE from_object=? AND to_object=?',pair).fetchone()
            if travel:
                from domain import time_value
                gap=time_value(row['start_time'])-time_value(other['end_time']) if before else time_value(other['start_time'])-time_value(row['end_time'])
                if gap<travel[0]:reasons.append('Onvoldoende tijd voor de geconfigureerde reistijd.')
    return reasons

def asset_ids(work):
    values=str(work.get('required_assets') or '').split(',')
    try:return sorted({int(x.strip()) for x in values if x.strip()})
    except ValueError:raise Problem('Materieel: gebruik bestaande nummers gescheiden door komma’s.')

def save(c,user,body,rid=None):
    require(user,'shifts',True)
    previous=record(c,'shifts',rid) if rid else {}
    if previous:version(previous,body.get('version'))
    allowed={'object_id','employee_id','date','start_time','end_time','status','workorder_id','planner_notes'}
    if set(body)-allowed-{'version'}:raise Problem('Onbekend planningsveld.')
    row={k:body.get(k,previous.get(k,'')) for k in allowed}
    row['status']=row['status'] or 'Gepland';row['workorder_id']=int(row['workorder_id']) if row['workorder_id'] else None
    if row['status'] not in ('Gepland','Bevestigd','Afgerond','Geannuleerd'):raise Problem('Ongeldige dienststatus.')
    for key in allowed-{'workorder_id'}:row[key]=text(row[key])
    record(c,'objects',row['object_id']);interval(row)
    if row['employee_id']:record(c,'employees',row['employee_id'])
    if row['workorder_id']:
        work=record(c,'workorders',row['workorder_id'])
        if work['date']!=row['date'] or work['start_time']!=row['start_time'] or work['end_time']!=row['end_time']:raise Problem('Pas eerst de datum en tijden van de werkopdracht aan; alle teamdiensten volgen hetzelfde tijdvak.',409)
    problems=issues(c,row,rid or 0)
    if row['status']!='Geannuleerd' and problems:raise Problem(' '.join(problems),409)
    if rid:update(c,'shifts',rid,row)
    else:rid=insert(c,'shifts',row)
    current=record(c,'shifts',rid)
    insert(c,'schedule_history',{'shift_id':rid,'actor_id':user['id'],'before_json':json.dumps(previous),'after_version':current['version']})
    for wid in {previous.get('workorder_id'),row['workorder_id']}-{None,''}:
        work=record(c,'workorders',wid)
        c.execute('DELETE FROM reservations WHERE workorder_id=?',(wid,))
        active=c.execute("SELECT 1 FROM shifts WHERE workorder_id=? AND status!='Geannuleerd'",(wid,)).fetchone()
        if active:
            for aid in asset_ids(work):insert(c,'reservations',{'asset_id':aid,'workorder_id':wid,'date':work['date'],'start_time':work['start_time'],'end_time':work['end_time']})
    for eid in {previous.get('employee_id'),row['employee_id']}-{None,''}:
        notify(c,f'shift:{rid}:{current["version"]}','Je planning is gewijzigd.','shifts',employee_id=eid)
    audit(c,user,'update' if previous else 'create','shifts',rid)
    return current

def suggestions(c,user,body):
    require(user,'shifts',True)
    row={k:text(body.get(k,'')) for k in ('object_id','date','start_time','end_time')};interval(row)
    work=record(c,'workorders',body['workorder_id']) if body.get('workorder_id') else {}
    row['workorder_id']=work.get('id');row['status']='Gepland'
    settings=c.execute("SELECT value FROM settings WHERE key='planning_weights'").fetchone()
    weights=json.loads(settings[0]) if settings else {'availability':20,'workload':2,'familiarity':10,'region':10,'skills':10}
    day=date_value(row['date']);start=str(day-dt.timedelta(days=day.weekday()));end=str(day+dt.timedelta(days=6-day.weekday()))
    location=record(c,'objects',row['object_id'])
    candidates=[];excluded=[]
    for raw in c.execute('SELECT * FROM employees ORDER BY id').fetchall():
        emp=dict(raw);proposal={**row,'employee_id':str(emp['id'])};problems=issues(c,proposal,body.get('exclude_shift_id',0))
        if problems:excluded.append({'id':emp['id'],'name':emp['name'],'reasons':problems});continue
        workload=sum(interval(dict(x)) for x in c.execute("SELECT * FROM shifts WHERE employee_id=? AND date BETWEEN ? AND ? AND status!='Geannuleerd' AND id!=?",(str(emp['id']),start,end,body.get('exclude_shift_id',0))))
        available=bool(c.execute("SELECT 1 FROM availability WHERE employee_id=? AND date=? AND status='Beschikbaar'",(str(emp['id']),row['date'])).fetchone())
        familiar=bool(c.execute('SELECT 1 FROM shifts WHERE employee_id=? AND object_id=?',(str(emp['id']),row['object_id'])).fetchone())
        region=bool(emp.get('region') and emp['region']==location.get('region'))
        score=weights.get('availability',20)*available-weights.get('workload',2)*workload+weights.get('familiarity',10)*familiar+weights.get('region',10)*region+weights.get('skills',10)*len(words(emp.get('skills'))&words(work.get('required_skills')))
        reasons=[('Beschikbaarheid geregistreerd' if available else 'Beschikbaarheid niet bevestigd'),f'{workload:g} uur ingepland deze week',('Bekend op locatie' if familiar else 'Nog niet op locatie ingepland'),('Voorkeursregio komt overeen' if region else 'Geen overeenkomende voorkeursregio')]
        candidates.append({'id':emp['id'],'name':emp['name'],'score':round(score,2),'reasons':reasons,'planned_hours':workload})
    return {'candidates':sorted(candidates,key=lambda x:(-x['score'],x['id'])),'excluded':excluded,'weights':weights,'travel':'Alleen handmatig vastgelegde reistijden met bron worden gecontroleerd. Ontbrekende reistijd wordt niet geschat.'}

def undo(c,user,body):
    require(user,'shifts',True)
    h=record(c,'schedule_history',body['history_id']);current=record(c,'shifts',h['shift_id'])
    if h['undone'] or current['version']!=h['after_version']:raise Problem('Deze wijziging kan niet veilig worden teruggedraaid.',409)
    before=json.loads(h['before_json'])
    if not before:raise Problem('Nieuwe dienst: annuleer deze via het formulier.',409)
    fields={'object_id','employee_id','date','start_time','end_time','status','workorder_id','planner_notes'}
    result=save(c,user,{k:before[k] for k in fields}|{'version':current['version']},current['id'])
    update(c,'schedule_history',h['id'],{'undone':1});audit(c,user,'undo','shifts',current['id']);return result

def assess_many(c,rows):
    """Batchcontrole voor rapporten: vaste aantallen queries i.p.v. queries per dienst.
    Definitieve mutatiecontrole blijft issues() binnen de schrijftransactie.
    """
    rows=[x for x in rows if x['status'] not in ('Geannuleerd','Afgerond')]
    if not rows:return []
    lo=min(x['date'] for x in rows);hi=max(x['date'] for x in rows)
    employees={str(x['id']):dict(x) for x in c.execute('SELECT * FROM employees')}
    works={x['id']:dict(x) for x in c.execute('SELECT * FROM workorders WHERE date BETWEEN ? AND ?',(lo,hi))}
    assets={x['id']:dict(x) for x in c.execute('SELECT * FROM assets')}
    certs={(str(x['employee_id']),x['name'].casefold()):x['expires_on'] for x in c.execute('SELECT * FROM certifications')}
    travel={(str(x['from_object']),str(x['to_object'])):x['minutes'] for x in c.execute('SELECT * FROM travel_estimates')}
    shifts={};available={};leave={};reserved={}
    for sh in c.execute("SELECT * FROM shifts WHERE date BETWEEN ? AND ? AND status!='Geannuleerd'",(lo,hi)):shifts.setdefault((sh['employee_id'],sh['date']),[]).append(dict(sh))
    for row in c.execute('SELECT * FROM availability WHERE date BETWEEN ? AND ?',(lo,hi)):available.setdefault((row['employee_id'],row['date']),[]).append(dict(row))
    for row in c.execute("SELECT * FROM leave WHERE start_date<=? AND end_date>=? AND status IN ('Goedgekeurd','Ziek','Ziekgemeld')",(hi,lo)):leave.setdefault(row['employee_id'],[]).append(dict(row))
    for row in c.execute('SELECT * FROM reservations WHERE date BETWEEN ? AND ?',(lo,hi)):reserved.setdefault((row['asset_id'],row['date']),[]).append(dict(row))
    output=[]
    from domain import time_value
    for row in rows:
        reasons=[];eid=str(row['employee_id']);key=(eid,row['date']);emp=employees.get(eid)
        try:interval(row)
        except Problem as exc:output.append({'id':row['id'],'reasons':[str(exc)]});continue
        if eid and not emp:reasons.append('Medewerker ontbreekt.')
        if emp and emp['status']!='Actief':reasons.append('Medewerker is niet actief.')
        for other in shifts.get(key,[]):
            if row['id']==other['id']:continue
            if other['start_time']<row['end_time'] and other['end_time']>row['start_time']:reasons.append('Roosterconflict met dienst #'+str(other['id']))
            else:
                before=other['end_time']<=row['start_time'];pair=(other['object_id'],row['object_id']) if before else (row['object_id'],other['object_id']);minutes=travel.get(pair)
                if minutes is not None:
                    gap=time_value(row['start_time'])-time_value(other['end_time']) if before else time_value(other['start_time'])-time_value(row['end_time'])
                    if gap<minutes:reasons.append('Onvoldoende tijd voor de geconfigureerde reistijd.')
        if any(x['start_date']<=row['date']<=x['end_date'] for x in leave.get(eid,[])):reasons.append('Medewerker heeft goedgekeurd verlof of geregistreerd verzuim.')
        entries=available.get(key,[])
        if any(x['status']=='Niet beschikbaar' and x['start_time']<row['end_time'] and x['end_time']>row['start_time'] for x in entries):reasons.append('Medewerker heeft zich voor deze tijd niet beschikbaar gemeld.')
        windows=sorted((x['start_time'],x['end_time']) for x in entries if x['status']=='Beschikbaar')
        if windows:
            covered=row['start_time']
            for start,end in windows:
                if start<=covered:covered=max(covered,end)
            if covered<row['end_time']:reasons.append('Dienst valt buiten de opgegeven beschikbaarheid.')
        work=works.get(row.get('workorder_id'))
        if work:
            if emp:
                missing=words(work.get('required_skills'))-words(emp.get('skills'))
                if missing:reasons.append('Vaardigheden ontbreken: '+', '.join(sorted(missing)))
                for name in words(work.get('required_certifications')):
                    expiry=certs.get((eid,name))
                    if not expiry or expiry<row['date']:reasons.append('Certificaat ontbreekt of verlopen: '+name)
                if work['team_id'] and emp['team_id']!=work['team_id']:reasons.append('Medewerker behoort niet tot het vereiste team.')
            for aid in asset_ids(work):
                asset=assets.get(aid)
                if not asset:reasons.append('Materieel ontbreekt.');continue
                if asset['status'] in ('Onderhoud','Buiten gebruik') or asset['inspection_date'] and asset['inspection_date']<row['date'] or asset['maintenance_date']==row['date']:reasons.append('Materieel niet beschikbaar of keuring verlopen: '+asset['name'])
                if any(x['workorder_id']!=work['id'] and x['start_time']<row['end_time'] and x['end_time']>row['start_time'] for x in reserved.get((aid,row['date']),[])):reasons.append('Materieel al gereserveerd: '+asset['name'])
        if reasons:output.append({'id':row['id'],'reasons':reasons})
    return output
