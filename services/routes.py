"""Versie 5 HTTP-adapter; transacties omsluiten volledige bedrijfsoperaties."""
import json,urllib.parse,datetime as dt
from pathlib import Path
from domain import Problem,validate,protect_delete,date_value,STATUSES,REQUIRED
from . import planning,workorders,timekeeping,finance,documents,reporting
from .common import *
from .access import *
from .migrations import EXTRA

RESOURCES={
 'communications':('Contacthistorie','customers',['customer_id','date','subject','notes']),
 'articles':('Artikelen en materialen','orders',['code','name','unit','rate','vat_rate','status']),
 'teams':('Teams','employees',['name','department']),
 'contacts':('Contactpersonen','customers',['customer_id','name','email','phone','notes']),
 'certifications':('Certificeringen','employees',['employee_id','name','expires_on']),
 'travel_estimates':('Reistijden','shifts',['from_object','to_object','minutes','source']),
}

def send_binary(h,data,mime,name):
    h.send_response(200);h.send_header('Content-Type',mime);h.send_header('Content-Length',str(len(data)));h.send_header('Cache-Control','no-store');h.send_header('Content-Disposition',"attachment; filename*=UTF-8''"+urllib.parse.quote(name));h.end_headers();h.wfile.write(data)

def extra_validate(c,module,values):
    for field in values:
        value=values[field]
        if field in ('manager_id','team_id'):
            values[field]=int(value) if value else None
            if value:record(c,'employees' if field=='manager_id' else 'teams',values[field])
        elif field=='emergency_available':
            if str(value) not in ('0','1'):raise Problem('Kies 0 of 1 voor noodbeschikbaarheid.')
            values[field]=int(value)
        else:values[field]=text(value or '')
        if values[field] and field.endswith('_date'):date_value(values[field])
    return values

def entity_save(c,user,module,body,modules,rid=None):
    require(user,module,True)
    if module in ('workorders','shifts','hours','invoices'):raise Problem('Gebruik de gekoppelde proceshandeling voor dit onderdeel.')
    old=record(c,module,rid) if rid else {}
    if old:version(old,body.get('version'))
    fields=modules[module][1];extra=EXTRA.get(module,{})
    if set(body)-set(fields)-set(extra)-{'version'}:raise Problem('Onbekend veld.')
    row=validate(c,module,{k:v for k,v in body.items() if k in fields} or {fields[0]:old.get(fields[0],'')},fields,old)
    row.update(extra_validate(c,module,{k:body[k] for k in extra if k in body}))
    if module=='customers':
        duplicate=c.execute('SELECT id FROM customers WHERE lower(trim(name))=lower(trim(?)) AND id!=?',(row['name'],rid or 0)).fetchone()
        if duplicate:raise Problem('Mogelijke dubbele klant: #'+str(duplicate[0])+'. Controleer de bestaande klant.',409)
        if not row.get('customer_number',old.get('customer_number')):row['customer_number']='KL-'+str(c.execute('SELECT COALESCE(MAX(id),0)+1 FROM customers').fetchone()[0]).zfill(6)
    if rid:update(c,module,rid,row)
    else:rid=insert(c,module,row)
    audit(c,user,'update' if old else 'create',module,rid)
    if module in ('leave','availability'):
        notify(c,f'{module}:{rid}:{record(c,module,rid)["version"]}','Beschikbaarheid gewijzigd; controleer de planning.','shifts',roles={'admin','company_admin','operations','planner'})
    return record(c,module,rid)

