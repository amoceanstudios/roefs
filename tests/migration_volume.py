"""Daadwerkelijke synthetische CSV/XLSX-migratie via HTTP; geen productiedataset."""
import base64,csv,datetime as dt,io,json,sqlite3,threading,time,subprocess,sys,urllib.request,urllib.error
from pathlib import Path
from support import LiveServer,ROOT
sys.path.insert(0,str(ROOT))
from services.spreadsheets import xlsx

def fixtures():
 day=dt.date(2030,2,4)
 data={
 'customers':[['external_id','name'],*[[f'C{i:05}',f'Fictieve migratieklant {i:05}'] for i in range(800)]],
 'employees':[['external_id','name','contract_hours'],*[[f'E{i:05}',f'Fictieve migratiemedewerker {i:05}','38'] for i in range(250)]],
 'objects':[['external_id','name','customer_id'],*[[f'L{i:05}',f'Fictieve migratielocatie {i:05}',f'C{i%800:05}'] for i in range(2000)]],
 'contracts':[['external_id','name','customer_id','object_id','monthly_value','start_date','end_date'],*[[f'K{i:05}',f'Fictief migratiecontract {i:05}',f'C{i%800:05}',f'L{i:05}','100','01-01-2030','31-12-2030'] for i in range(1000)]],
 'workorders':[['external_id','object_id','contract_id','description','date','start_time','end_time','capacity'],*[[f'W{i:05}',f'L{i%1000:05}',f'K{i%1000:05}',f'Fictieve migratieopdracht {i:05}',str(day+dt.timedelta(days=i//250)),'08:00','09:00','1'] for i in range(5000)]],
 'shifts':[['external_id','object_id','employee_id','workorder_id','date','start_time','end_time'],*[[f'P{i:05}',f'L{i%1000:05}',f'E{i%250:05}',f'W{i:05}',str(day+dt.timedelta(days=i//250)),'08:00','09:00'] for i in range(5000)]],
 'hours':[['external_id','employee_id','workorder_id','date','hours','starts_at','ends_at','break_minutes'],*[[f'H{i:05}',f'E{(i//2)%250:05}',f'W{i//2:05}',str(day+dt.timedelta(days=(i//2)//250)),'0,5',str(day+dt.timedelta(days=(i//2)//250))+('T08:00:00+01:00' if i%2==0 else 'T08:30:00+01:00'),str(day+dt.timedelta(days=(i//2)//250))+('T08:30:00+01:00' if i%2==0 else 'T09:00:00+01:00'),'0'] for i in range(10000)]],
 }
 root=ROOT/'fixtures'/'migration';root.mkdir(parents=True,exist_ok=True)
 for category,rows in data.items():
  stream=io.StringIO();csv.writer(stream,delimiter=';').writerows(rows);(root/(category+'.csv')).write_text(stream.getvalue(),encoding='utf-8-sig');(root/(category+'.xlsx')).write_bytes(xlsx([('Gegevens',rows)]))
 return root,data

def run():
 root,data=fixtures();s=LiveServer();samples=[];stop=threading.Event();errors=[];contention=[];results=[]
 def sample():
  while not stop.wait(.2):
   try:samples.append(int(next(x.split()[1] for x in Path(f'/proc/{s.proc.pid}/status').read_text().splitlines() if x.startswith('VmRSS:'))))
   except (OSError,StopIteration):pass
 watcher=threading.Thread(target=sample,daemon=True);watcher.start()
 try:
  token=s.login()
  def req(path,body=None):
   payload=json.dumps(body).encode() if body is not None else None
   request=urllib.request.Request(s.url+'/api/v5/migration'+path,data=payload,headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
   try:r=urllib.request.urlopen(request,timeout=180)
   except urllib.error.HTTPError as exc:r=exc
   with r:
    result=json.load(r);assert r.status==200,(path,r.status,result);return result
  def concurrent_write():
   begin=time.perf_counter()
   try:
    status,body,_=s.request('/api/v5/entities/customers','POST',{'name':'Fictieve gelijktijdige controle '+str(time.time_ns())},token);contention.append({'status':status,'seconds':round(time.perf_counter()-begin,4)})
   except Exception as e:errors.append(type(e).__name__)
  for index,(category,rows) in enumerate(data.items()):
   started=time.perf_counter();format='csv' if index%2==0 else 'xlsx';blob=(root/(category+'.'+format)).read_bytes();job=req('/uploads',{'source':'Fictieve NoCore-volumetest','category':category,'filename':category+'.'+format,'content':base64.b64encode(blob).decode()});jid=job['id']
   with sqlite3.connect(s.db) as c:before=c.execute('SELECT COUNT(*) FROM '+category).fetchone()[0]
   thread=threading.Thread(target=concurrent_write);thread.start();job=req(f'/{jid}/preview',{'version':job['version'],'mapping':job['mapping'],'policy':'reject'});thread.join()
   assert job['status']=='Gecontroleerd',(category,job['summary'],[r for r in job['rows'] if r['preview']['action']=='Fout'][:2])
   with sqlite3.connect(s.db) as c:
    actual=c.execute('SELECT COUNT(*) FROM '+category).fetchone()[0];assert actual==before+(1 if category=='customers' else 0),(category,'proefrun wijzigde data')
   job=req(f'/{jid}/confirm',{'version':job['version'],'confirm':True})
   while job['status']=='Bezig':job=req(f'/{jid}/batch',{'version':job['version']})
   assert job['status']=='Voltooid',(category,job.get('last_error'));assert job['results']['Nieuw']==len(rows)-1
   elapsed=time.perf_counter()-started
   # Hetzelfde bestand opnieuw door upload, proefrun en definitieve verwerking.
   repeat=req('/uploads',{'source':'Fictieve NoCore-volumetest','category':category,'filename':category+'.'+format,'content':base64.b64encode(blob).decode()});repeat=req(f'/{repeat["id"]}/preview',{'version':repeat['version'],'mapping':repeat['mapping'],'policy':'reject'});assert repeat['summary']['Ongewijzigd']==len(rows)-1,(category,repeat['summary'],repeat['rows'][:1]);repeat=req(f'/{repeat["id"]}/confirm',{'version':repeat['version'],'confirm':True})
   while repeat['status']=='Bezig':repeat=req(f'/{repeat["id"]}/batch',{'version':repeat['version']})
   assert repeat['status']=='Voltooid';results.append({'category':category,'format':format,'rows':len(rows)-1,'first_import_seconds':round(elapsed,3),'repeat_unchanged':repeat['results']['Ongewijzigd']});print(json.dumps(results[-1]),flush=True)
  s.stop();s.start()
  with sqlite3.connect(s.db) as c:
   assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert c.execute('PRAGMA foreign_key_check').fetchall()==[]
   assert c.execute('SELECT COUNT(*) FROM migration_links').fetchone()[0]==24050
   for query in ['SELECT COUNT(*) FROM objects o LEFT JOIN customers c ON c.id=o.customer_id WHERE o.customer_id!=\'\' AND c.id IS NULL','SELECT COUNT(*) FROM contracts k JOIN objects o ON o.id=k.object_id WHERE k.customer_id!=o.customer_id','SELECT COUNT(*) FROM shifts s JOIN workorders w ON w.id=s.workorder_id WHERE s.object_id!=w.object_id','SELECT COUNT(*) FROM hours h LEFT JOIN employees e ON e.id=h.employee_id WHERE e.id IS NULL']:assert c.execute(query).fetchone()[0]==0
  backup=Path(s.temp.name)/'migration-backup.zip';target=Path(s.temp.name)/'restored';subprocess.run([sys.executable,str(ROOT/'manage.py'),'backup','--db',str(s.db),'--output',str(backup)],check=True,capture_output=True);subprocess.run([sys.executable,str(ROOT/'manage.py'),'restore','--archive',str(backup),'--target',str(target)],check=True,capture_output=True)
  with sqlite3.connect(target/'roefs.db') as c:assert c.execute('SELECT COUNT(*) FROM migration_links').fetchone()[0]==24050
  assert not errors and all(x['status']==201 for x in contention),contention
  report={'results':results,'external_links':24050,'peak_sampled_server_rss_mb':round(max(samples,default=0)/1024,2),'concurrent_writes':contention,'integrity':'ok','foreign_keys':0,'restart':True,'backup_restore':True,'limitations':'Fictieve NoCore-achtige bestanden; geen echte NoCore-export, productiehardware of onafhankelijke acceptatie.'};(ROOT/'reports'/'migration-volume.json').write_text(json.dumps(report,indent=2));return 0
 finally:stop.set();watcher.join();s.close()
if __name__=='__main__':raise SystemExit(run())
