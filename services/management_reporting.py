"""Managementoverzichten uit opgeslagen records; geen geschatte omzet/reistijden."""
from collections import defaultdict
from decimal import Decimal
from .access import permitted
from .common import eur,money
from domain import interval,date_value

def build(c,user,report):
    shifts=report['shifts'];hours=report['hours'];works=report['workorders'];work_ids={w['id'] for w in works};days=(date_value(report['to'])-date_value(report['from'])).days+1
    employees={};customers={};equipment={};contracts={}
    def emp(eid):
        if eid not in employees:
            row=c.execute('SELECT name,contract_hours FROM employees WHERE id=?',(eid,)).fetchone()
            employees[eid]={'employee_id':eid,'name':row['name'] if row else 'Niet toegewezen','planned_hours':0.0,'approved_hours':Decimal(0),'contract_capacity':float(row['contract_hours'] or 0)*days/7 if row else 0}
        return employees[eid]
    for shift in shifts:
        if shift['status']!='Geannuleerd':emp(shift['employee_id'])['planned_hours']+=interval(shift)-int(shift.get('break_minutes') or 0)/60
    for hour in hours:
        if hour['status'] in ('Goedgekeurd','Akkoord'):emp(hour['employee_id'])['approved_hours']+=money(hour['hours'])
    for work in works:
        cid=str(work['customer_id'])
        if cid not in customers:
            row=c.execute('SELECT name FROM customers WHERE id=?',(cid,)).fetchone();customers[cid]={'customer_id':cid,'name':row['name'],'workorders':0,'completed':0,'approved_hours':Decimal(0)}
        customers[cid]['workorders']+=1
        if work['workflow'] in ('Voltooid','Goedgekeurd','Factureerbaar') or work['status']=='Afgerond':customers[cid]['completed']+=1
        if work.get('contract_id'):
            contract=c.execute('SELECT name,monthly_value,status FROM contracts WHERE id=?',(work['contract_id'],)).fetchone()
            entry=contracts.setdefault(work['contract_id'],{'contract_id':work['contract_id'],'name':contract['name'],'status':contract['status'],'workorders':0,'approved_hours':Decimal(0)})
            entry['workorders']+=1
    contract_by_work={w['id']:w.get('contract_id') for w in works}
    for hour in hours:
        if hour['status'] in ('Goedgekeurd','Akkoord'):
            if str(hour['customer_id']) in customers:customers[str(hour['customer_id'])]['approved_hours']+=money(hour['hours'])
            cid=contract_by_work.get(hour['workorder_id'])
            if cid in contracts:contracts[cid]['approved_hours']+=money(hour['hours'])
    for row in c.execute('SELECT r.*,a.name FROM reservations r JOIN assets a ON a.id=r.asset_id WHERE r.date BETWEEN ? AND ?',(report['from'],report['to'])):
        if row['workorder_id'] not in work_ids:continue
        item=equipment.setdefault(row['asset_id'],{'asset_id':row['asset_id'],'name':row['name'],'reserved_hours':0.0,'reservations':0});item['reserved_hours']+=interval(dict(row));item['reservations']+=1
    for row in employees.values():row.update(approved_hours=str(row['approved_hours']),planned_hours=round(row['planned_hours'],2),contract_capacity=round(row['contract_capacity'],2));row['planned_capacity_percent']=round(row['planned_hours']/row['contract_capacity']*100,2) if row['contract_capacity'] else None
    for collection in (customers,contracts):
        for row in collection.values():row['approved_hours']=str(row['approved_hours'])
    for row in equipment.values():row['calendar_utilization_percent']=round(row['reserved_hours']/(24*days)*100,2);row['reserved_hours']=round(row['reserved_hours'],2)
    result={'employees':list(employees.values()),'customers':list(customers.values()),'contracts':list(contracts.values()),'equipment':list(equipment.values()),'definitions':{'employees':'Geplande uren na pauze / contracturen per week × kalenderdagen/7. Indicatief; geen verzuim- of cao-capaciteit.','equipment':'Gereserveerde uren / 24 uur per kalenderdag; geen gemeten draaiuren.','contracts':'Opdrachten en goedgekeurde uren met expliciete contractkoppeling.','finance':'Concept- en creditbedragen van de geselecteerde opdrachten; geen geboekte omzet of bankontvangsten.'}}
    if permitted(user,'invoices'):
        invoices=[dict(r) for r in c.execute('SELECT i.* FROM invoices i JOIN workorders w ON w.id=i.workorder_id WHERE w.date BETWEEN ? AND ?',(report['from'],report['to'])) if r['workorder_id'] in work_ids]
        result['finance']={'invoices':invoices,'net':eur(sum((money(x['net_amount'] or '0',True) for x in invoices),Decimal(0))),'vat':eur(sum((money(x['vat_amount'] or '0',True) for x in invoices),Decimal(0))),'total':eur(sum((money(x['amount'],True) for x in invoices),Decimal(0)))}
    return result
