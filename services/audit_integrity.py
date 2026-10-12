"""Controleketen voor auditrecords; anker extern bewaren voor detectie van truncatie."""
import hashlib,json

def digest(previous,row):return hashlib.sha256((previous+'\n'+json.dumps(list(row),ensure_ascii=False,separators=(',',':'))).encode()).hexdigest()
def migrate(c):
    existed=c.execute("SELECT 1 FROM sqlite_master WHERE name='audit_chain'").fetchone()
    c.execute('CREATE TABLE IF NOT EXISTS audit_chain (audit_id INTEGER PRIMARY KEY,previous TEXT NOT NULL,digest TEXT NOT NULL)')
    if not existed:
        previous='0'*64
        for row in c.execute('SELECT id,actor,action,module,record_id,detail,at FROM audit ORDER BY id').fetchall():
            value=digest(previous,row);c.execute('INSERT INTO audit_chain VALUES(?,?,?)',(row[0],previous,value));previous=value

def append(c,actor,action,module,rid,detail,at):
    cursor=c.execute('INSERT INTO audit(actor,action,module,record_id,detail,at) VALUES(?,?,?,?,?,?)',(actor,action,module,rid,detail,at))
    last=c.execute('SELECT digest FROM audit_chain ORDER BY audit_id DESC LIMIT 1').fetchone();previous=last[0] if last else '0'*64
    aid=cursor.lastrowid;value=digest(previous,(aid,actor,action,module,rid,detail,at));c.execute('INSERT INTO audit_chain VALUES(?,?,?)',(aid,previous,value))

def verify(c):
    previous='0'*64;count=0
    rows=c.execute('SELECT id,actor,action,module,record_id,detail,at FROM audit ORDER BY id').fetchall()
    chain={r[0]:(r[1],r[2]) for r in c.execute('SELECT * FROM audit_chain')}
    for row in rows:
        expected=digest(previous,row)
        if chain.get(row[0])!=(previous,expected):return {'ok':False,'record_id':row[0],'checked':count,'error':'Auditrecord of controleketen gewijzigd.'}
        previous=expected;count+=1
    if count!=len(chain):return {'ok':False,'checked':count,'error':'Auditrecords ontbreken.'}
    return {'ok':True,'checked':count,'anchor':previous,'limitation':'Bewaar dit anker extern. Iemand met volledige databasecontrole kan beide tabellen herschrijven; dit is geen onveranderbaar extern auditarchief.'}
