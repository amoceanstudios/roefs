import os,sys,tempfile,subprocess,time,json,urllib.request,urllib.error
from pathlib import Path
root=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as t:
 env={**os.environ,'PORT':'19591','ROEFS_DB':t+'/test.db','ROEFS_DEMO_GATE':''}
 p=subprocess.Popen([sys.executable,str(root/'server.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
 try:
  def req(path,method='GET',body=None,token=None):
   h={'Content-Type':'application/json'}
   if token:h['Authorization']='Bearer '+token
   r=urllib.request.Request('http://127.0.0.1:19591/api/'+path,data=json.dumps(body).encode() if body is not None else None,headers=h,method=method)
   try:
    with urllib.request.urlopen(r,timeout=15) as f:return f.status,json.load(f)
   except urllib.error.HTTPError as e:return e.code,json.loads(e.read())
  for i in range(50):
   if p.poll() is not None:raise RuntimeError(p.communicate()[1].decode())
   try:req('health');break
   except:time.sleep(.1)
  a=req('login','POST',{'username':'Roefs','password':'Amocean1!'})[1]['token'];b=req('login','POST',{'username':'Bart van Aalde','password':'Amocean2!'})[1]['token']
  checks=[]
  def check(ok,name):
   checks.append(name);assert ok,name
  st,ov=req('planning/overview',token=a);check(st==200,'overview admin');check(len(ov['shifts'])==1,'one example');check(len(ov['employees'])==1,'employees visible admin')
  st,em=req('planning/overview',token=b);check(st==200,'overview employee');check(not em['employees'],'no employee roster list')
  check(req('planning/suggest','POST',{'date':ov['shifts'][0]['date'],'start_time':'09:00','end_time':'11:00'},b)[0]==403,'employee cannot suggest')
  check(req('planning/suggest','POST',{'date':'2026-10-11','start_time':'15:00','end_time':'12:00'},a)[0]==400,'invalid hours suggestion')
  st,r=req('planning/suggest','POST',{'date':ov['shifts'][0]['date'],'start_time':'08:00','end_time':'12:00'},a);check(st==200,'suggest works');check(len(r['candidates'])==0,'overlap filters candidate')
  st,r=req('planning/suggest','POST',{'date':ov['shifts'][0]['date'],'start_time':'12:00','end_time':'16:00'},a);check(len(r['candidates'])==1,'adjacent shift available')
  sh={'object_id':'1','employee_id':'1','date':ov['shifts'][0]['date'],'start_time':'09:00','end_time':'11:00','status':'Gepland'}
  check(req('records/shifts','POST',sh,a)[0]==409,'reject overlapping shift')
  sh['start_time']='16:00';sh['end_time']='12:00';check(req('records/shifts','POST',sh,a)[0]==400,'reject inverted times')
  sh['start_time']='12:00';sh['end_time']='16:00';st,new=req('records/shifts','POST',sh,a);check(st==201,'allow adjacent shift')
  sh['object_id']='999';check(req('records/shifts','POST',sh,a)[0]==400,'reject nonexistent object')
  sh['object_id']='1';sh['employee_id']='999';check(req('records/shifts','POST',sh,a)[0]==400,'reject nonexistent employee')
  check(req('records/shifts/'+str(new['id']),'PUT',{'start_time':'10:00'},a)[0]==409,'reject overlapping shift update')
  check(req('records/shifts/'+str(new['id']),'PUT',{'end_time':'11:00'},a)[0]==400,'reject inverted update')
  check(req('records/shifts','POST',sh,b)[0]==403,'employee cannot create shift')
  print('PASS:',len(checks),'planning/permissions checks')
 finally:
  p.terminate();p.wait(timeout=5)