def resource_save(c,user,table,body,rid=None):
    require(user,RESOURCES[table][1],True);fields=RESOURCES[table][2];old=record(c,table,rid) if rid else {}
    if old:version(old,body.get('version'))
    if set(body)-set(fields)-{'version'}:raise Problem('Onbekend veld.')
    row={f:text(body.get(f,old.get(f,''))) for f in fields}
    if 'name' in fields and not row['name']:raise Problem('Naam is verplicht.')
    for field,target in [('customer_id','customers'),('employee_id','employees'),('from_object','objects'),('to_object','objects')]:
        if field in row:row[field]=int(row[field]);record(c,target,row[field])
    if table=='communications':
        date_value(row['date']);text(row['subject'],200,True)
    if table=='articles':
        row['rate']=str(money(row['rate'] or '0'));row['vat_rate']=str(money(row['vat_rate'] or '21'));row['status']=row['status'] or 'Actief'
        if not row['code'] or row['vat_rate'] not in ('0','9','21') or row['status'] not in ('Actief','Inactief'):raise Problem('Controleer artikelcode, btw en status.')
    if table=='certifications':date_value(row['expires_on']);row['name']=row['name'].casefold()
    if table=='travel_estimates':
        row['minutes']=int(row['minutes'])
        if not 0<=row['minutes']<=1440 or not row['source']:raise Problem('Vul een betrouwbare bron en reistijd van 0–1440 minuten in.')
    if row.get('email'):
        import re
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',row['email']):raise Problem('Ongeldig e-mailadres.')
    if rid:row['version']=old['version']+1;update(c,table,rid,row)
    else:rid=insert(c,table,row)
    audit(c,user,'update' if old else 'create',table,rid);return record(c,table,rid)

def visible_work(c,user):
    if permitted(user,'workorders'):return [dict(x) for x in c.execute('SELECT * FROM workorders ORDER BY id DESC')]
    if user['role']=='employee' and user.get('employee_id'):
        return [dict(x) for x in c.execute("SELECT DISTINCT w.* FROM workorders w LEFT JOIN shifts s ON s.workorder_id=w.id AND s.status!='Geannuleerd' WHERE w.employee_id=? OR s.employee_id=? ORDER BY w.id DESC",(str(user['employee_id']),str(user['employee_id'])))]
    raise Problem('Geen toegang tot opdrachten.',403)

