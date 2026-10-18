"""Optionele TOTP (RFC 6238), inschakelen na wachtwoord én actuele code."""
import base64,hashlib,hmac,secrets,struct,time,urllib.parse
from domain import Problem
from .common import audit

def code(secret,counter):
    key=base64.b32decode(secret+'='*((8-len(secret)%8)%8));mac=hmac.new(key,struct.pack('>Q',counter),hashlib.sha1).digest();offset=mac[-1]&15
    return str((struct.unpack('>I',mac[offset:offset+4])[0]&0x7fffffff)%1000000).zfill(6)
def verify(secret,supplied,last=-1):
    if not isinstance(supplied,str) or len(supplied)!=6 or not supplied.isdigit():raise Problem('Vul een geldige verificatiecode in.',401)
    current=int(time.time()//30)
    for counter in (current,current-1,current+1):
        if counter>last and hmac.compare_digest(code(secret,counter),supplied):return counter
    raise Problem('Verificatiecode ongeldig, verlopen of al gebruikt.',401)
def migrate(c):
    c.execute('CREATE TABLE IF NOT EXISTS mfa_recovery_codes (user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, digest TEXT NOT NULL, used_at TEXT, PRIMARY KEY(user_id,digest))')
    if c.execute('SELECT 1 FROM schema_migrations WHERE version=7').fetchone():return
    for field,kind in [('mfa_secret','TEXT'),('mfa_pending','TEXT'),('mfa_counter','INTEGER NOT NULL DEFAULT -1'),('password_iterations','INTEGER NOT NULL DEFAULT 250000')]:
        if field not in {r[1] for r in c.execute('PRAGMA table_info(users)')}:c.execute(f'ALTER TABLE users ADD COLUMN {field} {kind}')
    c.execute('INSERT INTO schema_migrations(version) VALUES(7)')
def route(c,user,action,body):
    row=c.execute('SELECT * FROM users WHERE id=?',(user['id'],)).fetchone()
    if action=='status':return {'enabled':bool(row['mfa_secret']),'recovery_remaining':c.execute('SELECT COUNT(*) FROM mfa_recovery_codes WHERE user_id=? AND used_at IS NULL',(user['id'],)).fetchone()[0]}
    password=str(body.get('password',''))
    expected=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(row['salt']),row['password_iterations']).hex()
    if not hmac.compare_digest(expected,row['password_hash']):raise Problem('Huidig wachtwoord onjuist.',403)
    if action=='setup':
        if row['mfa_secret']:raise Problem('Verificatie in twee stappen is al ingeschakeld.',409)
        secret=base64.b32encode(secrets.token_bytes(20)).decode().rstrip('=');c.execute('UPDATE users SET mfa_pending=? WHERE id=?',(secret,user['id']));audit(c,user,'mfa_setup','users',user['id']);return {'secret':secret,'uri':'otpauth://totp/'+urllib.parse.quote('AMOCEAN INTEL:'+user['username'])+'?secret='+secret+'&issuer=AMOCEAN%20INTEL&algorithm=SHA1&digits=6&period=30'}
    if action=='enable':
        if not row['mfa_pending']:raise Problem('Start eerst de configuratie.')
        counter=verify(row['mfa_pending'],body.get('code',''));c.execute('UPDATE users SET mfa_secret=mfa_pending,mfa_pending=NULL,mfa_counter=? WHERE id=?',(counter,user['id']))
    elif action=='recovery':
        if not row['mfa_secret']:raise Problem('Activeer eerst verificatie in twee stappen.',409)
        counter=verify(row['mfa_secret'],body.get('code',''),row['mfa_counter'])
        c.execute('UPDATE users SET mfa_counter=? WHERE id=?',(counter,user['id']))
        codes=generate_recovery(c,user['id']);audit(c,user,'mfa_recovery_rotated','users',user['id'])
        c.execute('DELETE FROM sessions WHERE user_id=?',(user['id'],))
        return {'recovery_codes':codes,'relogin_required':True}
    elif action=='disable':
        if not row['mfa_secret']:raise Problem('Verificatie in twee stappen is niet actief.')
        verify(row['mfa_secret'],body.get('code',''),row['mfa_counter']);c.execute('UPDATE users SET mfa_secret=NULL,mfa_pending=NULL,mfa_counter=-1 WHERE id=?',(user['id'],))
    else:raise Problem('Onbekende beveiligingshandeling.',404)
    codes=generate_recovery(c,user['id']) if action=='enable' else []
    if action=='disable':c.execute('DELETE FROM mfa_recovery_codes WHERE user_id=?',(user['id'],))
    c.execute('DELETE FROM sessions WHERE user_id=?',(user['id'],));audit(c,user,'mfa_'+action,'users',user['id']);return {'ok':True,'relogin_required':True,'recovery_codes':codes}


def recovery_digest(user_id,value):
    # 128-bit randomly generated codes; SHA-256 is sufficient for this entropy.
    return hashlib.sha256(('roefs-recovery:'+str(user_id)+':'+value.strip().lower().replace('-','')).encode()).hexdigest()

def generate_recovery(c,user_id):
    c.execute('DELETE FROM mfa_recovery_codes WHERE user_id=?',(user_id,))
    codes=['-'.join([value[i:i+8] for i in range(0,32,8)]) for value in [secrets.token_hex(16) for _ in range(10)]]
    c.executemany('INSERT INTO mfa_recovery_codes(user_id,digest) VALUES(?,?)',[(user_id,recovery_digest(user_id,x)) for x in codes])
    return codes

def authenticate(c,user,supplied):
    if isinstance(supplied,str) and len(supplied.strip()) in (32,35):
        changed=c.execute("UPDATE mfa_recovery_codes SET used_at=CURRENT_TIMESTAMP WHERE user_id=? AND digest=? AND used_at IS NULL",(user['id'],recovery_digest(user['id'],supplied))).rowcount
        if changed!=1:raise Problem('Herstelcode ongeldig of al gebruikt.',401)
        c.execute('DELETE FROM sessions WHERE user_id=?',(user['id'],))
        audit(c,user,'mfa_recovery_used','users',user['id'])
        return 'recovery'
    counter=verify(user['mfa_secret'],supplied,user['mfa_counter'])
    c.execute('UPDATE users SET mfa_counter=? WHERE id=?',(counter,user['id']))
    return 'totp'
