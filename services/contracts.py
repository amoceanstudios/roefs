"""Contractlocaties en expliciete, geversioneerde verlengbesluiten."""
from domain import Problem,date_value
from .common import record,version,text,insert,update,audit,notify
from .access import require

def detail(c,user,cid):
    require(user,'contracts');row=record(c,'contracts',cid)
    return {'contract':row,'locations':[dict(x) for x in c.execute('SELECT l.*,o.name FROM contract_locations l JOIN objects o ON o.id=l.object_id WHERE contract_id=? ORDER BY o.name',(cid,))],'events':[dict(x) for x in c.execute('SELECT * FROM contract_events WHERE contract_id=? ORDER BY id DESC LIMIT 100',(cid,))],'workorders':[dict(x) for x in c.execute('SELECT id,description,date,workflow,status FROM workorders WHERE contract_id=? ORDER BY date DESC LIMIT 100',(cid,))]}

def locations(c,user,cid,body):
    require(user,'contracts',True);row=record(c,'contracts',cid);version(row,body.get('version'));items=body.get('locations')
    if not isinstance(items,list) or not 1<=len(items)<=100:raise Problem('Koppel 1 tot 100 locaties.')
    ids=set()
    for item in items:
        obj=record(c,'objects',int(item['object_id']))
        if str(obj['customer_id'])!=str(row['customer_id']):raise Problem('Alle locaties moeten bij de contractklant horen.',409)
        if obj['id'] in ids:raise Problem('Locatie is dubbel opgenomen.',409)
        ids.add(obj['id']);text(item.get('frequency',''),100,True)
    assigned={int(x[0]) for x in c.execute('SELECT DISTINCT object_id FROM workorders WHERE contract_id=?',(cid,))}
    if assigned-ids:raise Problem('Locatie heeft gekoppelde opdrachten en kan niet uit het contract worden verwijderd.',409)
    c.execute('DELETE FROM contract_locations WHERE contract_id=?',(cid,))
    for item in items:insert(c,'contract_locations',{'contract_id':cid,'object_id':int(item['object_id']),'frequency':text(item['frequency'],100,True)})
    update(c,'contracts',cid,{'version':row['version']+1});audit(c,user,'locations','contracts',cid);return detail(c,user,cid)

def decide(c,user,cid,body):
    require(user,'contracts',True);row=record(c,'contracts',cid);version(row,body.get('version'));reason=text(body.get('reason',''),1000,True);action=body.get('action')
    if action=='renew':
        if row['status']!='Actief':raise Problem('Alleen een actief contract kan worden verlengd.',409)
        end=date_value(body.get('end_date',''));old=date_value(row['end_date']) if row['end_date'] else date_value(row['start_date'])
        if end<=old:raise Problem('Nieuwe einddatum moet na de bestaande einddatum liggen.')
        renewal=body.get('renewal_date','')
        if renewal and not date_value(row['start_date'])<=date_value(renewal)<=end:raise Problem('Verlengherinnering moet binnen de contractduur vallen.')
        patch={'end_date':str(end),'renewal_date':renewal}
    elif action=='activate' and row['status']=='Concept':patch={'status':'Actief'}
    elif action=='terminate' and row['status']=='Actief':patch={'status':'Beëindigd'}
    elif action=='cancel' and row['status']=='Concept':patch={'status':'Geannuleerd'}
    else:raise Problem('Deze contractovergang is niet toegestaan.',409)
    update(c,'contracts',cid,patch);eid=insert(c,'contract_events',{'contract_id':cid,'actor_id':user['id'],'action':action,'reason':reason,'old_end':row['end_date'],'new_end':patch.get('end_date',row['end_date'])});audit(c,user,action,'contracts',cid,reason)
    notify(c,f'contract-decision:{eid}','Contractbesluit opgeslagen.','contracts',roles={'admin','company_admin','operations','finance'})
    return detail(c,user,cid)
