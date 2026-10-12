"""Persistente accountbegrenzing en additieve beveiligingsmigratie."""
import time,os,datetime as dt
from domain import Problem

def migrate(c):
    c.execute('CREATE TABLE IF NOT EXISTS auth_attempts (username TEXT PRIMARY KEY, window_start REAL NOT NULL, attempts INTEGER NOT NULL)')
    if 'break_minutes' not in {r[1] for r in c.execute('PRAGMA table_info(shifts)')}:c.execute('ALTER TABLE shifts ADD COLUMN break_minutes INTEGER NOT NULL DEFAULT 0')
    c.execute("CREATE TABLE IF NOT EXISTS planning_series (id INTEGER PRIMARY KEY,title TEXT NOT NULL,definition TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,status TEXT NOT NULL DEFAULT 'Actief',snapshot TEXT NOT NULL DEFAULT '[]')")
    c.execute('CREATE TABLE IF NOT EXISTS planning_occurrences (series_id INTEGER NOT NULL REFERENCES planning_series(id),shift_id INTEGER NOT NULL UNIQUE REFERENCES shifts(id),PRIMARY KEY(series_id,shift_id))')
    initialize_scanning='scan_status' not in {r[1] for r in c.execute('PRAGMA table_info(files)')}
    for name,kind in [('scan_status',"TEXT NOT NULL DEFAULT 'Quarantaine'"),('scan_detail',"TEXT NOT NULL DEFAULT 'Bestaand bestand: opnieuw scannen.'"),('deleted_at','TEXT'),('version','INTEGER NOT NULL DEFAULT 1')]:
        if name not in {r[1] for r in c.execute('PRAGMA table_info(files)')}:c.execute('ALTER TABLE files ADD COLUMN '+name+' '+kind)
    if initialize_scanning:c.execute("UPDATE files SET scan_status='Tekstbijlage',scan_detail='Geen actieve inhoud; geen malwarescan uitgevoerd.' WHERE mime='text/plain' AND scan_status='Quarantaine'")
    c.execute("CREATE TABLE IF NOT EXISTS time_clocks(id INTEGER PRIMARY KEY,employee_id INTEGER NOT NULL REFERENCES employees(id),workorder_id INTEGER NOT NULL REFERENCES workorders(id),starts_at TEXT NOT NULL,created_by INTEGER NOT NULL REFERENCES users(id),state TEXT NOT NULL DEFAULT 'Actief',hours_id INTEGER REFERENCES hours(id),reason TEXT NOT NULL DEFAULT '',version INTEGER NOT NULL DEFAULT 1)")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS one_active_clock ON time_clocks(employee_id) WHERE state='Actief'")
    c.execute('CREATE TABLE IF NOT EXISTS invoice_sequences (series TEXT PRIMARY KEY,next_number INTEGER NOT NULL)')
    if 'contract_id' not in {r[1] for r in c.execute('PRAGMA table_info(workorders)')}:c.execute('ALTER TABLE workorders ADD COLUMN contract_id INTEGER REFERENCES contracts(id)')
    c.execute('CREATE TABLE IF NOT EXISTS contract_locations(contract_id INTEGER NOT NULL REFERENCES contracts(id),object_id INTEGER NOT NULL REFERENCES objects(id),frequency TEXT NOT NULL,PRIMARY KEY(contract_id,object_id))')
    c.execute('CREATE TABLE IF NOT EXISTS contract_events(id INTEGER PRIMARY KEY,contract_id INTEGER NOT NULL REFERENCES contracts(id),actor_id INTEGER NOT NULL REFERENCES users(id),action TEXT NOT NULL,reason TEXT NOT NULL,old_end TEXT,new_end TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
    c.execute('CREATE INDEX IF NOT EXISTS workorder_contract ON workorders(contract_id,date)')
    c.execute('CREATE TABLE IF NOT EXISTS sync_cursors(connection_id INTEGER NOT NULL REFERENCES sync_connections(id),category TEXT NOT NULL,cursor TEXT NOT NULL,PRIMARY KEY(connection_id,category))')
    c.execute('CREATE TABLE IF NOT EXISTS session_activity(token TEXT PRIMARY KEY REFERENCES sessions(token) ON DELETE CASCADE,last_seen REAL NOT NULL)')
    c.execute('INSERT OR IGNORE INTO schema_migrations(version) VALUES(9)')

def attempt(c,username):
    # Alleen bestaande accounts: voorkom onbegrensde opslag van verzonnen namen.
    c.execute('BEGIN IMMEDIATE')
    try:
        now=time.time()
        c.execute('DELETE FROM auth_attempts WHERE window_start<?',(now-300,))
        if c.execute('SELECT 1 FROM users WHERE username=?',(username,)).fetchone():
            row=c.execute('SELECT attempts FROM auth_attempts WHERE username=?',(username,)).fetchone()
            if row and row[0]>=10:raise Problem('Te veel inlogpogingen. Probeer over vijf minuten opnieuw.',429)
            c.execute('INSERT INTO auth_attempts VALUES(?,?,1) ON CONFLICT(username) DO UPDATE SET attempts=attempts+1',(username,now))
        c.commit()
    except Exception:c.rollback();raise


def session_active(c,token_hash):
    now=time.time();minutes=min(480,max(5,int(os.environ.get('ROEFS_SESSION_IDLE_MINUTES','30'))))
    row=c.execute('SELECT last_seen FROM session_activity WHERE token=?',(token_hash,)).fetchone()
    if row and now-row[0]>minutes*60:
        c.execute('DELETE FROM sessions WHERE token=?',(token_hash,));c.commit();return False
    if not row or now-row[0]>=60:
        c.execute('INSERT INTO session_activity VALUES(?,?) ON CONFLICT(token) DO UPDATE SET last_seen=excluded.last_seen',(token_hash,now));c.commit()
    return True
