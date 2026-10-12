import time,logging,re
from services import migrations,access,authentication,sync_migrations,synchronization,mfa,operational_migrations
from services.routes import dispatch
from domain import Problem, REFERENCES, REQUIRED, STATUSES, NUMBERS, LABELS, date_value, interval, schedule_issues, scoped_rows, validate, protect_delete
import json,sqlite3,os,hashlib,hmac,secrets,threading,datetime,csv,io,urllib.parse,base64
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DB=Path(os.environ.get('ROEFS_DB',str(ROOT/'data'/'roefs.db')));DB.parent.mkdir(parents=True,exist_ok=True)
PORT=int(os.environ.get('PORT','8765'))
MODULES={
'customers':('Relaties',['name','contact','email','phone','city','status']),
'objects':('Objecten',['name','customer_id','address','city','type','frequency','status']),
'contracts':('Contracten',['name','customer_id','object_id','monthly_value','start_date','end_date','status']),
'quotes':('Offertes',['name','customer_id','amount','status','description']),
'invoices':('Facturen',['number','customer_id','contract_id','amount','due_date','status']),
'ledger':('Boekhouding',['description','date','account','debit','credit','status']),
'payroll':('Verloning',['employee_id','period','hours','gross_amount','status']),
'employees':('HRM',['name','role','email','phone','contract_hours','status']),
'shifts':('Planning',['object_id','employee_id','date','start_time','end_time','status']),
'hours':('Urenregistratie',['employee_id','shift_id','date','hours','status']),
'inspections':('Kwaliteit DKS/VSR',['object_id','inspector','date','score','status','notes']),
'logbook':('Digitaal logboek',['object_id','author','date','message','status']),
'workorders':('Werkbonnen',['object_id','employee_id','description','date','hours','status','signed_by']),
'orders':('Bestellingen',['item','object_id','quantity','unit','status']),
'assets':('Materieel',['name','serial','object_id','inspection_date','status']),
'keys':('Sleutelregistratie',['object_id','key_code','holder','issued_at','status']),
'vehicles':('Wagenpark',['plate','model','driver','inspection_date','status']),
'documents':('Documenten',['name','category','reference','date','status']),
'leave':('Verlof & verzuim',['employee_id','start_date','end_date','type','status']),
'availability':('Beschikbaarheid',['employee_id','date','start_time','end_time','status']),
'alerts':('Meldingen',['title','severity','description','status'])}
CONN=threading.local()
LOGIN_LOCK=threading.Lock()
LOGIN_ATTEMPTS={}
def conn():
 if not hasattr(CONN,'db'):
  CONN.db=sqlite3.connect(DB,timeout=15,check_same_thread=False);CONN.db.row_factory=sqlite3.Row;CONN.db.execute('PRAGMA foreign_keys=ON');CONN.db.execute('PRAGMA journal_mode=WAL')
 return CONN.db
def log(actor,action,module,record,detail=''):
 conn().execute('INSERT INTO audit(actor,action,module,record_id,detail,at) VALUES(?,?,?,?,?,?)',(actor,action,module,record,str(detail),datetime.datetime.now().isoformat(timespec='seconds')))
