import os,subprocess,tempfile,time,json,urllib.request,urllib.error,sqlite3
root=os.path.dirname(os.path.abspath(__file__))
checks=[]
with tempfile.TemporaryDirectory() as tmp:
 env={**os.environ,'PORT':'19874','ROEFS_DB':tmp+'/test.db','ROEFS_DEMO_GATE':''}
 p=subprocess.Popen(['python3',root+'/server.py'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
 try:
  for _ in range(70):
   if p.poll() is not None:raise RuntimeError(p.communicate()[1].decode())
   try:urllib.request.urlopen('http://127.0.0.1:19874/api/health',timeout=.3);break
   except Exception:time.sleep(.1)
  def api(route,method='GET',data=None,token=None,expected=200):
   r=urllib.request.Request('http://127.0.0.1:19874/api/'+route,method=method,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json',**({'Authorization':'Bearer '+token} if token else {})})
   try:
    with urllib.request.urlopen(r,timeout=8) as resp:status=resp.status;body=json.load(resp)
   except urllib.error.HTTPError as e:status=e.code;body=json.load(e)
   assert status==expected,(route,status,expected,body)
   checks.append(route+' '+str(status));return body
  api('health')
  api('users',expected=401)
  a=api('login','POST',{'username':'Roefs','password':'Amocean1!'})['token']
  b=api('login','POST',{'username':'Bart van Aalde','password':'Amocean2!'})['token']
  api('login','POST',{'username':'Roefs','password':'wrong'},expected=401)
  for tok in (a,b):
   api('me',token=tok);api('modules',token=tok);api('dashboard',token=tok);api('messages',token=tok)
  for module in ['customers','objects','contracts','quotes','invoices','ledger','payroll','employees','shifts','hours','inspections','logbook','workorders','orders','assets','keys','vehicles','documents','leave','alerts']:
   data=api('records/'+module,token=a);assert len(data)==1,(module,len(data))
  for route in ['users','hr/profiles','demo/chain','smart/overview','autopilot/jobs','audit']:
   api(route,token=a);api(route,token=b,expected=403)
  for route in ['records/customers','records/employees','records/payroll','records/invoices']:
   api(route,token=b,expected=403)
  for route in ['records/shifts','records/hours','records/workorders','records/logbook']:
   api(route,token=b)
  api('records/shifts','POST',{'object_id':'1'},token=b,expected=403)
  api('users','POST',{'username':'No rights','password':'TestPassword123','role':'employee'},token=b,expected=403)
  u=api('users','POST',{'username':'Demo planner','password':'TestPassword123','role':'employee'},token=a,expected=201)['id']
  api('users/permissions','POST',{'user_id':u,'permissions':['objects','orders']},token=a)
  api('users/permissions','POST',{'user_id':u,'permissions':['payroll']},token=a,expected=400)
  api('messages','POST',{'subject':'Voorraad','body':'Microvezeldoeken bijna op'},token=b,expected=201)
  msgs=api('messages',token=a);assert len(msgs)==1 and msgs[0]['sender']=='Bart van Aalde'
  api('messages/read','POST',{'id':msgs[0]['id']},token=b,expected=403)
  api('messages/read','POST',{'id':msgs[0]['id']},token=a)
  assert api('messages',token=a)[0]['read_at']
  api('logout','POST',{},token=b)
  api('me',token=b,expected=401)
  print('PASS:',len(checks),'API checks')
 finally:p.terminate();p.wait(timeout=10)