def dispatch(h,c,user,path,method,modules,db):
    parts=path.strip('/').split('/');query={k:v[0] for k,v in urllib.parse.parse_qs(urllib.parse.urlsplit(h.path).query).items()}
    body=h.body() if method in ('POST','PUT','DELETE') else {}
    if method!='GET':c.execute('BEGIN IMMEDIATE')
    result=None;status=200
    if path=='home' and method=='GET':
        from .dashboard import home
        result=home(c,user)
    elif path=='security/audit-integrity' and method=='GET':
        require(user,'settings')
        from .audit_integrity import verify
        result=verify(c)
    elif path.startswith('security/mfa/'):
        from .mfa import route
        action=parts[-1]
        if (action=='status')!=(method=='GET'):raise Problem('Ongeldige methode.',405)
        result=route(c,user,action,body)
    elif path.startswith('sync'):
        from .synchronization import route
        result=route(h,c,user,path,method,body,modules,db)
    elif path=='metadata' and method=='GET':
        result={'roles':ROLES,'modules':{m:{'label':v[0],'fields':v[1]+list(EXTRA.get(m,{})),'statuses':STATUSES[m],'required':REQUIRED[m],'write':permitted(user,m,True)} for m,v in modules.items() if permitted(user,m)},'resources':{k:{'label':v[0],'fields':v[2],'write':permitted(user,v[1],True)} for k,v in RESOURCES.items() if permitted(user,v[1])},'states':workorders.STATES,'permissions':{m:{'read':permitted(user,m),'write':permitted(user,m,True)} for m in set(modules)|{'reports','settings'}}}
    elif parts[0]=='entities' and len(parts) in (2,3) and parts[1] in modules:
        module=parts[1];rid=int(parts[2]) if len(parts)==3 else None;require(user,module,method!='GET')
        if method=='GET':
            if rid:result=record(c,module,rid)
            else:
                fields=modules[module][1]+list(EXTRA.get(module,{}));sort=query.get('sort','id')
                if sort not in fields+['id','version']:raise Problem('Ongeldig sorteerveld.')
                direction='DESC' if query.get('direction')=='desc' else 'ASC';limit=min(100,max(1,int(query.get('limit',25))));offset=max(0,int(query.get('offset',0)));args=[];where=[]
                if 'ids' in query:
                    ids=query['ids'].split(',')
                    if len(ids)>1000 or any(not value.isdigit() for value in ids):raise Problem('Ongeldige recordselectie.')
                    where.append('id IN ('+','.join('?' for _ in ids)+')');args.extend(ids)
                if query.get('q'):
                    where.append('('+' OR '.join('CAST('+f+' AS TEXT) LIKE ? ESCAPE \'\\\'' for f in fields)+')');pattern='%'+query['q'].replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%';args.extend([pattern]*len(fields))
                for f in ('status','customer_id','employee_id','object_id','department','service','team_id','workflow'):
                    if query.get(f) and f in fields:where.append(f+'=?');args.append(query[f])
                clause=' WHERE '+' AND '.join(where) if where else ''
                count=c.execute('SELECT COUNT(*) FROM '+module+clause,args).fetchone()[0]
                result={'items':[dict(x) for x in c.execute('SELECT * FROM '+module+clause+' ORDER BY '+sort+' '+direction+' LIMIT ? OFFSET ?',args+[limit,offset])],'total':count,'limit':limit,'offset':offset}
        elif method in ('POST','PUT') and (rid is None)==(method=='POST'):result=entity_save(c,user,module,body,modules,rid);status=201 if not rid else 200
        elif method=='DELETE' and rid:
            old=record(c,module,rid);version(old,body.get('version'))
            if old.get('workflow') or old.get('workorder_id'):raise Problem('Gekoppelde procesgegevens kunnen niet worden verwijderd.',409)
            protect_delete(c,module,rid,modules);c.execute('DELETE FROM '+module+' WHERE id=?',(rid,));audit(c,user,'delete',module,rid);result={'ok':True}
        else:raise Problem('Ongeldige methode.',405)
    elif parts[0]=='resources' and len(parts) in (2,3) and parts[1] in RESOURCES:
        table=parts[1];rid=int(parts[2]) if len(parts)==3 else None;require(user,RESOURCES[table][1],method!='GET')
        if method=='GET':result=record(c,table,rid) if rid else [dict(x) for x in c.execute('SELECT * FROM '+table+' ORDER BY id DESC')]
        elif method in ('POST','PUT') and (rid is None)==(method=='POST'):result=resource_save(c,user,table,body,rid)
        elif method=='DELETE' and rid:
            old=record(c,table,rid);version(old,body.get('version'))
            if table=='teams' and (c.execute('SELECT 1 FROM employees WHERE team_id=?',(rid,)).fetchone() or c.execute('SELECT 1 FROM workorders WHERE team_id=?',(rid,)).fetchone()):raise Problem('Team is nog gekoppeld.',409)
            if table=='articles' and c.execute("SELECT 1 FROM sync_links WHERE category='articles' AND local_id=?",(rid,)).fetchone():raise Problem('Artikel is extern gekoppeld. Kies Inactief.',409)
            c.execute('DELETE FROM '+table+' WHERE id=?',(rid,));audit(c,user,'delete',table,rid);result={'ok':True}
        else:raise Problem('Ongeldige methode.',405)
    elif parts[0]=='customers' and len(parts)==3 and parts[2]=='timeline' and method=='GET':
        require(user,'customers');rid=int(parts[1]);result={'customer':record(c,'customers',rid),'locations':[dict(x) for x in c.execute('SELECT * FROM objects WHERE customer_id=?',(str(rid),))],'contacts':[dict(x) for x in c.execute('SELECT * FROM contacts WHERE customer_id=?',(rid,))],'contracts':[dict(x) for x in c.execute('SELECT * FROM contracts WHERE customer_id=?',(str(rid),))],'workorders':[dict(x) for x in c.execute('SELECT w.* FROM workorders w JOIN objects o ON o.id=w.object_id WHERE o.customer_id=?',(str(rid),))],'communications':[dict(x) for x in c.execute('SELECT * FROM communications WHERE customer_id=? ORDER BY date DESC,id DESC',(rid,))],'audit':[dict(x) for x in c.execute("SELECT * FROM audit WHERE module='customers' AND record_id=? ORDER BY id DESC",(rid,))]}
    elif parts[0]=='contracts' and len(parts) in (2,3):
        from . import contracts
        cid=int(parts[1])
        if len(parts)==2 and method=='GET':result=contracts.detail(c,user,cid)
        elif len(parts)==3 and parts[2]=='locations' and method=='PUT':result=contracts.locations(c,user,cid,body)
        elif len(parts)==3 and parts[2]=='decision' and method=='POST':result=contracts.decide(c,user,cid,body)
        else:raise Problem('Ongeldige contracthandeling.',405)
    elif path=='customers/import' and method=='POST':
        rows=body.get('rows')
        if not isinstance(rows,list) or not 1<=len(rows)<=200:raise Problem('Importeer 1 tot 200 klanten per batch.')
        result={'items':[entity_save(c,user,'customers',row,modules) for row in rows]}
    elif parts[:2]==['planning','series']:
        from . import planning_series
        if len(parts)==2 and method=='GET':result=planning_series.listing(c,user)
        elif len(parts)==2 and method=='POST':result=planning_series.create(c,user,body)
        elif len(parts)==3 and method=='POST':result=planning_series.change(c,user,int(parts[2]),body)
        else:raise Problem('Ongeldige reeksactie.',405)
    elif path=='planning/suggest' and method=='POST':result=planning.suggestions(c,user,body)
    elif path=='planning/calendar' and method=='GET':
        if user['role']!='employee':require(user,'shifts')
        start=query.get('from',str(dt.date.today()));end=query.get('to',start);a=date_value(start);z=date_value(end)
        if not 0<=(z-a).days<=62:raise Problem('Kies maximaal 63 kalenderdagen.')
        source=[dict(x) for x in c.execute('SELECT s.*,e.name employee_name,e.department,e.team_id,o.name object_name,o.customer_id FROM shifts s LEFT JOIN employees e ON e.id=s.employee_id JOIN objects o ON o.id=s.object_id WHERE s.date BETWEEN ? AND ? ORDER BY s.date,s.start_time',(start,end))]
        if user['role']=='employee':source=[x for x in source if x['employee_id']==str(user.get('employee_id') or -1)]
        for f in ('employee_id','team_id','customer_id','object_id','department'):
            if query.get(f):source=[x for x in source if str(x.get(f) or '')==query[f]]
        if query.get('asset_id'):
            ids={x[0] for x in c.execute('SELECT workorder_id FROM reservations WHERE asset_id=?',(query['asset_id'],))};source=[x for x in source if x['workorder_id'] in ids]
        result={'shifts':source,'unassigned':[] if user['role']=='employee' else [dict(x) for x in c.execute("SELECT * FROM workorders WHERE workflow IN ('Concept','Gepland') ORDER BY date,id")],'history':[] if user['role']=='employee' else [dict(x) for x in c.execute('SELECT * FROM schedule_history ORDER BY id DESC LIMIT 100')],'reservations':[] if user['role']=='employee' else [dict(x) for x in c.execute('SELECT * FROM reservations WHERE date BETWEEN ? AND ?',(start,end))]}
    elif parts[0]=='shifts' and len(parts)<=2 and method in ('POST','PUT'):result=planning.save(c,user,body,int(parts[1]) if len(parts)==2 else None)
    elif path=='planning/bulk' and method=='POST':
        rows=body.get('shifts')
        if not isinstance(rows,list) or not 1<=len(rows)<=100:raise Problem('Een batch bevat 1 tot 100 diensten.')
        result={'items':[planning.save(c,user,{k:v for k,v in row.items() if k!='id'},row.get('id')) for row in rows]}
    elif len(parts)==3 and parts[:2]==['planning','resize'] and method=='POST':result=planning.resize(c,user,int(parts[2]),body)
    elif path=='planning/undo' and method=='POST':result=planning.undo(c,user,body)
    elif parts[0]=='workorders' and len(parts)<=3:
        rid=int(parts[1]) if len(parts)>=2 else None
        if method=='GET' and len(parts)<=2:
            if not rid:result=visible_work(c,user)
            else:
                work=workorders.visible(c,user,rid);result={'workorder':work,'checklist':[dict(x) for x in c.execute('SELECT * FROM checklist WHERE workorder_id=?',(rid,))],'events':[dict(x) for x in c.execute('SELECT * FROM workorder_events WHERE workorder_id=? ORDER BY id',(rid,))],'shifts':[dict(x) for x in c.execute('SELECT id,employee_id,date,start_time,end_time,status,version FROM shifts WHERE workorder_id=?',(rid,))]}
        elif len(parts)<=2 and method in ('POST','PUT'):result=workorders.save(c,user,body,rid)
        elif len(parts)==3 and parts[2]=='transition' and method=='POST':result=workorders.transition(c,user,rid,body)
        elif len(parts)==3 and parts[2]=='checklist' and method=='POST':
            work=workorders.visible(c,user,rid)
            if user['role']!='employee':require(user,'workorders',True)
            if work['workflow'] in ('Voltooid','Goedgekeurd','Factureerbaar','Geannuleerd'):raise Problem('Checklist is vergrendeld.',409)
            if body.get('id'):
                task=record(c,'checklist',int(body['id']));version(task,body.get('version'))
                if task['workorder_id']!=rid:raise Problem('Checklisttaak niet gevonden.',404)
                if not isinstance(body.get('done'),bool):raise Problem('Kies voltooid of niet voltooid.')
                update(c,'checklist',task['id'],{'done':int(body['done']),'done_by':user['id'],'done_at':dt.datetime.now(dt.timezone.utc).isoformat(),'version':task['version']+1});result=record(c,'checklist',task['id'])
            else:
                require(user,'workorders',True);tid=insert(c,'checklist',{'workorder_id':rid,'title':text(body.get('title',''),300,True)});result=record(c,'checklist',tid)
            audit(c,user,'checklist','workorders',rid)
        elif len(parts)==3 and parts[2]=='pdf' and method=='GET':
            w=workorders.visible(c,user,rid);lines=[f"Werkopdracht #{rid}",w['description'],'Status: '+str(w['workflow'] or w['status']),'Datum: '+w['date'],'Afronding: '+str(w['completion_notes'] or ''),'Aftekennaam (geen gekwalificeerde handtekening): '+w['signed_by']]+[('Gereed: ' if t['done'] else 'Open: ')+t['title'] for t in c.execute('SELECT * FROM checklist WHERE workorder_id=?',(rid,))];return send_binary(h,reporting.pdf('Werkbon',lines),'application/pdf',f'werkbon-{rid}.pdf')
        else:raise Problem('Ongeldige werkopdrachthandeling.',405)
    elif parts[0]=='clock':
        from . import time_clock
        if len(parts)==1 and method=='GET':result=time_clock.listing(c,user)
        elif len(parts)==1 and method=='POST':result=time_clock.start(c,user,body)
        elif len(parts)==2 and method=='POST':result=time_clock.finish(c,user,int(parts[1]),body)
        else:raise Problem('Ongeldige klokhandeling.',405)
    elif parts[0]=='hours' and len(parts)<=3:
        rid=int(parts[1]) if len(parts)>1 else None
        if method=='GET':
            if user['role']=='employee':result=[dict(x) for x in c.execute('SELECT * FROM hours WHERE employee_id=? ORDER BY id DESC',(str(user['employee_id']),))]
            else:require(user,'hours');result=[dict(x) for x in c.execute('SELECT * FROM hours ORDER BY id DESC')]
        elif method in ('POST','PUT') and len(parts)<=2:result=timekeeping.save(c,user,body,rid)
        elif method=='POST' and len(parts)==3 and parts[2]=='review':result=timekeeping.review(c,user,rid,body)
        else:raise Problem('Ongeldige urenhandeling.',405)
    elif path=='invoices/prepare' and method=='POST':result=finance.prepare(c,user,body)
    elif parts[0]=='invoices' and len(parts)==3:
        require(user,'invoices',method!='GET');rid=int(parts[1])
        if parts[2]=='review' and method=='POST':result=finance.review(c,user,rid,body)
        elif parts[2]=='credit' and method=='POST':result=finance.credit(c,user,rid,body)
        elif parts[2] in ('pdf','csv','lines') and method=='GET':
            inv=record(c,'invoices',rid);lines=[dict(x) for x in c.execute('SELECT * FROM invoice_lines WHERE invoice_id=?',(rid,))]
            if parts[2]=='lines':result={'invoice':inv,'lines':lines}
            elif parts[2]=='csv':return send_binary(h,reporting.csv_bytes(lines,['description','quantity','rate','vat_rate','net','vat']),'text/csv; charset=utf-8',f'factuur-{rid}.csv')
            else:return send_binary(h,reporting.pdf('Conceptfactuur '+inv['number'],['Beoordeling: '+str(inv['review_status']),'Klant: '+record(c,'customers',inv['customer_id'])['name']]+[f"{x['description']} | {x['quantity']} × EUR {x['rate']} | netto EUR {x['net']} | btw EUR {x['vat']}" for x in lines]+['Totaal EUR '+inv['amount'],'Niet verzonden; controleer in uw boekhouding.']),'application/pdf',f'factuur-{rid}.pdf')
        else:raise Problem('Ongeldige factuurhandeling.',405)
    elif path=='files/config' and method=='GET':result={'max_bytes':documents.MAX_BYTES,'scanning':'ClamAV indien beschikbaar; anders quarantaine voor PDF en afbeeldingen.'}
    elif parts[0]=='files' and len(parts)==3 and parts[2]=='rescan' and method=='POST':result=documents.rescan(c,user,int(parts[1]),db)
    elif parts[0]=='files' and len(parts)==2 and method=='DELETE':result=documents.delete(c,user,int(parts[1]),body,db)
    elif path=='files' and method=='POST':result=documents.upload(c,user,body,db)
    elif path=='files' and method=='GET':
        result=[]
        for raw in c.execute('SELECT * FROM files WHERE deleted_at IS NULL ORDER BY id DESC'):
            row=dict(raw)
            try:documents.authorized(c,user,row)
            except Problem:continue
            row.pop('storage_key');result.append(row)
    elif parts[0]=='files' and len(parts)==2 and method=='GET':
        row,data=documents.download(c,user,int(parts[1]),db);return send_binary(h,data,row['mime'],row['name'])
    elif path in ('reports/management','reports/management/csv','reports/management/pdf') and method=='GET':
        from .management_reporting import build
        base=reporting.report(c,user,query);result=build(c,user,base)
        section=query.get('section','employees')
        if section not in ('employees','customers','contracts','equipment'):raise Problem('Onbekend rapportonderdeel.')
        rows=result[section]
        if path.endswith('/csv'):return send_binary(h,reporting.csv_bytes(rows,list(rows[0]) if rows else ['Geen gegevens']),'text/csv; charset=utf-8','management-'+section+'.csv')
        if path.endswith('/pdf'):return send_binary(h,reporting.pdf('Managementrapport '+{'employees':'Medewerkers','customers':'Klanten','contracts':'Contracten','equipment':'Materieel'}[section],[result['definitions'].get(section,'')]+[' | '.join(str(v) for v in row.values()) for row in rows]),'application/pdf','management-'+section+'.pdf')
    elif path=='reports' and method=='GET':result=reporting.report(c,user,query)
    elif path in ('reports/csv','reports/pdf') and method=='GET':
        r=reporting.report(c,user,query)
        if path.endswith('csv'):return send_binary(h,reporting.csv_bytes(r['hours'],['id','employee_name','date','hours','status','customer_id']),'text/csv; charset=utf-8','urenrapport.csv')
        return send_binary(h,reporting.pdf('Bedrijfsrapport',[r['from']+' tot '+r['to'],r['definition'],f"Gepland: {r['planned_hours']} uur; goedgekeurd: {r['approved_hours']} uur",json.dumps(r['workorder_status'],ensure_ascii=False)]+[f"{x['employee_name']} | {x['date']} | {x['hours']} uur | {x['status']}" for x in r['hours']]),'application/pdf','rapport.pdf')
    elif path=='notifications' and method=='GET':result=[dict(x) for x in c.execute('SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 200',(user['id'],))]
    elif path=='notifications/read' and method=='POST':
        row=record(c,'notifications',int(body['id']))
        if row['user_id']!=user['id']:raise Problem('Melding niet gevonden.',404)
        update(c,'notifications',row['id'],{'read_at':dt.datetime.now(dt.timezone.utc).isoformat()});result={'ok':True}
    elif path=='preferences' and method in ('GET','PUT'):
        if method=='PUT':
            if set(body)-{'tour_step','tour_completed','notifications'}:raise Problem('Onbekende voorkeur.')
            values={k:int(v) for k,v in body.items()}
            if any(v not in (0,1) for k,v in values.items() if k!='tour_step') or not 0<=values.get('tour_step',0)<=50:raise Problem('Ongeldige voorkeur.')
            c.execute('INSERT OR IGNORE INTO preferences(user_id) VALUES(?)',(user['id'],))
            if values:c.execute('UPDATE preferences SET '+','.join(k+'=?' for k in values)+' WHERE user_id=?',list(values.values())+[user['id']])
        result=dict(c.execute('SELECT * FROM preferences WHERE user_id=?',(user['id'],)).fetchone() or {'tour_step':0,'tour_completed':0,'notifications':1})
    elif path=='reminders/run' and method=='POST':
        require(user,'settings',True)
        from .notifications import deadlines
        deadlines(c,user);result={'ok':True,'external_delivery':'Niet geconfigureerd; uitsluitend interne meldingen.'}
    elif path=='settings' and method in ('GET','PUT'):
        require(user,'settings',method!='GET');keys={'organization','services','departments','planning_weights','retention_days','labor_rules','invoice_numbering','document_retention_auto'}
        if method=='PUT':
            if set(body)-keys:raise Problem('Onbekende instelling.')
            for key,value in body.items():
                if key=='planning_weights':
                    if not isinstance(value,dict) or set(value)-{'availability','workload','familiarity','region','skills'} or any(not isinstance(v,(int,float)) or isinstance(v,bool) or not 0<=v<=100 for v in value.values()):raise Problem('Planningsgewichten: getallen tussen 0 en 100.')
                elif key=='document_retention_auto':
                    if not isinstance(value,bool):raise Problem('Kies expliciet aan of uit voor automatische documentverwijdering.')
                elif key=='invoice_numbering':finance.validate_numbering(value)
                elif key=='labor_rules':
                    from .labor_rules import validate
                    validate(value)
                elif key=='retention_days':
                    if not 1<=int(value)<=36500:raise Problem('Bewaartermijn buiten bereik.')
                else:text(value,4000)
                c.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,json.dumps(value,ensure_ascii=False)))
            audit(c,user,'update','settings',0)
        result={r['key']:json.loads(r['value']) for r in c.execute('SELECT * FROM settings') if r['key'] in keys};result['integrations']={'email':'Niet geconfigureerd','push':'Niet geconfigureerd','accounting':'CSV-export; geen automatische boeking','tunnel':'Optioneel via start.py --tunnel; geen productiepublicatie'}
    elif path=='sessions' and method=='GET':result=[{'id':r['token'][:16],'expires':r['expires']} for r in c.execute('SELECT token,expires FROM sessions WHERE user_id=?',(user['id'],))]
    elif path=='sessions/revoke' and method=='POST':
        prefix=text(body.get('id',''),16,True)
        if len(prefix)!=16:raise Problem('Ongeldige sessiereferentie.')
        c.execute('DELETE FROM sessions WHERE user_id=? AND substr(token,1,16)=?',(user['id'],prefix));audit(c,user,'revoke','sessions',user['id']);result={'ok':True}
    elif path=='audit' and method=='GET':
        if user['role'] not in {'admin','company_admin','operations','director','auditor'}:raise Problem('Geen toegang tot het wijzigingslogboek.',403)
        result=[dict(x) for x in c.execute('SELECT * FROM audit WHERE actor LIKE ? AND module LIKE ? ORDER BY id DESC LIMIT 200',('%'+query.get('actor','')+'%','%'+query.get('module','')+'%'))]
    else:raise Problem('Route niet gevonden.',404)
    if method!='GET':c.commit()
    return h.respond(result,status)