def init():
 c=conn();c.execute('CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT)');c.execute('CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,actor TEXT,action TEXT,module TEXT,record_id INTEGER,detail TEXT,at TEXT)');c.execute('CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE,salt TEXT,password_hash TEXT,role TEXT)');c.execute('CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER,expires TEXT)');c.execute('CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT,sender_id INTEGER NOT NULL,subject TEXT NOT NULL,body TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,read_at TEXT)');c.execute('CREATE TABLE IF NOT EXISTS permissions(user_id INTEGER NOT NULL,module TEXT NOT NULL,PRIMARY KEY(user_id,module))')
 c.execute('CREATE TABLE IF NOT EXISTS autopilot_jobs(id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT NOT NULL,source_id INTEGER NOT NULL,candidate_id INTEGER,status TEXT NOT NULL,payload TEXT NOT NULL,created_by TEXT,approved_by TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,executed_at TEXT,notes TEXT)')
 c.execute('CREATE INDEX IF NOT EXISTS autopilot_status ON autopilot_jobs(status,created_at)')
 c.execute('''CREATE TABLE IF NOT EXISTS employee_cao_profiles(employee_id INTEGER PRIMARY KEY,employment_start TEXT NOT NULL DEFAULT '',wage_group INTEGER,step INTEGER,contract_type TEXT DEFAULT '',commute_km_round_trip TEXT DEFAULT '',notes TEXT DEFAULT '',updated_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
 c.execute('''CREATE TABLE IF NOT EXISTS employee_contract_terms(id INTEGER PRIMARY KEY AUTOINCREMENT,employee_id INTEGER NOT NULL,start_date TEXT NOT NULL,end_date TEXT NOT NULL,kind TEXT NOT NULL DEFAULT 'Bepaalde tijd',created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
 c.execute('CREATE INDEX IF NOT EXISTS terms_employee ON employee_contract_terms(employee_id,start_date)')
 for m,(_,fields) in MODULES.items():
  c.execute('CREATE TABLE IF NOT EXISTS '+m+'(id INTEGER PRIMARY KEY AUTOINCREMENT,'+','.join(f+' TEXT DEFAULT \'\'' for f in fields)+',created_at TEXT DEFAULT CURRENT_TIMESTAMP,updated_at TEXT DEFAULT CURRENT_TIMESTAMP)')
 fresh=not c.execute('SELECT 1 FROM users LIMIT 1').fetchone()
 if 'employee_id' not in {x[1] for x in c.execute('PRAGMA table_info(users)')}:
  c.execute('ALTER TABLE users ADD COLUMN employee_id INTEGER')
  c.execute('ALTER TABLE users ADD COLUMN active INTEGER NOT NULL DEFAULT 1')
 if fresh:
  pw=os.environ.get('ROEFS_ADMIN_PASSWORD')
  if not pw:raise RuntimeError('Start via start.py of stel ROEFS_ADMIN_PASSWORD en ROEFS_EMPLOYEE_PASSWORD in.')
  salt=secrets.token_hex(16);ph=hashlib.pbkdf2_hmac('sha256',pw.encode(),bytes.fromhex(salt),250000).hex()
  c.execute('INSERT INTO users(username,salt,password_hash,role) VALUES(?,?,?,?)',('Roefs',salt,ph,'admin'))
 if fresh:
  salt=secrets.token_hex(16);pw=os.environ.get('ROEFS_EMPLOYEE_PASSWORD')
  if not pw:raise RuntimeError('ROEFS_EMPLOYEE_PASSWORD ontbreekt. Start via start.py.')
  ph=hashlib.pbkdf2_hmac('sha256',pw.encode(),bytes.fromhex(salt),250000).hex()
  c.execute('INSERT INTO users(username,salt,password_hash,role) VALUES(?,?,?,?)',('Bart van Aalde',salt,ph,'employee'))
 if fresh and not c.execute('SELECT 1 FROM customers LIMIT 1').fetchone():
  today=datetime.date.today(); examples={
  'customers':['Voorbeeldklant Eindhoven','Contactpersoon','contact@voorbeeld.invalid','040-0000000','Eindhoven','Actief'],
  'objects':['Kantoorlocatie Eindhoven','1','Voorbeeldstraat 12','Eindhoven','Kantoor','Dagelijks','Actief'],
  'contracts':['Dagelijkse interieurverzorging','1','1','2450',str(today.replace(day=1)),str(today+datetime.timedelta(days=365)),'Actief'],
  'quotes':['Extra glasbewassing','1','650','Concept','Periodieke glasbewassing'],
  'invoices':['CONCEPT-001','1','1','2450',str(today+datetime.timedelta(days=30)),'Concept'],
  'ledger':['Voorbeeld omzetboeking',str(today),'8000','0','2450','Concept'],
  'payroll':['1',today.strftime('%Y-%m'),'32','0','Concept'],
  'employees':['Bart van Aalde','Interieurverzorger','medewerker@voorbeeld.invalid','06-00000000','32','Actief'],
  'shifts':['1','1',str(today),'08:00','12:00','Gepland'],
  'hours':['1','1',str(today),'4','Goedgekeurd'],
  'inspections':['1','Rayonleider',str(today),'92','Afgerond','Voorbeeldcontrole'],
  'logbook':['1','Kantoor',str(today),'Controleer de sanitaire voorraad.','Open'],
  'workorders':['1','1','Periodieke glasbewassing',str(today),'3','Nieuw',''],
  'orders':['Microvezeldoeken','1','10','stuks','Aangevraagd'],
  'assets':['Schrobzuigmachine','DEMO-001','1',str(today+datetime.timedelta(days=90)),'Beschikbaar'],
  'keys':['1','SLEUTEL-001','Bart van Aalde',str(today),'Uitgegeven'],
  'vehicles':['XX-000-X','Bedrijfsbus','Bart van Aalde',str(today+datetime.timedelta(days=90)),'Actief'],
  'documents':['Schoonmaakinstructie','Werkinstructie','Object 1',str(today),'Actief'],
  'leave':['1',str(today+datetime.timedelta(days=15)),str(today+datetime.timedelta(days=16)),'Verlof','Aangevraagd'],
  'alerts':['Werkbon wacht op toewijzing','Normaal','Bekijk de werkbon in het werkoverzicht.','Open']}
  for m,v in examples.items():
   fields=MODULES[m][1];c.execute('INSERT INTO '+m+'('+','.join(fields)+') VALUES('+','.join('?' for _ in fields)+')',v)
  c.execute('INSERT OR IGNORE INTO employee_cao_profiles(employee_id,employment_start,wage_group,step,contract_type,commute_km_round_trip,notes) VALUES(?,?,?,?,?,?,?)',(1,'2025-01-01',1,1,'Bepaalde tijd','12','Fictief demonstratieprofiel'))
  c.execute('INSERT INTO employee_contract_terms(employee_id,start_date,end_date,kind) VALUES(?,?,?,?)',(1,'2026-01-01','2027-12-31','Bepaalde tijd'))
 if not c.execute("SELECT 1 FROM settings WHERE key='account_link_v1'").fetchone():
  # Eenmalige migratie: uitsluitend een unieke bestaande naam koppelen.
  c.execute("UPDATE users SET employee_id=(SELECT MIN(id) FROM employees WHERE name=users.username) WHERE role='employee' AND (SELECT COUNT(*) FROM employees WHERE name=users.username)=1")
  c.execute("INSERT INTO settings VALUES('account_link_v1','done')")
 for table in ('shifts','hours','leave','availability','workorders'):
  c.execute('CREATE INDEX IF NOT EXISTS idx_'+table+'_employee ON '+table+'(employee_id)')
 c.execute('CREATE INDEX IF NOT EXISTS idx_shifts_date ON shifts(date,employee_id)')
 c.execute('DELETE FROM sessions WHERE expires<?',(datetime.datetime.now().isoformat(),))
 migrations.migrate(c,MODULES)
 sync_migrations.migrate(c)
 mfa.migrate(c)
 operational_migrations.migrate(c)
 c.commit()
def rows(m):return [dict(r) for r in conn().execute('SELECT * FROM '+m+' ORDER BY id DESC')]
def number(v):
 try:return float(v or 0)
 except:return 0
# 2026 basisuurlonen: officiële Schoonmakend Nederland tabel, 1 januari 2026.
# Rijen: dienstjaar 1 t/m 4; kolommen loongroep 1 t/m 6.
CAO_WAGES_2026={1:[15.52,16.08,16.70,17.53,18.20,19.12],2:[16.08,16.63,17.30,18.14,18.82,19.77],3:[16.55,17.17,17.84,18.73,19.45,20.42],4:[17.05,17.70,18.44,19.31,20.06,21.07]}
CAO_SOURCE='https://www.schoonmakendnederland.nl/cao-schoonmaak-en-glazenwassersbedrijf/loontabellen-2026'
CAO_FULL='https://www.schoonmakendnederland.nl/l/library/download/urn:uuid:c6e8fab5-f683-42cc-96f4-f23f08ec70ec/cao+schoonmaak+definitief+%28zonder+fnv%29%2C+2026-2028.pdf?format=save_to_disk'
def cao_calc(b):
 from decimal import Decimal,ROUND_HALF_UP
 def dec(v):return Decimal(str(v))
 def eur(v):return str(v.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP))
 date=datetime.date.fromisoformat(str(b['date']))
 if not (datetime.date(2026,1,1)<=date<=datetime.date(2028,6,30)):raise ValueError('Kies een datum tussen 2026-01-01 en 2028-06-30')
 group=int(b['group']);step=int(b['step']);hours=dec(b.get('hours',0))
 if group not in range(1,7) or step not in CAO_WAGES_2026:raise ValueError('Deze calculator ondersteunt uitsluitend dienstjaren 1 t/m 4 en loongroepen 1 t/m 6')
 if hours<0 or hours>744:raise ValueError('Uren buiten toegestaan bereik')
 base=dec(CAO_WAGES_2026[step][group-1]);factor=Decimal('1');changes=[]
 if date>=datetime.date(2027,1,1):factor*=Decimal('1.031');changes.append('1 januari 2027: +3,1%')
 if date>=datetime.date(2028,1,1):factor*=Decimal('1.03');changes.append('1 januari 2028: +3,0%')
 hourly=base*factor
 return {'date':str(date),'group':group,'step':step,'hours':str(hours),'base_2026':eur(base),'hourly_estimate':eur(hourly),'gross_estimate':eur(hourly*hours),'changes':changes,'source':CAO_SOURCE,'status':'Indicatieve bruto basisloonberekening; geen loonstrook of definitieve cao-loontabel voor 2027/2028','warnings':['Alleen basisuurloon, geen toeslagen, all-in loon, vakantiegeld, pensioen, belasting of uitzonderingen.','2027/2028: rekenkundige projectie vanaf 2026, niet de gepubliceerde loontabel.']}
def cao_contract_check(b):
 dates=b.get('start_dates',[])
 if not isinstance(dates,list) or not 1<=len(dates)<=20:raise ValueError('Voer 1 tot 20 contractstartdatums in')
 starts=sorted(datetime.date.fromisoformat(str(x)) for x in dates)
 if len(starts)!=len(set(starts)):raise ValueError('Dubbele contractstartdatums; controleer invoer')
 from_start=starts[0];new=any(x>=datetime.date(2026,9,1) for x in starts)
 # Overgangsbepaling vereist beoordeling per arbeidscontract, geen automatische rechtsgevolgen.
 limit=21 if from_start>=datetime.date(2026,9,1) else 24
 months=(starts[-1].year-from_start.year)*12+starts[-1].month-from_start.month
 signals=[]
 if len(starts)>=3:signals.append('Drie of meer opgegeven contracten: controleer de ketenregeling en eventuele uitzonderingen.')
 if months>=limit-2:signals.append('Startdatums beslaan bijna of meer dan de indicatieve '+str(limit)+'-maandengrens; controleer einddatums en tussenpozen.')
 if new and from_start<datetime.date(2026,9,1):signals.append('Overgangssituatie rond 1 september 2026: handmatige beoordeling vereist.')
 signals.append('Zonder einddatums, tussenpozen, opvolgend werkgeverschap en uitzonderingen is geen definitief oordeel mogelijk.')
 return {'starts':[str(x) for x in starts],'count':len(starts),'indicative_limit_months':limit,'months_between_first_last_start':months,'signals':signals,'result':'Signalering; geen juridisch oordeel','source':CAO_FULL}
def cao_sickness_check(b):
 start=datetime.date.fromisoformat(str(b['employment_start']));ill=datetime.date.fromisoformat(str(b['sick_start']))
 if ill<start:raise ValueError('Ziektedatum mag niet vóór indiensttreding liggen')
 if ill<datetime.date(2026,7,1):return {'status':'Niet berekend','reason':'Voor ziektegevallen vóór 1 juli 2026 moet de eerdere regeling worden toegepast.','source':CAO_FULL}
 years=(ill-start).days/365.2425
 def anniversary(n):
  try:return start.replace(year=start.year+n)
  except ValueError:return start.replace(year=start.year+n,month=2,day=28)
 rate=85 if ill<anniversary(2) else 90 if ill<=anniversary(6) else 100
 special=b.get('exception','none')
 if special not in ('none','work_accident','pregnancy'):raise ValueError('Onbekende uitzondering')
 if special!='none':rate=100
 return {'status':'Indicatieve cao-loondoorbetaling','service_years_approx':round(years,2),'percentage':rate,'year_1':rate,'year_2':rate,'warnings':['Wettelijk minimumloon, dagloondefinitie, wachtdagen, toepasselijkheid en overige cao-voorwaarden controleren.','Dit is geen verzuimdiagnose of definitieve loonberekening.'],'source':CAO_FULL}
def cao_travel_preview(b):
 from decimal import Decimal,ROUND_HALF_UP
 date=datetime.date.fromisoformat(str(b['date']))
 if date<datetime.date(2027,1,1):raise ValueError('Deze nieuwe cao-reisregeling geldt vanaf 1 januari 2027')
 km=Decimal(str(b.get('km_round_trip','0')));days=int(b.get('days','0'));rate=Decimal(str(b.get('rate','0')))
 if not (Decimal('0')<=km<=Decimal('1000')) or not 0<=days<=31 or not Decimal('0')<rate<=Decimal('0.50'):raise ValueError('Controleer kilometers, werkdagen en handmatig gekozen tarief')
 result=(km*days*rate).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
 return {'amount':str(result),'km_round_trip':str(km),'days':days,'rate':str(rate),'status':'Rekenvoorbeeld op basis van handmatig ingevoerd tarief','warnings':['Het juiste fiscaal onbelaste maximum voor de peildatum is niet automatisch opgehaald.','Controleer cao-uitzonderingen, verhuizingen en feitelijk gereden kilometers.'],'source':CAO_FULL}
class Handler(BaseHTTPRequestHandler):
 def send_response(self,code,message=None):
  super().send_response(code,message)
  self.send_header('X-Content-Type-Options','nosniff')
  self.send_header('X-Frame-Options','DENY')
  self.send_header('Referrer-Policy','no-referrer')
  self.send_header('Permissions-Policy','camera=(), microphone=(), geolocation=()')
  self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'; object-src 'none'")
  if getattr(self,'_gate_cookie',False):
   self.send_header('Set-Cookie','roefs_demo_gate='+hashlib.sha256(os.environ.get('ROEFS_DEMO_GATE','').encode()).hexdigest()+'; HttpOnly; Secure; SameSite=Lax; Path=/')
 def respond(self,obj,status=200,headers=None):
  data=json.dumps(obj,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY');self.send_header('Referrer-Policy','no-referrer');self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'");
  for k,v in (headers or {}).items():self.send_header(k,v)
  self.end_headers();self.wfile.write(data)
 def body(self):
  if self.headers.get_content_type()!='application/json':raise Problem('Verstuur gegevens als JSON.',415)
  if self.headers.get('Transfer-Encoding'):raise Problem('Niet-ondersteunde overdracht.',400)
  try:n=int(self.headers.get('Content-Length','0'))
  except ValueError:raise Problem('Ongeldige verzoeklengte.')
  if not 0<=n<=1000000:raise Problem('Verzoek te groot of ongeldig.',413)
  try:b=json.loads(self.rfile.read(n) or b'{}',parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
  except (ValueError,UnicodeDecodeError):raise Problem('Ongeldige JSON-invoer.')
  if not isinstance(b,dict):raise Problem('Verwacht een JSON-object.')
  return b
 def actor(self):
  token,_=authentication.session_token(self)
  r=conn().execute('SELECT u.id,u.username,u.role,u.employee_id FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>? AND u.active=1',(hashlib.sha256(token.encode()).hexdigest(),datetime.datetime.now().isoformat())).fetchone() if token else None
  return dict(r) if r else None
 def route(self,method):
  if method!='GET':
   origin=self.headers.get('Origin')
   if origin and urllib.parse.urlsplit(origin).netloc!=self.headers.get('Host'):
    raise Problem('Verzoek vanaf een andere website geweigerd.',403)
  gate=os.environ.get('ROEFS_DEMO_GATE','')
  if gate:
   auth=self.headers.get('Authorization','')
   try:
    encoded=auth.split(' ',1)[1] if auth.startswith('Basic ') else ''
    supplied=base64.b64decode(encoded,validate=True).decode('utf-8')
   except (ValueError,UnicodeDecodeError,IndexError):supplied=''
   cookie=self.headers.get('Cookie','')
   valid_cookie=any(hmac.compare_digest(item.strip(),'roefs_demo_gate='+hashlib.sha256(gate.encode()).hexdigest()) for item in cookie.split(';'))
   valid_basic=hmac.compare_digest(supplied,'demo:'+gate)
   if not (valid_cookie or valid_basic):
    self.send_response(401)
    self.send_header('WWW-Authenticate','Basic realm="ROEFS ONE prive demo"')
    self.send_header('Cache-Control','no-store')
    self.send_header('Content-Length','0')
    self.end_headers()
    return
   self._gate_cookie=valid_basic
  path=urllib.parse.urlsplit(self.path).path
  if path in ('/app.js','/ui.js','/styles.css','/ui.css','/enterprise.js','/enterprise.css','/nl.js','/integrations.js') and method=='GET':
   data=(ROOT/path[1:]).read_bytes();self.send_response(200);self.send_header('Content-Type','text/javascript; charset=utf-8' if path.endswith('.js') else 'text/css; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-cache');self.end_headers();self.wfile.write(data);return
  if path=='/assets/amocean-mark.png':
   data=(ROOT/'assets'/'amocean-mark.png').read_bytes();self.send_response(200);self.send_header('Content-Type','image/png');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
  if path=='/' or path=='/index.html':
   data=(ROOT/'index.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
  if path=='/api/health':
   conn().execute('SELECT 1').fetchone()
   return self.respond({'ok':True,'database':'connected','modules':len(MODULES),'instance':os.environ.get('ROEFS_INSTANCE_ID','')})
  if path=='/api/login' and method=='POST':
   b=self.body();username=str(b.get('username',''))[:80];key=(self.client_address[0],username);now=time.monotonic()
   with LOGIN_LOCK:
    for k in list(LOGIN_ATTEMPTS):
     if now-LOGIN_ATTEMPTS[k][0]>300:del LOGIN_ATTEMPTS[k]
    attempts=LOGIN_ATTEMPTS.get(key,(now,0))
    if attempts[1]>=10:raise Problem('Te veel inlogpogingen. Probeer over vijf minuten opnieuw.',429)
    if len(LOGIN_ATTEMPTS)>10000:raise Problem('Te veel verzoeken. Probeer later opnieuw.',429)
    LOGIN_ATTEMPTS[key]=(attempts[0],attempts[1]+1)
   r=conn().execute('SELECT * FROM users WHERE username=? AND active=1',(username,)).fetchone()
   good=r and hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',str(b.get('password','')).encode(),bytes.fromhex(r['salt']),r['password_iterations']).hex(),r['password_hash'])
   if not good:return self.respond({'error':'Ongeldige inloggegevens'},401)
   if r['mfa_secret']:
    conn().execute('BEGIN IMMEDIATE')
    current=conn().execute('SELECT mfa_secret,mfa_counter FROM users WHERE id=?',(r['id'],)).fetchone()
    counter=mfa.verify(current['mfa_secret'],b.get('code',''),current['mfa_counter']);conn().execute('UPDATE users SET mfa_counter=? WHERE id=?',(counter,r['id']))
   if r['password_iterations']<600000:
    hashed=hashlib.pbkdf2_hmac('sha256',str(b.get('password','')).encode(),bytes.fromhex(r['salt']),600000).hex();conn().execute('UPDATE users SET password_hash=?,password_iterations=600000 WHERE id=?',(hashed,r['id']))
   with LOGIN_LOCK:LOGIN_ATTEMPTS.pop(key,None)
   token=secrets.token_urlsafe(36);exp=(datetime.datetime.now()+datetime.timedelta(hours=8)).isoformat();conn().execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),r['id'],exp));conn().commit();return self.respond({'token':token,'csrf':authentication.csrf(token),'username':r['username'],'role':r['role']},headers={'Set-Cookie':authentication.cookie(self,token)})
  user=self.actor()
  if not user:return self.respond({'error':'Log eerst in'},401)
  c=conn();uid=user['id'];admin=user['role']!='employee'
  authentication.check_csrf(self,method)
  if path.startswith('/api/v5/'):
   return dispatch(self,c,user,path[8:],method,MODULES,DB)
  if user['role']!='employee':access.legacy_access(user,path,method,MODULES)
  if path=='/api/me' and method=='GET':
   return self.respond({'username':user['username'],'role':user['role'],'employee_id':user['employee_id'],'csrf':authentication.csrf(authentication.session_token(self)[0]),'permissions':[r['module'] for r in c.execute('SELECT module FROM permissions WHERE user_id=?',(uid,))]})
  if path=='/api/logout' and method=='POST':
   tok,_=authentication.session_token(self);c.execute('DELETE FROM sessions WHERE token=?',(hashlib.sha256(tok.encode()).hexdigest(),));c.commit();return self.respond({'ok':True},headers={'Set-Cookie':authentication.cookie(self,'',True)})
  if path=='/api/messages' and method=='GET':
   if user['role'] in access.ADMIN:return self.respond([dict(r) for r in c.execute('SELECT m.*,u.username AS sender FROM messages m JOIN users u ON u.id=m.sender_id ORDER BY m.id DESC LIMIT 100')])
   return self.respond([dict(r) for r in c.execute('SELECT m.*,u.username AS sender FROM messages m JOIN users u ON u.id=m.sender_id WHERE sender_id=? ORDER BY m.id DESC LIMIT 100',(uid,))])
  if path=='/api/messages' and method=='POST':
   b=self.body();subject=str(b.get('subject','')).strip()[:120];body=str(b.get('body','')).strip()[:1500]
   if not subject or not body:return self.respond({'error':'Onderwerp en bericht zijn verplicht'},400)
   c.execute('INSERT INTO messages(sender_id,subject,body) VALUES(?,?,?)',(uid,subject,body));log(user['username'],'send','messages',c.execute('SELECT last_insert_rowid()').fetchone()[0]);c.commit();return self.respond({'ok':True},201)
  if path=='/api/messages/read' and method=='POST':
   if not admin:return self.respond({'error':'Alleen beheerder'},403)
   mid=int(self.body().get('id',0));
   if not c.execute('SELECT 1 FROM messages WHERE id=?',(mid,)).fetchone():raise Problem('Bericht niet gevonden.',404)
   log(user['username'],'read','messages',mid);c.execute('UPDATE messages SET read_at=CURRENT_TIMESTAMP WHERE id=?',(mid,));c.commit();return self.respond({'ok':True})
  if path=='/api/users' and method=='GET':
   if not admin:return self.respond({'error':'Alleen beheerder'},403)
   return self.respond([{'id':r['id'],'username':r['username'],'role':r['role'],'employee_id':r['employee_id'],'active':bool(r['active']),'permissions':[p['module'] for p in c.execute('SELECT module FROM permissions WHERE user_id=?',(r['id'],))]} for r in c.execute('SELECT id,username,role,employee_id,active FROM users ORDER BY id')])
  if path=='/api/users' and method=='POST':
   if not admin:return self.respond({'error':'Alleen beheerder'},403)
   b=self.body();username=str(b.get('username','')).strip()[:80];pw=str(b.get('password',''));role=b.get('role','employee')
   if not username or not 12<=len(pw)<=200 or role not in access.ROLES:return self.respond({'error':'Gebruikersnaam, wachtwoord van 12 tot 200 tekens en geldige rol vereist'},400)
   eid=b.get('employee_id') or None
   if eid and not c.execute('SELECT 1 FROM employees WHERE id=?',(eid,)).fetchone():raise Problem('Medewerker niet gevonden.')
   salt=secrets.token_hex(16);ph=hashlib.pbkdf2_hmac('sha256',pw.encode(),bytes.fromhex(salt),250000).hex()
   try:
    cur=c.execute('INSERT INTO users(username,salt,password_hash,role,employee_id) VALUES(?,?,?,?,?)',(username,salt,ph,role,eid));log(user['username'],'create','users',cur.lastrowid);c.commit();return self.respond({'id':cur.lastrowid},201)
   except sqlite3.IntegrityError:return self.respond({'error':'Gebruikersnaam bestaat al'},409)
  if path=='/api/users/update' and method=='POST':
   if not admin:raise Problem('Alleen beheer kan accounts aanpassen.',403)
   b=self.body();target=int(b.get('user_id',0));c.execute('BEGIN IMMEDIATE')
   old=c.execute('SELECT * FROM users WHERE id=?',(target,)).fetchone()
   if not old:raise Problem('Gebruiker niet gevonden.',404)
   role=b.get('role',old['role']);active=b.get('active',bool(old['active']))
   if role not in access.ROLES or not isinstance(active,bool):raise Problem('Ongeldige rol of accountstatus.')
   if old['role']=='admin' and old['active'] and (role!='admin' or not active):
    if c.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND active=1").fetchone()[0]<=1:raise Problem('Het laatste actieve beheerdersaccount moet behouden blijven.',409)
   password=b.get('password','')
   if password and (not isinstance(password,str) or not 12<=len(password)<=200):raise Problem('Gebruik een wachtwoord van 12 tot 200 tekens.')
   c.execute('UPDATE users SET role=?,active=? WHERE id=?',(role,int(active),target))
   if password:
    salt=secrets.token_hex(16);ph=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),250000).hex()
    c.execute('UPDATE users SET salt=?,password_hash=?,password_iterations=250000 WHERE id=?',(salt,ph,target))
   if password or not active or role!=old['role']:c.execute('DELETE FROM sessions WHERE user_id=?',(target,))
   log(user['username'],'update','users',target,'Accountrechten of wachtwoord bijgewerkt');c.commit();return self.respond({'ok':True})
  if path=='/api/users/permissions' and method=='POST':
   if not admin:return self.respond({'error':'Alleen beheerder'},403)
   b=self.body();target=int(b.get('user_id',0));allowed={'shifts','hours','workorders','logbook','objects','orders','assets','documents','inspections','employeeportal'}
   perms=b.get('permissions',[])
   if not isinstance(perms,list) or any(x not in allowed for x in perms):return self.respond({'error':'Ongeldige rechten'},400)
   if not c.execute('SELECT 1 FROM users WHERE id=?',(target,)).fetchone():return self.respond({'error':'Gebruiker onbekend'},404)
   log(user['username'],'permissions','users',target)
   c.execute('DELETE FROM permissions WHERE user_id=?',(target,));c.executemany('INSERT INTO permissions(user_id,module) VALUES(?,?)',[(target,p) for p in set(perms)]);c.commit();return self.respond({'ok':True})
  employee_default={'start','dashboard','messages','shifts','hours','workorders','logbook','employeeportal','availability','leave'}
  allowed_employee=employee_default|{r['module'] for r in c.execute('SELECT module FROM permissions WHERE user_id=?',(uid,))}
  if not admin:
   public_employee={'/api/modules','/api/dashboard','/api/planning/overview','/api/lookups'}
   if not path.startswith('/api/records/') and path not in public_employee:
    raise Problem('Geen toegang tot deze functie.',403)
   if path.startswith('/api/records/'):
    mod=path.split('/')[3]
    if mod not in MODULES or mod not in allowed_employee:raise Problem('Geen toegang tot deze module.',403)
  if path=='/api/users/link' and method=='POST':
   b=self.body();target=int(b.get('user_id',0));eid=b.get('employee_id') or None
   if eid and not c.execute('SELECT 1 FROM employees WHERE id=?',(eid,)).fetchone():raise Problem('Medewerker niet gevonden.')
   if not c.execute('SELECT 1 FROM users WHERE id=?',(target,)).fetchone():raise Problem('Gebruiker niet gevonden.',404)
   c.execute('UPDATE users SET employee_id=? WHERE id=?',(eid,target));log(user['username'],'link','users',target);c.commit();return self.respond({'ok':True})
  if path=='/api/lookups' and method=='GET':
   result={}
   for m in ('customers','objects','contracts','employees','shifts'):
    source=rows(m) if admin and access.permitted(user,m) else scoped_rows(c,m,user)
    if (not admin or not access.permitted(user,m)) and m=='employees':source=[dict(x) for x in c.execute('SELECT id,name FROM employees WHERE id=?',(user['employee_id'],))]
    result[m]=[{'id':x['id'],'name':x.get('name') or (x.get('date','')+' '+x.get('start_time','')+' #'+str(x['id']))} for x in source]
   return self.respond(result)
  if path=='/api/modules' and method=='GET':
   return self.respond({m:{'label':v[0],'fields':v[1],'required':REQUIRED[m],'statuses':STATUSES[m],'references':{f:REFERENCES[f] for f in v[1] if f in REFERENCES},'numbers':{f:NUMBERS[f] for f in v[1] if f in NUMBERS}} for m,v in MODULES.items() if (admin and access.permitted(user,m)) or (not admin and m in allowed_employee)})
  if path=='/api/dashboard' and user['role'] not in access.ADMIN:
   if user['role']!='employee':
    return self.respond({'counts':{m:c.execute('SELECT COUNT(*) FROM '+m).fetchone()[0] for m in MODULES if access.permitted(user,m)}})
  if path=='/api/dashboard' and not admin:
   own={m:scoped_rows(c,m,user) for m in MODULES if m in allowed_employee}
   return self.respond({'counts':{m:len(v) for m,v in own.items()},'open_workorders':sum(x['status'] not in ('Afgerond','Geannuleerd') for x in own['workorders']),'pending_hours':sum(x['status']=='Ingediend' for x in own['hours'])})
  # Planning intelligence: validated proposals, no unapproved automatic assignments.
  if path=='/api/planning/overview' and method=='GET':
   query=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
   try:day=datetime.date.fromisoformat(query.get('date',[str(datetime.date.today())])[0])
   except ValueError:return self.respond({'error':'Ongeldige datum'},400)
   week=day-datetime.timedelta(days=day.weekday());end=week+datetime.timedelta(days=6)
   shifts=[dict(r) for r in c.execute('SELECT * FROM shifts WHERE date BETWEEN ? AND ? ORDER BY date,start_time,id',(str(week),str(end)))]
   if not admin:
    shifts=[sh for sh in shifts if sh['employee_id']==str(user['employee_id'])]
   employees={str(r['id']):dict(r) for r in c.execute('SELECT * FROM employees')}
   objects={str(r['id']):dict(r) for r in c.execute('SELECT * FROM objects')}
   conflicts=[];unassigned=[];bad_times=[];weekly={}
   for sh in shifts:
    eid=sh['employee_id'];sid=sh['id'];daystr=sh['date']
    if sh['status']=='Geannuleerd':continue
    if not eid or eid not in employees:unassigned.append(sid)
    if sh['start_time']>=sh['end_time'] or len(sh['start_time'])!=5 or len(sh['end_time'])!=5:bad_times.append(sid);continue
    if eid and eid in employees:
     try:weekly[eid]=round(weekly.get(eid,0)+(datetime.datetime.strptime(sh['end_time'],'%H:%M')-datetime.datetime.strptime(sh['start_time'],'%H:%M')).total_seconds()/3600,2)
     except ValueError:bad_times.append(sid)
   for i,a in enumerate(shifts):
    if a['status']=='Geannuleerd' or not a['employee_id']:continue
    for b in shifts[i+1:]:
     if b['status']!='Geannuleerd' and a['date']==b['date'] and a['employee_id']==b['employee_id'] and a['start_time']<b['end_time'] and a['end_time']>b['start_time']:
      conflicts.append([a['id'],b['id']])
   for sh in shifts:
    sh['employee_name']=employees.get(sh['employee_id'],{}).get('name','Niet toegewezen')
    sh['object_name']=objects.get(sh['object_id'],{}).get('name','Onbekend object')
   unavailable=[{'id':sh['id'],'reasons':schedule_issues(c,sh,sh['id'])} for sh in shifts if sh['id'] not in bad_times and sh['status']!='Geannuleerd']
   return self.respond({'availability_conflicts':[x for x in unavailable if x['reasons']], 'week_start':str(week),'week_end':str(end),'shifts':shifts,'employees':list(employees.values()) if admin and access.permitted(user,'employees') else [],'objects':list(objects.values()) if admin else [],'conflicts':conflicts,'unassigned':unassigned,'invalid_times':sorted(set(bad_times)),'weekly_hours':weekly if admin else {}})
  if path=='/api/planning/suggest' and method=='POST':
   if not admin:return self.respond({'error':'Alleen beheerder'},403)
   b=self.body();date=str(b.get('date',''));start=str(b.get('start_time',''));end=str(b.get('end_time',''));exclude=str(b.get('exclude_shift_id',''))
   try:
    datetime.date.fromisoformat(date);a=datetime.datetime.strptime(start,'%H:%M');z=datetime.datetime.strptime(end,'%H:%M')
    if z<=a:raise ValueError()
   except ValueError:return self.respond({'error':'Vul een geldige datum en tijden in; einde moet na begin liggen'},400)
   interval({'date':date,'start_time':start,'end_time':end})
   candidates=[]
   for emp in c.execute("SELECT * FROM employees WHERE status='Actief' ORDER BY name"):
    busy=c.execute("SELECT 1 FROM shifts WHERE employee_id=? AND date=? AND status!='Geannuleerd' AND id!=? AND start_time<? AND end_time>? LIMIT 1",(str(emp['id']),date,exclude or '-1',end,start)).fetchone()
    away=c.execute("SELECT 1 FROM leave WHERE employee_id=? AND status IN ('Goedgekeurd','Ziek','Ziekgemeld') AND start_date<=? AND end_date>=? LIMIT 1",(str(emp['id']),date,date)).fetchone()
    candidate={'date':date,'start_time':start,'end_time':end,'employee_id':str(emp['id']),'status':'Gepland'}
    if schedule_issues(c,candidate,exclude or -1):continue
    total=0
    week=datetime.date.fromisoformat(date);ws=str(week-datetime.timedelta(days=week.weekday()));we=str(week-datetime.timedelta(days=week.weekday())+datetime.timedelta(days=6))
    for sh in c.execute("SELECT start_time,end_time FROM shifts WHERE employee_id=? AND date BETWEEN ? AND ? AND status!='Geannuleerd' AND id!=?",(str(emp['id']),ws,we,exclude or '-1')):
     try:total+=(datetime.datetime.strptime(sh['end_time'],'%H:%M')-datetime.datetime.strptime(sh['start_time'],'%H:%M')).total_seconds()/3600
     except ValueError:pass
    hours=(z-a).total_seconds()/3600;contract=number(emp['contract_hours']);projected=round(total+hours,2)
    candidates.append({'id':emp['id'],'name':emp['name'],'role':emp['role'],'planned_hours':round(total,2),'projected_hours':projected,'contract_hours':contract,'above_contract':bool(contract and projected>contract),'availability_registered':bool(c.execute('SELECT 1 FROM availability WHERE employee_id=? AND date=?',(str(emp['id']),date)).fetchone()),'note':'Overlap, verlof en geregistreerde beschikbaarheid gecontroleerd; reistijd en kwalificaties handmatig beoordelen.'})
   candidates.sort(key=lambda x:(x['above_contract'],x['projected_hours'],x['name']))
   return self.respond({'candidates':candidates,'automatic_assignment':False,'checks':['Roosteroverlap','Goedgekeurd verlof/verzuim','Indicatieve contracturen'],'limitations':['Geen reistijdberekening','Niet-geregistreerde beschikbaarheid is onbekend','Geen volledige CAO- of rusttijdcontrole']})
  if path=='/api/demo/chain' and method=='GET':
   c=conn()
   def one(m):
    r=c.execute('SELECT * FROM '+m+' ORDER BY id LIMIT 1').fetchone()
    return dict(r) if r else None
   customer=one('customers');obj=one('objects');employee=one('employees')
   chain={m:one(m) for m in ('customers','objects','contracts','employees','shifts','hours','workorders','inspections','logbook','quotes','invoices','orders','assets','keys','vehicles','documents','leave','payroll','ledger','alerts')}
   checks=[]
   for table,field,target in [('objects','customer_id','customers'),('contracts','customer_id','customers'),('contracts','object_id','objects'),('shifts','employee_id','employees'),('shifts','object_id','objects'),('hours','employee_id','employees'),('hours','shift_id','shifts'),('workorders','object_id','objects'),('workorders','employee_id','employees'),('invoices','customer_id','customers'),('invoices','contract_id','contracts')]:
    missing=c.execute('SELECT COUNT(*) FROM '+table+' t WHERE t.'+field+" != '' AND NOT EXISTS (SELECT 1 FROM "+target+' x WHERE CAST(x.id AS TEXT)=t.'+field+')').fetchone()[0]
    checks.append({'name':MODULES[table][0]+' → '+MODULES[target][0],'ok':missing==0,'issues':missing})
   for m in MODULES:
    n=c.execute('SELECT COUNT(*) FROM '+m).fetchone()[0]
    checks.append({'name':MODULES[m][0]+': '+str(n)+' opgeslagen regels','ok':True,'issues':0,'note':'Aantal opgeslagen records; geen maximum van één demonstratierecord.'})
   return self.respond({'chain':chain,'checks':checks,'passed':sum(x['ok'] for x in checks),'total':len(checks),'demo_only':True,'message':'Demonstratie van gekoppelde records. Geen productiecertificering of volledige ERP-dekking.'})
  if path=='/api/hr/profiles' and method=='GET':
   c=conn();profiles={r['employee_id']:dict(r) for r in c.execute('SELECT * FROM employee_cao_profiles')}
   return self.respond([{'employee':dict(e),'profile':profiles.get(e['id']),'terms':[dict(t) for t in c.execute('SELECT * FROM employee_contract_terms WHERE employee_id=? ORDER BY start_date',(e['id'],))]} for e in c.execute('SELECT * FROM employees ORDER BY name')])
  if path=='/api/hr/profile' and method=='POST':
   b=self.body();c=conn();eid=int(b.get('employee_id',0))
   if not c.execute('SELECT 1 FROM employees WHERE id=?',(eid,)).fetchone():return self.respond({'error':'Medewerker niet gevonden'},404)
   start=str(b.get('employment_start','')).strip();group=str(b.get('wage_group','')).strip();step=str(b.get('step','')).strip()
   if start:datetime.date.fromisoformat(start)
   if group and (not group.isdigit() or int(group) not in range(1,7)):raise ValueError('Loongroep moet 1 t/m 6 zijn')
   if step and (not step.isdigit() or int(step) not in range(1,5)):raise ValueError('Deze demo ondersteunt alleen treden 1 t/m 4')
   from decimal import Decimal
   km=str(b.get('commute_km_round_trip','')).strip()
   if km and not (Decimal('0')<=Decimal(km)<=Decimal('1000')):raise ValueError('Kilometers buiten bereik')
   c.execute('''INSERT INTO employee_cao_profiles(employee_id,employment_start,wage_group,step,contract_type,commute_km_round_trip,notes) VALUES(?,?,?,?,?,?,?) ON CONFLICT(employee_id) DO UPDATE SET employment_start=excluded.employment_start,wage_group=excluded.wage_group,step=excluded.step,contract_type=excluded.contract_type,commute_km_round_trip=excluded.commute_km_round_trip,notes=excluded.notes,updated_at=CURRENT_TIMESTAMP''',(eid,start,int(group) if group else None,int(step) if step else None,str(b.get('contract_type',''))[:80],km,str(b.get('notes',''))[:300]))
   log(user['username'],'update','employee_cao_profiles',eid);c.commit();return self.respond({'ok':True})
  if path=='/api/hr/contract-term' and method=='POST':
   b=self.body();c=conn();eid=int(b.get('employee_id',0))
   if not c.execute('SELECT 1 FROM employees WHERE id=?',(eid,)).fetchone():return self.respond({'error':'Medewerker niet gevonden'},404)
   start=datetime.date.fromisoformat(str(b.get('start_date','')));end=datetime.date.fromisoformat(str(b.get('end_date','')))
   if end<start:raise ValueError('Einddatum ligt vóór startdatum')
   kind=str(b.get('kind','Bepaalde tijd'))
   if kind not in ('Bepaalde tijd','Onbepaalde tijd'):raise ValueError('Ongeldig contracttype')
   if c.execute('SELECT 1 FROM employee_contract_terms WHERE employee_id=? AND start_date<=? AND end_date>=?',(eid,str(end),str(start))).fetchone():return self.respond({'error':'Overlappende contractperioden'},409)
   cur=c.execute('INSERT INTO employee_contract_terms(employee_id,start_date,end_date,kind) VALUES(?,?,?,?)',(eid,str(start),str(end),kind))
   log(user['username'],'create','employee_contract_terms',cur.lastrowid);c.commit();return self.respond({'ok':True,'id':cur.lastrowid},201)
  if path=='/api/hr/contract-term/delete' and method=='POST':
   b=self.body();c=conn();tid=int(b.get('id',0));r=c.execute('SELECT * FROM employee_contract_terms WHERE id=?',(tid,)).fetchone()
   if not r:return self.respond({'error':'Contractperiode niet gevonden'},404)
   c.execute('DELETE FROM employee_contract_terms WHERE id=?',(tid,));log(user['username'],'delete','employee_contract_terms',tid);c.commit();return self.respond({'ok':True})
  if path=='/api/hr/preview' and method=='POST':
   b=self.body();eid=int(b.get('employee_id',0));c=conn();employee=c.execute('SELECT * FROM employees WHERE id=?',(eid,)).fetchone()
   if not employee:return self.respond({'error':'Medewerker niet gevonden'},404)
   profile=c.execute('SELECT * FROM employee_cao_profiles WHERE employee_id=?',(eid,)).fetchone()
   date=datetime.date.fromisoformat(str(b.get('date',datetime.date.today().isoformat())))
   period=str(b.get('period',date.strftime('%Y-%m')))
   if len(period)!=7 or period[4]!='-' or not period[:4].isdigit() or not period[5:].isdigit() or not 1<=int(period[5:])<=12:raise ValueError('Periode moet JJJJ-MM zijn')
   hrs=[dict(x) for x in c.execute('SELECT * FROM hours WHERE employee_id=? AND substr(date,1,7)=?',(str(eid),period))]
   accepted=[x for x in hrs if x['status'] in ('Goedgekeurd','Akkoord')]
   pending=[x for x in hrs if x['status'] not in ('Goedgekeurd','Akkoord','Afgewezen')]
   from decimal import Decimal
   total=sum((Decimal(str(x['hours'])) for x in accepted if str(x['hours']).strip()),Decimal('0'))
   warnings=[]
   if any(Decimal(str(x['hours']))<0 or Decimal(str(x['hours']))>24 for x in hrs if str(x['hours']).strip()):warnings.append('Urenregel met onwaarschijnlijk aantal uren; handmatig controleren.')
   if pending:warnings.append(str(len(pending))+' urenregels wachten nog op beoordeling; niet meegenomen.')
   wage=None
   if profile and profile['wage_group'] and profile['step']:
    wage=cao_calc({'date':str(date),'group':profile['wage_group'],'step':profile['step'],'hours':str(total)})
   else:warnings.append('Loongroep of trede ontbreekt in het personeelsdossier.')
   terms=[dict(t) for t in c.execute('SELECT * FROM employee_contract_terms WHERE employee_id=? ORDER BY start_date',(eid,))]
   temporary=[t for t in terms if t['kind']=='Bepaalde tijd']
   if len(temporary)>=3:warnings.append('Drie of meer tijdelijke contracten geregistreerd; ketenregeling laten beoordelen.')
   for t in terms:
    if t['end_date']>=str(date) and t['end_date']<=str(date+datetime.timedelta(days=60)):warnings.append('Contract eindigt binnen 60 dagen: '+t['end_date'])
   if not terms:warnings.append('Geen contractperioden geregistreerd.')
   if not profile or not profile['employment_start']:warnings.append('Indiensttredingsdatum ontbreekt.')
   return self.respond({'employee':dict(employee),'period':period,'date':str(date),'approved_hours':str(total),'approved_entries':len(accepted),'pending_entries':len(pending),'wage':wage,'terms':terms,'warnings':warnings,'status':'Alleen controle en indicatieve bruto salarisvoorbereiding; niets geboekt of uitbetaald','source':CAO_FULL})
  if path=='/api/cao/contract-check' and method=='POST':
   try:return self.respond(cao_contract_check(self.body()))
   except (ValueError,KeyError,TypeError) as e:return self.respond({'error':str(e)},400)
  if path=='/api/cao/sickness-check' and method=='POST':
   try:return self.respond(cao_sickness_check(self.body()))
   except (ValueError,KeyError,TypeError) as e:return self.respond({'error':str(e)},400)
  if path=='/api/cao/travel-preview' and method=='POST':
   try:return self.respond(cao_travel_preview(self.body()))
   except (ValueError,KeyError,TypeError) as e:return self.respond({'error':str(e)},400)
  if path=='/api/cao/rules':
   return self.respond({'period':'2026-07-01 t/m 2028-06-30','full_text':CAO_FULL,'wages_2026':CAO_SOURCE,'wage_changes':[{'date':'2027-01-01','percent':3.1},{'date':'2028-01-01','percent':3.0}],'temporary_contracts':{'max_contracts':3,'max_months':21,'effective_for_contracts_started_on_or_after':'2026-09-01','previous_limit_months':24},'sickness_new_cases_from':'2026-07-01','sickness_rates':[{'service':'0 tot minder dan 2 jaar','rate':85},{'service':'2 tot en met 6 jaar','rate':90},{'service':'langer dan 6 jaar','rate':100}],'sickness_exceptions':'Bij bedrijfsongeval of zwangerschapsgerelateerde ziekte 100%; wettelijke minimumloonbescherming en overige cao-voorwaarden gelden.','note':'Bronnen voor HR-controle, geen volledige geautomatiseerde salarisverwerking.'})
  if path=='/api/cao/calculate' and method=='POST':
   try:return self.respond(cao_calc(self.body()))
   except (ValueError,KeyError,ArithmeticError) as e:return self.respond({'error':str(e)},400)
  if path=='/api/modules':return self.respond({m:{'label':v[0],'fields':v[1]} for m,v in MODULES.items()})
  if path=='/api/audit':return self.respond([dict(x) for x in conn().execute('SELECT * FROM audit ORDER BY id DESC LIMIT 100')])
  if path=='/api/dashboard':
   c=conn();counts={m:c.execute('SELECT COUNT(*) FROM '+m).fetchone()[0] for m in MODULES}
   invoiced=sum(number(x['amount']) for x in rows('invoices') if x['status'] not in ('Concept','Geannuleerd'))
   return self.respond({'counts':counts,'invoiced':invoiced,'open_workorders':sum(x['status'] not in ('Afgerond','Geannuleerd') for x in rows('workorders')),'pending_hours':sum(x['status']=='Ingediend' for x in rows('hours'))})
  if path=='/api/autopilot/jobs' and method=='GET':
   return self.respond([dict(r) for r in conn().execute('SELECT * FROM autopilot_jobs ORDER BY id DESC LIMIT 100')])
  if path=='/api/autopilot/propose' and method=='POST':
   b=self.body();kind=b.get('kind');source=b.get('source_id');candidate=b.get('candidate_id');c=conn()
   if kind not in ('shift_replacement','workorder_from_log','invoice_from_contract'):
    return self.respond({'error':'Onbekende workflow'},400)
   if not str(source).isdigit() or (kind=='shift_replacement' and not str(candidate).isdigit()):
    return self.respond({'error':'Selecteer geldige records'},400)
   source=int(source);candidate=int(candidate) if str(candidate).isdigit() else None
   if kind=='shift_replacement':
    sh=c.execute('SELECT * FROM shifts WHERE id=?',(source,)).fetchone()
    emp=c.execute("SELECT * FROM employees WHERE id=? AND status='Actief'",(candidate,)).fetchone()
    if not sh or not emp or sh['status']=='Geannuleerd':return self.respond({'error':'Dienst of medewerker ongeldig'},400)
    payload={'source_version':sh['version'],'shift_id':source,'employee_id':candidate,'employee':emp['name'],'date':sh['date'],'time':sh['start_time']+'–'+sh['end_time']}
   elif kind=='workorder_from_log':
    row=c.execute('SELECT * FROM logbook WHERE id=?',(source,)).fetchone()
    if not row or row['status']!='Open':return self.respond({'error':'Kies een open logboekmelding'},400)
    payload={'source_version':row['version'],'logbook_id':source,'object_id':row['object_id'],'description':row['message'],'date':datetime.date.today().isoformat()}
   else:
    row=c.execute('SELECT * FROM contracts WHERE id=?',(source,)).fetchone()
    if not row or row['status']!='Actief' or number(row['monthly_value'])<=0:return self.respond({'error':'Actief contract met geldig bedrag vereist'},400)
    payload={'source_version':row['version'],'contract_id':source,'customer_id':row['customer_id'],'amount':row['monthly_value'],'number':'CONCEPT-AUTO-'+str(source)+'-'+datetime.datetime.now().strftime('%Y%m%d%H%M%S')+'-'+secrets.token_hex(3)}
   cur=c.execute('INSERT INTO autopilot_jobs(kind,source_id,candidate_id,status,payload,created_by) VALUES(?,?,?,?,?,?)',(kind,source,candidate,'Wacht op goedkeuring',json.dumps(payload,ensure_ascii=False),user['username']))
   log(user['username'],'propose','autopilot_jobs',cur.lastrowid,kind);c.commit()
   return self.respond({'id':cur.lastrowid,'status':'Wacht op goedkeuring','preview':payload},201)
  if path=='/api/autopilot/decide' and method=='POST':
   b=self.body();jid=b.get('id');decision=b.get('decision')
   if not str(jid).isdigit() or decision not in ('approve','reject'):return self.respond({'error':'Ongeldig besluit'},400)
   c=conn();c.execute('BEGIN IMMEDIATE')
   try:
    job=c.execute('SELECT * FROM autopilot_jobs WHERE id=?',(int(jid),)).fetchone()
    if not job or job['status']!='Wacht op goedkeuring':
     c.rollback();return self.respond({'error':'Voorstel niet meer beschikbaar'},409)
    if decision=='reject':
     c.execute("UPDATE autopilot_jobs SET status='Afgewezen',approved_by=?,executed_at=CURRENT_TIMESTAMP WHERE id=?",(user['username'],int(jid)))
     log(user['username'],'reject','autopilot_jobs',int(jid));c.commit();return self.respond({'ok':True,'status':'Afgewezen'})
    d=json.loads(job['payload']);kind=job['kind']
    source_table={'shift_replacement':'shifts','workorder_from_log':'logbook','invoice_from_contract':'contracts'}[kind]
    source_row=c.execute('SELECT version FROM '+source_table+' WHERE id=?',(job['source_id'],)).fetchone()
    if not source_row or source_row['version']!=d.get('source_version'):raise ValueError('Brongegevens zijn gewijzigd. Beoordeel een nieuw voorstel.')
    if kind=='shift_replacement':
     sh=c.execute('SELECT * FROM shifts WHERE id=?',(d['shift_id'],)).fetchone()
     emp=c.execute("SELECT * FROM employees WHERE id=? AND status='Actief'",(d['employee_id'],)).fetchone()
     if not sh or not emp or sh['status']=='Geannuleerd':raise ValueError('Dienst of medewerker niet meer geldig')
     conflict=c.execute("SELECT 1 FROM shifts WHERE id!=? AND employee_id=? AND date=? AND status!='Geannuleerd' AND start_time<? AND end_time>? LIMIT 1",(d['shift_id'],str(d['employee_id']),sh['date'],sh['end_time'],sh['start_time'])).fetchone()
     issues=schedule_issues(c,{**dict(sh),'employee_id':str(d['employee_id'])},sh['id'])
     if issues:raise ValueError(' '.join(issues))
     c.execute("UPDATE shifts SET employee_id=?,status='Gepland',updated_at=CURRENT_TIMESTAMP WHERE id=?",(str(d['employee_id']),d['shift_id']))
     msg='Dienst toegewezen; medewerker handmatig informeren (geen SMS-integratie)'
    elif kind=='workorder_from_log':
     row=c.execute("SELECT * FROM logbook WHERE id=? AND status='Open'",(d['logbook_id'],)).fetchone()
     if not row:raise ValueError('Logboekmelding niet meer open')
     c.execute("INSERT INTO workorders(object_id,employee_id,description,date,hours,status,signed_by) VALUES(?,?,?,?,?,?,?)",(row['object_id'],'',row['message'],datetime.date.today().isoformat(),'0','Nieuw',''))
     c.execute("UPDATE logbook SET status='In behandeling',updated_at=CURRENT_TIMESTAMP WHERE id=?",(d['logbook_id'],))
     msg='Werkbon aangemaakt; medewerker nog toewijzen'
    else:
     row=c.execute("SELECT * FROM contracts WHERE id=? AND status='Actief'",(d['contract_id'],)).fetchone()
     if not row or number(row['monthly_value'])<=0:raise ValueError('Contract niet meer geldig')
     c.execute("INSERT INTO invoices(number,customer_id,contract_id,amount,due_date,status) VALUES(?,?,?,?,?,?)",(d['number'],row['customer_id'],str(d['contract_id']),row['monthly_value'],str(datetime.date.today()+datetime.timedelta(days=30)),'Concept'))
     msg='Conceptfactuur gemaakt; niets verzonden of geboekt'
    c.execute("UPDATE autopilot_jobs SET status='Uitgevoerd',approved_by=?,executed_at=CURRENT_TIMESTAMP,notes=? WHERE id=?",(user['username'],msg,int(jid)))
    log(user['username'],'approve_execute','autopilot_jobs',int(jid),kind);c.commit()
    return self.respond({'ok':True,'status':'Uitgevoerd','message':msg})
   except ValueError as e:c.rollback();return self.respond({'error':str(e)},409)
   except Exception:c.rollback();raise
  if path=='/api/smart/overview':
   c=conn();today=datetime.date.today().isoformat()
   data={m:[dict(x) for x in c.execute('SELECT * FROM '+m+' ORDER BY id DESC')] for m in MODULES}
   def cnt(m,p):return sum(1 for x in data[m] if p(x))
   def amount(m,f,p=lambda x:True):return round(sum(number(x.get(f)) for x in data[m] if p(x)),2)
   def shift_problem(row):
    if row['status']=='Geannuleerd':return False
    if not row['employee_id']:return True
    try:return bool(schedule_issues(c,row,row['id']))
    except Problem:return True
   results={
    'customers':('Relatie-assistent',cnt('customers',lambda x:x['status']!='Actief'),'Niet-actieve klantrelaties controleren','objects'),
    'objects':('Objectcontrole',cnt('objects',lambda x:not x['customer_id'] or not x['frequency']),'Objecten zonder klant of schoonmaakfrequentie','shifts'),
    'contracts':('Contractbewaker',cnt('contracts',lambda x:x['status']=='Actief' and bool(x['end_date']) and x['end_date']<=str(datetime.date.today()+datetime.timedelta(days=60))),'Actieve contracten die binnen 60 dagen aflopen','quotes'),
    'quotes':('Offerte-opvolging',cnt('quotes',lambda x:x['status'] in ('Concept','Verzonden')),'Concepten en verzonden offertes om op te volgen','contracts'),
    'invoices':('Debiteurenradar',cnt('invoices',lambda x:x['status']=='Open' and bool(x['due_date']) and x['due_date']<today),'Openstaande facturen voorbij vervaldatum','ledger'),
    'ledger':('Boekingscontrole',cnt('ledger',lambda x:x['status']=='Concept'),'Conceptboekingen om te controleren','invoices'),
    'payroll':('Looncontrole',cnt('payroll',lambda x:x['status']=='Concept'),'Loonregels in concept; geen cao-berekening','hours'),
    'employees':('HR Signalering',cnt('employees',lambda x:x['status']!='Actief'),'Medewerkers met niet-actieve status','leave'),
    'shifts':('Roosterbewaker',cnt('shifts',shift_problem),'Diensten met onbezetting, ongeldige tijden of beschikbaarheidsconflicten','sos'),
    'hours':('Urencontrole',cnt('hours',lambda x:x['status']=='Ingediend'),'Ingediende uren ter goedkeuring','payroll'),
    'leave':('Verlofcoördinator',cnt('leave',lambda x:x['status']=='Aangevraagd'),'Openstaande verlof- en verzuimverzoeken','shifts'),
    'inspections':('Kwaliteitsradar',cnt('inspections',lambda x:number(x['score'])<80),'Inspecties met score onder 80 (instelbare demo-grens)','logbook'),
    'logbook':('Communicatie-assistent',cnt('logbook',lambda x:x['status']=='Open'),'Openstaande logboekmeldingen','workorders'),
    'workorders':('Werkbonversneller',cnt('workorders',lambda x:x['status'] not in ('Afgerond','Geannuleerd')),'Nog niet afgeronde werkbonnen','hours'),
    'orders':('Inkoopwachtrij',cnt('orders',lambda x:x['status']=='Aangevraagd'),'Bestelaanvragen om te beoordelen','assets'),
    'assets':('Materieelcontrole',cnt('assets',lambda x:bool(x['inspection_date']) and x['inspection_date']<=str(datetime.date.today()+datetime.timedelta(days=30))),'Machinekeuringen binnen 30 dagen','orders'),
    'keys':('Sleutelbewaker',cnt('keys',lambda x:x['status']=='Uitgegeven'),'Uitgegeven sleutels; controleer houders','objects'),
    'vehicles':('Wagenparkcontrole',cnt('vehicles',lambda x:bool(x['inspection_date']) and x['inspection_date']<=str(datetime.date.today()+datetime.timedelta(days=30))),'Voertuiginspecties binnen 30 dagen','assets'),
    'documents':('Documentcontrole',cnt('documents',lambda x:x['status']!='Actief'),'Documenten zonder actieve status','contracts'),
    'alerts':('Actie-inbox',cnt('alerts',lambda x:x['status']=='Open'),'Openstaande operationele meldingen','logbook')}
   return self.respond({'widgets':{m:{'title':v[0],'count':v[1],'description':v[2],'next':v[3],'records':len(data[m])} for m,v in results.items()},'meta':{'mode':'Controleerbare SQL/regelgebaseerde inzichten','date':today,'notices':['Geen automatische SMS of e-mail','Geen echte salarisberekening of betalingen','Menselijke controle vereist']}})
  if path=='/api/sos/candidates' and method=='POST':
   b=self.body();shift_id=b.get('shift_id');c=conn()
   if not str(shift_id).isdigit():return self.respond({'error':'Kies een geldige dienst'},400)
   shift=c.execute('SELECT * FROM shifts WHERE id=?',(int(shift_id),)).fetchone()
   if not shift:return self.respond({'error':'Dienst niet gevonden'},404)
   if shift['status']=='Geannuleerd':return self.respond({'error':'Geannuleerde dienst'},400)
   people=[]
   for e in c.execute("SELECT * FROM employees WHERE status='Actief' ORDER BY name"):
    if str(e['id'])==str(shift['employee_id']):continue
    conflicts=c.execute("SELECT 1 FROM shifts WHERE employee_id=? AND date=? AND status!='Geannuleerd' AND start_time<? AND end_time>? LIMIT 1",(str(e['id']),shift['date'],shift['end_time'],shift['start_time'])).fetchone()
    if schedule_issues(c,{**dict(shift),'employee_id':str(e['id'])},shift['id']):continue
    people.append({'id':e['id'],'name':e['name'],'role':e['role'],'contract_hours':e['contract_hours'],'reason':'Overlap, verlof en geregistreerde beschikbaarheid gecontroleerd; bevestiging en reistijd handmatig controleren'})
   return self.respond({'shift':dict(shift),'candidates':people,'mode':'Databasefilter, geen AI-routeberekening of bevestigde beschikbaarheid'})
  if path=='/api/sos/assign' and method=='POST':
   b=self.body();sid=b.get('shift_id');eid=b.get('employee_id');c=conn()
   if not str(sid).isdigit() or not str(eid).isdigit():return self.respond({'error':'Ongeldige selectie'},400)
   c.execute('BEGIN IMMEDIATE')
   try:
    sh=c.execute('SELECT * FROM shifts WHERE id=?',(int(sid),)).fetchone()
    emp=c.execute("SELECT * FROM employees WHERE id=? AND status='Actief'",(int(eid),)).fetchone()
    if not sh or not emp or sh['status']=='Geannuleerd':c.rollback();return self.respond({'error':'Dienst of actieve medewerker ontbreekt'},400)
    conflict=c.execute("SELECT 1 FROM shifts WHERE id!=? AND employee_id=? AND date=? AND status!='Geannuleerd' AND start_time<? AND end_time>? LIMIT 1",(int(sid),str(eid),sh['date'],sh['end_time'],sh['start_time'])).fetchone()
    issues=schedule_issues(c,{**dict(sh),'employee_id':str(eid)},sh['id'])
    if issues:raise Problem(' '.join(issues),409)
    old=sh['employee_id'];c.execute("UPDATE shifts SET employee_id=?,status='Gepland',updated_at=CURRENT_TIMESTAMP WHERE id=?",(str(eid),int(sid)))
    log(user['username'],'sos_assign','shifts',int(sid),'Van medewerker '+str(old)+' naar '+str(eid))
    c.commit();return self.respond({'ok':True,'employee':emp['name'],'shift_id':int(sid),'sms_sent':False,'notice':'Dienst opgeslagen. Er is geen SMS verzonden; informeer de medewerker zelf.'})
   except Exception:c.rollback();raise
  if path=='/api/ai/analyze' and method=='POST':
   b=self.body();kind=b.get('type');c=conn();result=[]
   if kind=='planning':
    for sh in rows('shifts'):
     if not sh['employee_id']:result.append('Dienst #'+str(sh['id'])+' heeft nog geen medewerker.')
     if sh['start_time']>=sh['end_time']:result.append('Dienst #'+str(sh['id'])+' heeft ongeldige tijden.')
    if not result:result=['Alle geregistreerde diensten hebben een medewerker en geldige begin- en eindtijd.']
   elif kind=='finance':
    for inv in rows('invoices'):
     if inv['status']=='Open' and inv['due_date']<str(datetime.date.today()):result.append('Factuur '+inv['number']+' is over de vervaldatum.')
    if not result:result=['Geen vervallen openstaande facturen gevonden.']
   elif kind=='quality':
    for x in rows('inspections'):
     if number(x['score'])<80:result.append('Inspectie #'+str(x['id'])+' heeft een score onder 80.')
    if not result:result=['Geen geregistreerde kwaliteitsscores onder 80 gevonden.']
   elif kind=='operations':
    result=['Open werkbonnen: '+str(sum(x['status'] not in ('Afgerond','Geannuleerd') for x in rows('workorders'))),'Ingediende uren ter controle: '+str(sum(x['status']=='Ingediend' for x in rows('hours'))),'Open meldingen: '+str(sum(x['status']=='Open' for x in rows('alerts')))]
   else:return self.respond({'error':'Onbekende analyse'},400)
   log(user['username'],'analyze','ai',0,kind);c.commit();return self.respond({'type':kind,'findings':result,'mode':'Regelgebaseerde analyse op actuele databasegegevens; geen generatief AI-model.'})
  parts=path.strip('/').split('/')
  if len(parts) in (3,4) and parts[:2]==['api','records'] and parts[2] in MODULES:
   m=parts[2];fields=MODULES[m][1]
   if len(parts)==4 and not parts[3].isdigit():raise Problem('Ongeldig recordnummer.')
   rid=int(parts[3]) if len(parts)==4 else None
   if method=='GET':
    data=scoped_rows(c,m,user)
    if rid is not None:
     found=next((x for x in data if x['id']==rid),None)
     if found is None:raise Problem('Record niet gevonden.',404)
     return self.respond(found)
    return self.respond(data)
   if method not in ('POST','PUT','DELETE') or (method=='POST')!=(rid is None):raise Problem('Ongeldige methode.',405)
   if not admin and m not in ('hours','workorders','logbook','availability','leave'):raise Problem('Alleen inzage in deze module.',403)
   c.execute('BEGIN IMMEDIATE')
   previous=dict(c.execute('SELECT * FROM '+m+' WHERE id=?',(rid,)).fetchone() or {}) if rid else {}
   if rid and not previous:raise Problem('Record niet gevonden.',404)
   if previous and (previous.get('workflow') or previous.get('workorder_id')):raise Problem('Gebruik de gekoppelde werkopdrachtfunctie voor dit record.',409)
   if previous and self.headers.get('If-Match') is not None:
    from services.common import version
    version(previous,self.headers.get('If-Match').strip('"'))
   if not admin:
    visible={x['id'] for x in scoped_rows(c,m,user)}
    if rid and rid not in visible:raise Problem('Record niet gevonden.',404)
    if not user['employee_id']:raise Problem('Je account is nog niet aan een medewerker gekoppeld.',403)
    if m=='workorders' and method!='PUT':raise Problem('Alleen de voortgang van je eigen werkbon aanpassen.',403)
    if m=='logbook' and method!='POST':raise Problem('Alleen nieuwe logboekmeldingen toevoegen.',403)
    if m in ('hours','leave') and previous and previous['status'] not in ('Ingediend','Aangevraagd'):raise Problem('Deze registratie is al beoordeeld.',403)
   if method=='DELETE':
    protect_delete(c,m,rid,MODULES)
    c.execute('DELETE FROM '+m+' WHERE id=?',(rid,));log(user['username'],'delete',m,rid);c.commit();return self.respond({'ok':True})
   body=self.body()
   if not admin:
    if m in ('hours','availability','leave'):
     if 'employee_id' in body and str(body['employee_id'])!=str(user['employee_id']):raise Problem('Je kunt alleen eigen gegevens opslaan.',403)
     body['employee_id']=str(user['employee_id'])
    if m=='hours':
     if body.get('status','Ingediend')!='Ingediend':raise Problem('Alleen beheer kan uren goedkeuren.',403)
     body['status']='Ingediend'
    if m=='leave':
     if body.get('status','Aangevraagd')!='Aangevraagd':raise Problem('Alleen beheer kan verlof beoordelen.',403)
     body['status']='Aangevraagd'
    if m=='logbook':
     allowed={str(x['id']) for x in scoped_rows(c,'objects',user)}
     if str(body.get('object_id')) not in allowed:raise Problem('Geen toegang tot dit object.',403)
     body['author']=user['username'];body['status']='Open'
    if m=='workorders':
     if any(f not in ('status','hours','signed_by') for f in body):raise Problem('Alleen status, uren en aftekening aanpassen.',403)
     if previous['status'] in ('Afgerond','Geannuleerd'):raise Problem('Deze werkbon is gesloten.',403)
     if body.get('status',previous['status']) not in ('Nieuw','In behandeling','Afgerond'):raise Problem('Ongeldige werkbonstatus.',403)
   row=validate(c,m,body,fields,previous)
   if rid:
    c.execute('UPDATE '+m+' SET '+','.join(f+'=?' for f in fields)+',updated_at=CURRENT_TIMESTAMP WHERE id=?',[row[f] for f in fields]+[rid]);action='update'
   else:
    cur=c.execute('INSERT INTO '+m+'('+','.join(fields)+') VALUES('+','.join('?' for _ in fields)+')',[row[f] for f in fields]);rid=cur.lastrowid;action='create'
   if m in ('leave','availability'):
    from services.common import notify
    saved=c.execute('SELECT version FROM '+m+' WHERE id=?',(rid,)).fetchone()
    notify(c,f'{m}:{rid}:{saved[0]}','Beschikbaarheid gewijzigd; controleer de planning.','shifts',roles={'admin','company_admin','operations','planner'})
   log(user['username'],action,m,rid);c.commit();return self.respond({'ok':True,'id':rid},201 if method=='POST' else 200)
  return self.respond({'error':'Route niet gevonden'},404)
 def do_GET(self):self.handle_request('GET')
 def do_POST(self):self.handle_request('POST')
 def do_PUT(self):self.handle_request('PUT')
 def do_DELETE(self):self.handle_request('DELETE')
 def handle_request(self,m):
  self.connection.settimeout(15)
  try:self.route(m)
  except Problem as e:self.respond({'error':str(e)},e.status)
  except (ValueError,TypeError,KeyError,ArithmeticError):self.respond({'error':'Ongeldige invoer. Controleer de velden.'},400)
  except sqlite3.IntegrityError:self.respond({'error':'Deze gegevens conflicteren met een bestaande registratie.'},409)
  except sqlite3.OperationalError:logging.exception('Databasefout');self.respond({'error':'Database tijdelijk niet beschikbaar. Probeer opnieuw.'},503)
  except (BrokenPipeError,ConnectionResetError,TimeoutError):pass
  except Exception:logging.exception('Onverwachte serverfout');self.respond({'error':'Interne serverfout'},500)
  finally:
   if hasattr(CONN,'db'):
    if CONN.db.in_transaction:CONN.db.rollback()
    CONN.db.close();del CONN.db
 def log_message(self,*args):pass
if __name__=='__main__':
 init();synchronization.start_worker(DB,MODULES);print(f'ROEFS ONE: http://localhost:{PORT}');ThreadingHTTPServer((os.environ.get('ROEFS_HOST','127.0.0.1'),PORT),Handler).serve_forever()
