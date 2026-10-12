import datetime as dt,json
from decimal import Decimal,InvalidOperation,ROUND_HALF_UP
from domain import Problem,date_value

def record(c,table,rid):
    r=c.execute('SELECT * FROM '+table+' WHERE id=?',(rid,)).fetchone()
    if not r:raise Problem('Gegevens niet gevonden.',404)
    return dict(r)
def version(row,expected):
    if expected is None:raise Problem('Versienummer ontbreekt. Vernieuw de gegevens.',428)
    if str(row['version'])!=str(expected):raise Problem('Een andere gebruiker heeft deze gegevens gewijzigd. Vernieuw en beoordeel de wijziging.',409)
def text(value,maxlen=2000,required=False):
    if not isinstance(value,(str,int,float)) or isinstance(value,bool):raise Problem('Verwacht tekst of een getal.')
    value=str(value).strip()
    if len(value)>maxlen or (required and not value):raise Problem('Vul de verplichte velden in binnen de aangegeven lengte.')
    return value
def money(value,allow_negative=False):
    try:n=Decimal(str(value).replace(',','.'))
    except InvalidOperation:raise Problem('Ongeldig bedrag.')
    if not n.is_finite() or abs(n)>100000000 or (n<0 and not allow_negative):raise Problem('Bedrag buiten bereik.')
    return n
def eur(value):return str(value.quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
def words(value):return {s.strip().casefold() for s in str(value or '').split(',') if s.strip()}
def audit(c,user,action,module,rid,detail=''):
    from .audit_integrity import append
    append(c,user['username'],action,module,rid,text(detail,10000),dt.datetime.now(dt.timezone.utc).isoformat())
def update(c,table,rid,values):
    c.execute('UPDATE '+table+' SET '+','.join(k+'=?' for k in values)+' WHERE id=?',list(values.values())+[rid])
def insert(c,table,values):
    return c.execute('INSERT INTO '+table+'('+','.join(values)+') VALUES('+','.join('?' for _ in values)+')',list(values.values())).lastrowid
def notify(c,event,title,target,employee_id=None,roles=None):
    for u in c.execute('SELECT id,role,employee_id FROM users WHERE active=1').fetchall():
        if employee_id is not None and str(u['employee_id'])!=str(employee_id):continue
        if roles is not None and u['role'] not in roles:continue
        pref=c.execute('SELECT notifications FROM preferences WHERE user_id=?',(u['id'],)).fetchone()
        if pref and not pref[0]:continue
        c.execute('INSERT OR IGNORE INTO notifications(user_id,event_key,title,target) VALUES(?,?,?,?)',(u['id'],event,title,target))
