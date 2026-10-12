"""Werkopdrachtstatusmachine en mobiele uitvoering."""
import datetime as dt
from domain import Problem,date_value,interval
from .common import *
from .access import require,permitted
from .planning import issues,asset_ids
STATES=['Concept','Gepland','Toegewezen','In uitvoering','Voltooid','Goedgekeurd','Factureerbaar','Geannuleerd','Correctie']
TRANSITIONS={'Concept':{'Gepland','Geannuleerd'},'Gepland':{'Toegewezen','Geannuleerd','Concept'},'Toegewezen':{'In uitvoering','Geannuleerd','Gepland'},'In uitvoering':{'Voltooid','Geannuleerd'},'Voltooid':{'Goedgekeurd','Correctie'},'Correctie':{'In uitvoering','Geannuleerd'},'Goedgekeurd':{'Factureerbaar','Correctie'},'Factureerbaar':{'Correctie'},'Geannuleerd':{'Concept'}}
FIELDS={'contract_id','object_id','employee_id','description','date','hours','signed_by','priority','service','team_id','required_skills','required_certifications','required_assets','capacity','start_time','end_time','completion_notes'}
def visible(c,user,wid):
    work=record(c,'workorders',wid)
    if permitted(user,'workorders'):return work
    if user['role']=='employee' and user.get('employee_id') and (str(work['employee_id'])==str(user['employee_id']) or c.execute("SELECT 1 FROM shifts WHERE workorder_id=? AND employee_id=? AND status!='Geannuleerd'",(wid,str(user['employee_id']))).fetchone()):return work
    raise Problem('Werkopdracht niet gevonden.',404)
def save(c,user,body,rid=None):
    require(user,'workorders',True)
    old=record(c,'workorders',rid) if rid else {}
    if old:
        version(old,body.get('version'))
        if old.get('workflow') not in ('Concept','Gepland','Correctie',None,''):raise Problem('Open de opdracht eerst voor correctie.',409)
        if c.execute("SELECT 1 FROM shifts WHERE workorder_id=? AND status!='Geannuleerd'",(rid,)).fetchone():raise Problem('Annuleer eerst de gekoppelde diensten voordat je opdrachtgegevens wijzigt.',409)
    if set(body)-FIELDS-{'version'}:raise Problem('Onbekend opdrachtveld.')
    row={k:body.get(k,old.get(k,'')) for k in FIELDS}
    for k in FIELDS-{'team_id','capacity','contract_id'}:row[k]=text(row[k] or '')
    row['capacity']=int(row['capacity'] or 1)
    if not 1<=row['capacity']<=100:raise Problem('Teamcapaciteit moet tussen 1 en 100 liggen.')
    row['team_id']=int(row['team_id']) if row['team_id'] else None
    if row['team_id']:record(c,'teams',row['team_id'])
    obj=record(c,'objects',row['object_id'])
    row['contract_id']=int(row['contract_id']) if row['contract_id'] else None
    if row['contract_id']:
        contract=record(c,'contracts',row['contract_id'])
        if str(contract['customer_id'])!=str(obj['customer_id']) or contract['status']!='Actief':raise Problem('Contract moet actief zijn en bij de locatieklant horen.',409)
        if not contract['start_date']<=row['date'] or contract['end_date'] and row['date']>contract['end_date']:raise Problem('Opdrachtdatum valt buiten de contractduur.',409)
        if str(contract['object_id'])!=str(obj['id']) and not c.execute('SELECT 1 FROM contract_locations WHERE contract_id=? AND object_id=?',(contract['id'],obj['id'])).fetchone():raise Problem('Locatie is niet aan dit contract gekoppeld.',409)
    if row['employee_id']:record(c,'employees',row['employee_id'])
    if not row['description']:raise Problem('Omschrijving is verplicht.')
    date_value(row['date']);interval(row)
    if row['priority'] not in ('','Laag','Normaal','Hoog','Spoed'):raise Problem('Ongeldige prioriteit.')
    for aid in asset_ids(row):record(c,'assets',aid)
    row['hours']=str(money(row['hours'] or 0));row['status']=old.get('status') or 'Nieuw'
    row['workflow']=old.get('workflow') or 'Concept'
    if rid:update(c,'workorders',rid,row)
    else:rid=insert(c,'workorders',row)
    audit(c,user,'update' if old else 'create','workorders',rid)
    return record(c,'workorders',rid)
