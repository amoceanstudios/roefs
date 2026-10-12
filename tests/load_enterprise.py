"""Gemengde lokale belasting met synthetische schaaldata; geen productiecertificering."""
import concurrent.futures,datetime as dt,json,os,platform,resource,sqlite3,statistics,time
from pathlib import Path
from support import LiveServer,ROOT

def run():
 s=LiveServer()
 try:
  with sqlite3.connect(s.db) as c:
   c.executemany("INSERT INTO employees(name,contract_hours,status,department) VALUES(?,32,'Actief','Fictieve industrie')",[(f'Fictieve medewerker {i:03}',) for i in range(2,251)])
   c.executemany("INSERT INTO customers(name,status) VALUES(?,'Actief')",[(f'Fictieve klant {i:03}',) for i in range(2,801)])
   c.executemany("INSERT INTO objects(name,customer_id,status) VALUES(?,?,'Actief')",[(f'Fictieve werklocatie {i:04}',str((i-1)%800+1)) for i in range(2,1601)])
   start=dt.date(2030,1,7)
   for d in range(20):
    date=str(start+dt.timedelta(days=d))
    for e in range(1,251):
     obj=str((e+d*250-1)%1600+1)
     w=c.execute("INSERT INTO workorders(object_id,employee_id,description,date,hours,status) VALUES(?,?,'Fictieve belastingopdracht',?,'4','Afgerond')",(obj,str(e),date)).lastrowid
     sh=c.execute("INSERT INTO shifts(object_id,employee_id,date,start_time,end_time,status) VALUES(?,?,?,'08:00','12:00','Gepland')",(obj,str(e),date)).lastrowid
     c.execute("INSERT INTO hours(employee_id,shift_id,workorder_id,date,hours,status) VALUES(?,?,?,?,'4','Goedgekeurd')",(str(e),str(sh),w,date))
  token=s.login();routes=['/api/v5/entities/customers?limit=25&offset=500','/api/v5/planning/calendar?from=2030-01-07&to=2030-01-13','/api/v5/reports?from=2030-01-07&to=2030-01-13','/api/v5/entities/workorders?limit=25','/api/v5/entities/employees?limit=25']
  requests=int(os.environ.get('ROEFS_LOAD_REQUESTS','100'));concurrency=int(os.environ.get('ROEFS_LOAD_CONCURRENCY','8'));assert 20<=requests<=2000 and 1<=concurrency<=64;before=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.perf_counter();rss=[]
  def request(i):
   begin=time.perf_counter()
   try:
    if i%5==0:code,body,_=s.request('/api/v5/entities/customers','POST',{'name':f'Fictieve belastingmutatie {i:04}'},token)
    else:code,body,_=s.request(routes[i%len(routes)],token=token)
    try:
     status=Path(f'/proc/{s.proc.pid}/status').read_text();rss.append(int(next(line.split()[1] for line in status.splitlines() if line.startswith('VmRSS:'))))
    except OSError:pass
    return {'status':code,'ms':(time.perf_counter()-begin)*1000,'error':body.get('error','') if isinstance(body,dict) else ''}
   except Exception as exc:return {'status':0,'ms':(time.perf_counter()-begin)*1000,'error':type(exc).__name__}
  with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:results=list(pool.map(request,range(requests)))
  elapsed=time.perf_counter()-start;times=sorted(x['ms'] for x in results);failed=[x for x in results if x['status'] not in (200,201)]
  with sqlite3.connect(s.db) as c:integrity=c.execute('PRAGMA integrity_check').fetchone()[0];fk=c.execute('PRAGMA foreign_key_check').fetchall();counts={m:c.execute('SELECT COUNT(*) FROM '+m).fetchone()[0] for m in ('employees','customers','objects','workorders','shifts','hours')}
  s.stop();after=resource.getrusage(resource.RUSAGE_CHILDREN)
  report={'environment':{'python':platform.python_version(),'platform':platform.platform(),'logical_cpus':os.cpu_count(),'network':'Loopback HTTP, geen tunnel of externe ERP'},'data':counts,'requests':requests,'concurrency':concurrency,'read_percent':80,'write_percent':20,'elapsed_seconds':round(elapsed,3),'requests_per_second':round(requests/elapsed,2),'median_ms':round(statistics.median(times),2),'p95_ms':round(times[int(.95*len(times))-1],2),'p99_ms':round(times[max(0,int(.99*len(times))-1)],2),'max_ms':round(max(times),2),'failed':len(failed),'error_rate_percent':len(failed)/requests*100,'http_503_database_unavailable':sum(x['status']==503 for x in results),'server_peak_sampled_rss_mb':round(max(rss,default=0)/1024,2),'server_cpu_seconds':round(after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,3),'sqlite_integrity':integrity,'foreign_key_violations':len(fk),'limitations':[f'Korte lokale proef met {concurrency} gelijktijdige verzoeken; geen 250 gelijktijdige gebruikers of duurtest.','CPU is gemeten over de gehele serverlevensduur, inclusief opstart en fixtures.','Contention gemeten via zichtbare HTTP 503; interne SQLite-wachttijd niet afzonderlijk geïnstrumenteerd.','RSS periodiek bemonsterd; echte piek kan hoger zijn.','Geen echte mobiele hardware, externe ERP of productie-infrastructuur.'],'errors':failed}
  (ROOT/'reports'/('load-enterprise-'+str(concurrency)+'.json')).write_text(json.dumps(report,indent=2));(ROOT/'reports'/'load-enterprise.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));return 1 if failed or integrity!='ok' or fk else 0
 finally:s.close()
if __name__=='__main__':raise SystemExit(run())
