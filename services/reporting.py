"""Gefilterde gegevens, veilige CSV en echte PDF met pagina's en tekst."""
import csv,io,datetime as dt,threading
REPORT_LOCK=threading.Lock()
from decimal import Decimal
from domain import date_value,Problem,interval
from .common import *
from .access import require

def csv_bytes(rows,fields,labels=None):
    stream=io.StringIO(newline='');writer=csv.writer(stream,delimiter=';')
    def cell(v):
        v=str(v if v is not None else '')
        return "'"+v if v.lstrip().startswith(('=','+','-','@')) or v.startswith(('\t','\r','\n')) else v
    writer.writerow([labels.get(f,f) for f in fields] if labels else fields)
    for row in rows:writer.writerow([cell(row.get(f,'')) for f in fields])
    return ('\ufeff'+stream.getvalue()).encode('utf-8')
def pdf(title,lines):
    """A4 PDF 1.4, Helvetica/WinAnsi. Geen actieve inhoud of externe verwijzingen."""
    import textwrap
    lines=[title,'AMOCEAN INTEL — fictieve demonstratiegegevens','']+[str(x) for x in lines]
    wrapped=[part for line in lines for part in (textwrap.wrap(line,95) or [''])]
    pages=[wrapped[i:i+48] for i in range(0,len(wrapped),48)]
    objs=[b'',b'',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>']
    pageids=[]
    for chunk in pages:
        pid=len(objs)+1;sid=pid+1;pageids.append(pid)
        objs.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {sid} 0 R >>'.encode())
        def escape(s):return s.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')
        content=('BT /F1 10 Tf 40 800 Td 15 TL '+''.join('('+escape(x)+') Tj T*\n' for x in chunk)+'ET').encode('cp1252','replace')
        objs.append(b'<< /Length '+str(len(content)).encode()+b' >>\nstream\n'+content+b'\nendstream')
    objs[0]=b'<< /Type /Catalog /Pages 2 0 R >>';objs[1]=('<< /Type /Pages /Count '+str(len(pages))+' /Kids ['+' '.join(f'{i} 0 R' for i in pageids)+'] >>').encode()
    output=bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n');offsets=[0]
    for i,obj in enumerate(objs,1):offsets.append(len(output));output.extend(f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n')
    pos=len(output);output.extend(f'xref\n0 {len(objs)+1}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]:output.extend(f'{offset:010d} 00000 n \n'.encode())
    output.extend(f'trailer << /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{pos}\n%%EOF'.encode());return bytes(output)

def report(c,user,query):
    # Eén zware rapportquery tegelijk voorkomt GIL/SQLite-row-conversiecontention.
    with REPORT_LOCK:return _report(c,user,query)

def _report(c,user,query):
    require(user,'reports')
    start=query.get('from','2000-01-01');end=query.get('to','2100-12-31');date_value(start);date_value(end)
    if end<start:raise Problem('Einddatum ligt voor begindatum.')
    department=query.get('department','');customer=query.get('customer_id','')
    conditions=['s.date BETWEEN ? AND ?'];args=[start,end]
    if department:conditions.append('e.department=?');args.append(department)
    if customer:conditions.append('o.customer_id=?');args.append(customer)
    shifts=[dict(x) for x in c.execute('SELECT s.*,e.name employee_name,e.department,o.customer_id,o.name object_name FROM shifts s LEFT JOIN employees e ON e.id=s.employee_id JOIN objects o ON o.id=s.object_id WHERE '+' AND '.join(conditions),args)]
    works=[dict(x) for x in c.execute('SELECT w.*,o.customer_id FROM workorders w JOIN objects o ON o.id=w.object_id WHERE w.date BETWEEN ? AND ?'+(' AND o.customer_id=?' if customer else ''),[start,end]+([customer] if customer else []))]
    if department:works=[w for w in works if any(s['workorder_id']==w['id'] for s in shifts)]
    hours=[dict(x) for x in c.execute('SELECT h.*,e.name employee_name,e.department,o.customer_id FROM hours h JOIN employees e ON e.id=h.employee_id LEFT JOIN workorders w ON w.id=h.workorder_id LEFT JOIN shifts s ON s.id=h.shift_id LEFT JOIN objects o ON o.id=COALESCE(w.object_id,s.object_id) WHERE h.date BETWEEN ? AND ?'+(' AND o.customer_id=?' if customer else '')+(' AND e.department=?' if department else ''),[start,end]+([customer] if customer else [])+([department] if department else []))]
    from . import scopes
    shifts=scopes.filter_rows(c,user,'shifts',shifts);works=scopes.filter_rows(c,user,'workorders',works);hours=scopes.filter_rows(c,user,'hours',hours)
    approved=sum((Decimal(x['hours']) for x in hours if x['status'] in ('Akkoord','Goedgekeurd')),Decimal(0))
    planned=sum(interval(s) for s in shifts if s['status']!='Geannuleerd')
    from .planning import assess_many
    conflicts=assess_many(c,shifts)
    statuses={}
    for work in works:statuses[work['workflow'] or work['status']]=statuses.get(work['workflow'] or work['status'],0)+1
    return {'from':start,'to':end,'planned_hours':round(planned,2),'approved_hours':str(approved),'utilization_percent':round(float(approved)/planned*100,2) if planned else None,'definition':'Benutting = goedgekeurde geregistreerde uren / geplande niet-geannuleerde diensturen × 100. Geen contractcapaciteitsmeting.','workorder_status':statuses,'shifts':shifts,'hours':hours,'workorders':works,'conflicts':[x for x in conflicts if x['reasons']]}
