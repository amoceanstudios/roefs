"""Decimale factuurvoorbereiding. Geen verzending, betaling of externe boeking."""
from decimal import Decimal
import datetime as dt
from domain import Problem
from .common import *
from .access import require

def prepare(c,user,body):
    require(user,'invoices',True)
    work=record(c,'workorders',body['workorder_id']);version(work,body.get('version'))
    if work['workflow']!='Factureerbaar':raise Problem('Werkopdracht is nog niet factureerbaar.',409)
    if c.execute('SELECT 1 FROM invoices WHERE workorder_id=? AND credit_of IS NULL',(work['id'],)).fetchone():raise Problem('Deze opdracht is al voorbereid voor facturatie.',409)
    hours=c.execute("SELECT * FROM hours WHERE workorder_id=? AND status IN ('Goedgekeurd','Akkoord')",(work['id'],)).fetchall()
    from . import scopes
    for hour in hours:scopes.require_record(c,user,'hours',hour['id'])
    if not hours:raise Problem('Geen goedgekeurde uren gevonden.',409)
    quantity=sum((money(x['hours']) for x in hours),Decimal(0));rate=money(body.get('hourly_rate','0'))
    if rate<=0:raise Problem('Een positief uurtarief is verplicht.')
    lines=[{'description':'Goedgekeurde uren werkopdracht #'+str(work['id']),'quantity':str(quantity),'rate':str(rate),'vat_rate':body.get('vat_rate','21')}]
    extras=body.get('lines',[])
    if not isinstance(extras,list) or len(extras)>100:raise Problem('Maximaal 100 extra factuurregels.')
    lines+=extras;computed=[]
    for line in lines:
        q=money(line['quantity']);r=money(line['rate']);v=money(line['vat_rate'])
        if v not in (Decimal(0),Decimal(9),Decimal(21)) or q<=0:raise Problem('Controleer aantal en btw-percentage (0, 9 of 21).')
        net=Decimal(eur(q*r));vat=Decimal(eur(net*v/100))
        computed.append({'description':text(line['description'],500,True),'quantity':str(q),'rate':str(r),'vat_rate':str(v),'net':str(net),'vat':str(vat)})
    net=sum((Decimal(x['net']) for x in computed),Decimal(0));vat=sum((Decimal(x['vat']) for x in computed),Decimal(0))
    obj=record(c,'objects',work['object_id']);number=draft_number(c,work['id'])
    rid=insert(c,'invoices',{'number':number,'customer_id':obj['customer_id'],'contract_id':str(work.get('contract_id') or ''),'amount':eur(net+vat),'due_date':str(dt.date.today()+dt.timedelta(days=30)),'status':'Concept','net_amount':eur(net),'vat_amount':eur(vat),'workorder_id':work['id'],'review_status':'Te beoordelen'})
    for line in computed:insert(c,'invoice_lines',{'invoice_id':rid,**line})
    audit(c,user,'prepare','invoices',rid);return record(c,'invoices',rid)
def review(c,user,rid,body):
    require(user,'invoices',True);row=record(c,'invoices',rid);version(row,body.get('version'))
    if row['review_status']!='Te beoordelen':raise Problem('Factuur is al beoordeeld.',409)
    if body.get('status') not in ('Goedgekeurd','Afgewezen'):raise Problem('Ongeldige beoordeling.')
    if body['status']=='Afgewezen' and not text(body.get('reason','')):raise Problem('Reden van afwijzing is verplicht.')
    update(c,'invoices',rid,{'review_status':body['status']});audit(c,user,'review','invoices',rid,text(body.get('reason','')));return record(c,'invoices',rid)
def credit(c,user,rid,body):
    require(user,'invoices',True);row=record(c,'invoices',rid);version(row,body.get('version'))
    reason=text(body.get('reason',''),500,True)
    if not row['workorder_id'] or row['credit_of'] or c.execute('SELECT 1 FROM invoices WHERE credit_of=?',(rid,)).fetchone():raise Problem('Deze factuur kan niet opnieuw gecrediteerd worden.',409)
    new=insert(c,'invoices',{'number':'CREDIT-'+row['number'],'customer_id':row['customer_id'],'contract_id':row['contract_id'],'amount':eur(-money(row['amount'])),'net_amount':eur(-money(row['net_amount'])),'vat_amount':eur(-money(row['vat_amount'])),'due_date':str(dt.date.today()),'status':'Concept','review_status':'Te beoordelen','credit_of':rid,'workorder_id':row['workorder_id']})
    for raw in c.execute('SELECT * FROM invoice_lines WHERE invoice_id=?',(rid,)).fetchall():
        line=dict(raw);line.pop('id');line.update(invoice_id=new,quantity=str(-money(line['quantity'])),net=eur(-money(line['net'])),vat=eur(-money(line['vat'])));insert(c,'invoice_lines',line)
    audit(c,user,'credit','invoices',new,reason);return record(c,'invoices',new)


def validate_numbering(value):
    import re
    if not isinstance(value,dict) or set(value)!={'enabled','prefix','width'} or not isinstance(value['enabled'],bool):raise Problem('Vul het conceptnummerprofiel volledig in.')
    if not isinstance(value['prefix'],str) or not re.fullmatch('[A-Z0-9-]{1,20}',value['prefix']):raise Problem('Nummerprefix: 1–20 hoofdletters, cijfers of streepjes.')
    if type(value['width'])!=int or not 3<=value['width']<=10:raise Problem('Nummerlengte: 3–10 cijfers.')
    return value

def draft_number(c,work_id):
    setting=c.execute("SELECT value FROM settings WHERE key='invoice_numbering'").fetchone()
    profile=json.loads(setting[0]) if setting else {'enabled':False}
    if not profile['enabled']:return 'CONCEPT-WB-'+str(work_id)
    series='CONCEPT-'+profile['prefix']+'-'+str(dt.date.today().year)
    c.execute('INSERT OR IGNORE INTO invoice_sequences VALUES(?,1)',(series,))
    number=c.execute('SELECT next_number FROM invoice_sequences WHERE series=?',(series,)).fetchone()[0]
    for _ in range(1000):
        value=series+'-'+str(number).zfill(profile['width']);number+=1
        if not c.execute('SELECT 1 FROM invoices WHERE number=?',(value,)).fetchone():
            c.execute('UPDATE invoice_sequences SET next_number=? WHERE series=?',(number,series));return value
    raise Problem('Conceptnummerreeks bevat te veel bestaande nummers; controleer de configuratie.',409)
