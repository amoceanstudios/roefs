"""Beperkte belastingproef met fictieve schaaldata; geen productiebenchmark."""
import concurrent.futures,datetime,json,sqlite3,statistics,time
from support import LiveServer,ROOT
s=LiveServer()
try:
 with sqlite3.connect(s.db) as c:
  c.executemany("INSERT INTO employees(name,contract_hours,status) VALUES(?,32,'Actief')",[(f'Demomedewerker {i:03}',) for i in range(2,251)])
  c.executemany("INSERT INTO customers(name,status) VALUES(?,'Actief')",[(f'Demoklant {i:03}',) for i in range(2,801)])
  week=datetime.date.today();week-=datetime.timedelta(days=week.weekday())
  c.execute('DELETE FROM shifts')
  c.executemany("INSERT INTO shifts(object_id,employee_id,date,start_time,end_time,status) VALUES('1',?,?,'08:00','12:00','Gepland')",[(str(e),str(week+datetime.timedelta(days=d))) for e in range(1,251) for d in range(5)])
 token=s.login();routes=['/api/dashboard','/api/planning/overview','/api/records/customers','/api/smart/overview']*6
 def request(path):
  start=time.perf_counter();status,body,_=s.request(path,token=token)
  assert status==200,(path,status,body)
  if path.endswith('/customers'):assert len(body)==800
  if path.endswith('/overview') and 'planning' in path:assert len(body['shifts'])==1250 and len(body['employees'])==250
  return round((time.perf_counter()-start)*1000,1)
 start=time.perf_counter()
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:times=list(pool.map(request,routes))
 with sqlite3.connect(s.db) as c:integrity=c.execute('PRAGMA integrity_check').fetchone()[0]
 result={'employees':250,'customers':800,'shifts':1250,'requests':len(times),'concurrency':4,'passed':len(times),'failed':0,'median_ms':round(statistics.median(times),1),'max_ms':max(times),'elapsed_seconds':round(time.perf_counter()-start,2),'sqlite_integrity':integrity,'limitations':'Korte lokale leesproef. Geen duurtest, 250 gelijktijdige gebruikers, productie-infrastructuur of extern tunnelverkeer.'}
 (ROOT/'reports'/'load-smoke.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
finally:s.close()
