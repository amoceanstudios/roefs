"""Persistente accountbegrenzing en additieve beveiligingsmigratie."""
import time
from domain import Problem

def migrate(c):
    c.execute('CREATE TABLE IF NOT EXISTS auth_attempts (username TEXT PRIMARY KEY, window_start REAL NOT NULL, attempts INTEGER NOT NULL)')
    if 'break_minutes' not in {r[1] for r in c.execute('PRAGMA table_info(shifts)')}:c.execute('ALTER TABLE shifts ADD COLUMN break_minutes INTEGER NOT NULL DEFAULT 0')
    c.execute("CREATE TABLE IF NOT EXISTS planning_series (id INTEGER PRIMARY KEY,title TEXT NOT NULL,definition TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,status TEXT NOT NULL DEFAULT 'Actief',snapshot TEXT NOT NULL DEFAULT '[]')")
    c.execute('CREATE TABLE IF NOT EXISTS planning_occurrences (series_id INTEGER NOT NULL REFERENCES planning_series(id),shift_id INTEGER NOT NULL UNIQUE REFERENCES shifts(id),PRIMARY KEY(series_id,shift_id))')
    for name,kind in [('scan_status',"TEXT NOT NULL DEFAULT 'Quarantaine'"),('scan_detail',"TEXT NOT NULL DEFAULT 'Bestaand bestand: opnieuw scannen.'"),('deleted_at','TEXT'),('version','INTEGER NOT NULL DEFAULT 1')]:
        if name not in {r[1] for r in c.execute('PRAGMA table_info(files)')}:c.execute('ALTER TABLE files ADD COLUMN '+name+' '+kind)
    c.execute("UPDATE files SET scan_status='Tekstbijlage',scan_detail='Geen actieve inhoud; geen malwarescan uitgevoerd.' WHERE mime='text/plain' AND scan_status='Quarantaine'")
    c.execute("CREATE TABLE IF NOT EXISTS time_clocks(id INTEGER PRIMARY KEY,employee_id INTEGER NOT NULL REFERENCES employees(id),workorder_id INTEGER NOT NULL REFERENCES workorders(id),starts_at TEXT NOT NULL,created_by INTEGER NOT NULL REFERENCES users(id),state TEXT NOT NULL DEFAULT 'Actief',hours_id INTEGER REFERENCES hours(id),reason TEXT NOT NULL DEFAULT '',version INTEGER NOT NULL DEFAULT 1)")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS one_active_clock ON time_clocks(employee_id) WHERE state='Actief'")
    c.execute('CREATE TABLE IF NOT EXISTS invoice_sequences (series TEXT PRIMARY KEY,next_number INTEGER NOT NULL)')
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