def transition(c,user,wid,body):
    work=visible(c,user,wid);version(work,body.get('version'));state=body.get('state');old=work.get('workflow') or 'Concept';reason=text(body.get('reason',''))
    if state not in TRANSITIONS.get(old,set()):raise Problem('Deze statusovergang is niet toegestaan.',409)
    if user['role']=='employee':
        if (old,state) not in {('Toegewezen','In uitvoering'),('Correctie','In uitvoering'),('In uitvoering','Voltooid')}:raise Problem('Alleen starten en gereedmelden van eigen werk toegestaan.',403)
    else:require(user,'workorders',True)
    if state in ('Goedgekeurd','Factureerbaar','Correctie') and user['role'] not in {'admin','company_admin','operations','supervisor'}:raise Problem('Alleen een leidinggevende kan deze beoordeling uitvoeren.',403)
    if state in ('Correctie','Geannuleerd') or old=='Geannuleerd':
        if not reason:raise Problem('Een reden is verplicht.')
    if c.execute('SELECT 1 FROM invoices WHERE workorder_id=?',(wid,)).fetchone():raise Problem('Gefactureerde opdracht is vergrendeld. Maak een creditcorrectie.',409)
    from . import scopes
    for related in c.execute('SELECT id FROM shifts WHERE workorder_id=?',(wid,)):scopes.require_record(c,user,'shifts',related['id'])
    shifts=[dict(x) for x in c.execute("SELECT * FROM shifts WHERE workorder_id=? AND status!='Geannuleerd'",(wid,))]
    if state in ('Toegewezen','In uitvoering'):
        if len({x['employee_id'] for x in shifts if x['employee_id']})<work['capacity']:raise Problem('Onvoldoende teamleden ingepland.',409)
        for shift in shifts:
            problems=issues(c,shift,shift['id'])
            if problems:raise Problem(' '.join(problems),409)
    if state in ('Voltooid','Goedgekeurd') and c.execute('SELECT 1 FROM checklist WHERE workorder_id=? AND done=0',(wid,)).fetchone():raise Problem('Rond eerst alle checklisttaken af.',409)
    if state=='Voltooid' and not text(body.get('completion_notes',work['completion_notes']) or ''):raise Problem('Vul de afrondingsnotitie in.')
    if state=='Factureerbaar':
        hrs=c.execute("SELECT * FROM hours WHERE workorder_id=? AND status!='Afgewezen'",(wid,)).fetchall()
        if not hrs or any(x['status'] not in ('Goedgekeurd','Akkoord') for x in hrs):raise Problem('Alle ingediende uren moeten eerst worden goedgekeurd.',409)
    values={'workflow':state,'status':{'Concept':'Nieuw','Gepland':'Nieuw','Toegewezen':'Nieuw','In uitvoering':'In behandeling','Correctie':'In behandeling','Geannuleerd':'Geannuleerd'}.get(state,'Afgerond')}
    if state=='Voltooid':values['completion_notes']=text(body.get('completion_notes',work['completion_notes']));values['signed_by']=text(body.get('signed_by',work['signed_by']) or '')
    if state=='Goedgekeurd':values['approved_by']=user['id']
    update(c,'workorders',wid,values)
    if state=='Voltooid':c.execute("UPDATE shifts SET status='Afgerond' WHERE workorder_id=? AND status!='Geannuleerd'",(wid,))
    if state=='Geannuleerd':
        c.execute("UPDATE shifts SET status='Geannuleerd' WHERE workorder_id=?",(wid,));c.execute('DELETE FROM reservations WHERE workorder_id=?',(wid,))
    eid=insert(c,'workorder_events',{'workorder_id':wid,'actor_id':user['id'],'old_state':old,'new_state':state,'reason':reason})
    audit(c,user,'transition','workorders',wid,old+' → '+state+' '+reason)
    notify(c,f'work:{eid}',f'Werkopdracht #{wid}: {state}','workorders',roles={'admin','company_admin','operations','supervisor'})
    for shift in shifts:notify(c,f'work:{eid}',f'Werkopdracht #{wid}: {state}','workorders',employee_id=shift['employee_id'])
    return record(c,'workorders',wid)
