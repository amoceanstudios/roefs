def migrate(c):
    if c.execute('SELECT 1 FROM schema_migrations WHERE version=8').fetchone():return
    c.execute("CREATE TABLE communications(id INTEGER PRIMARY KEY,customer_id INTEGER NOT NULL REFERENCES customers(id),date TEXT NOT NULL,subject TEXT NOT NULL,notes TEXT NOT NULL DEFAULT '',version INTEGER NOT NULL DEFAULT 1)")
    c.execute('CREATE TABLE sync_resolution_snapshots(id INTEGER PRIMARY KEY,conflict_id INTEGER NOT NULL REFERENCES sync_conflicts(id),local_json TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
    for table in ('workorders','hours','availability'):c.execute(f'CREATE INDEX IF NOT EXISTS v5_{table}_date ON {table}(date)')
    c.execute('CREATE INDEX IF NOT EXISTS v5_objects_customer ON objects(customer_id)')
    c.execute('INSERT INTO schema_migrations(version) VALUES(8)')
