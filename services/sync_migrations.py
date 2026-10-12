"""Niet-destructieve migratie voor duurzame synchronisatie en artikelstamgegevens."""
def migrate(c):
    if c.execute('SELECT 1 FROM schema_migrations WHERE version=6').fetchone():return
    statements=[
      "CREATE TABLE articles(id INTEGER PRIMARY KEY,code TEXT NOT NULL UNIQUE,name TEXT NOT NULL,unit TEXT NOT NULL DEFAULT 'stuks',rate TEXT NOT NULL DEFAULT '0',vat_rate TEXT NOT NULL DEFAULT '21',status TEXT NOT NULL DEFAULT 'Actief',version INTEGER NOT NULL DEFAULT 1)",
      "CREATE TABLE sync_connections(id INTEGER PRIMARY KEY,name TEXT NOT NULL,provider TEXT NOT NULL DEFAULT 'generic',base_url TEXT NOT NULL DEFAULT '',secret_env TEXT NOT NULL DEFAULT '',enabled INTEGER NOT NULL DEFAULT 0,interval_seconds INTEGER NOT NULL DEFAULT 300,policies TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,next_run TEXT,last_run TEXT,last_success TEXT,last_error TEXT,failures INTEGER NOT NULL DEFAULT 0,lease_owner TEXT,lease_until TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP)",
      'CREATE TABLE sync_links(id INTEGER PRIMARY KEY,connection_id INTEGER NOT NULL REFERENCES sync_connections(id),category TEXT NOT NULL,external_id TEXT NOT NULL,local_id INTEGER NOT NULL,local_version INTEGER NOT NULL,remote_revision TEXT NOT NULL,remote_hash TEXT NOT NULL,UNIQUE(connection_id,category,external_id),UNIQUE(connection_id,category,local_id))',
      "CREATE TABLE sync_runs(id INTEGER PRIMARY KEY,connection_id INTEGER NOT NULL REFERENCES sync_connections(id),started_at TEXT NOT NULL,finished_at TEXT,status TEXT NOT NULL DEFAULT 'Bezig',imported INTEGER NOT NULL DEFAULT 0,exported INTEGER NOT NULL DEFAULT 0,conflicts INTEGER NOT NULL DEFAULT 0,error TEXT)",
      "CREATE TABLE sync_events(id INTEGER PRIMARY KEY,run_id INTEGER REFERENCES sync_runs(id),connection_id INTEGER NOT NULL REFERENCES sync_connections(id),category TEXT,local_id INTEGER,external_id TEXT,action TEXT NOT NULL,detail TEXT NOT NULL,at TEXT DEFAULT CURRENT_TIMESTAMP)",
      "CREATE TABLE sync_conflicts(id INTEGER PRIMARY KEY,connection_id INTEGER NOT NULL REFERENCES sync_connections(id),category TEXT NOT NULL,local_id INTEGER,external_id TEXT NOT NULL,remote_revision TEXT NOT NULL,remote_json TEXT NOT NULL,local_version INTEGER,reason TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'Open',resolution TEXT,resolved_by INTEGER REFERENCES users(id),created_at TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(connection_id,category,external_id,remote_revision,local_version))",
      "CREATE TABLE sync_outbox(id INTEGER PRIMARY KEY,connection_id INTEGER NOT NULL REFERENCES sync_connections(id),category TEXT NOT NULL,local_id INTEGER NOT NULL,local_version INTEGER NOT NULL,external_id TEXT,remote_revision TEXT,payload TEXT NOT NULL,idempotency_key TEXT NOT NULL UNIQUE,status TEXT NOT NULL DEFAULT 'Wacht',attempts INTEGER NOT NULL DEFAULT 0,last_error TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(connection_id,category,local_id,local_version))",
      'CREATE INDEX sync_due ON sync_connections(enabled,next_run)',
      'CREATE INDEX sync_open_conflicts ON sync_conflicts(connection_id,status)',
      'CREATE INDEX sync_outbox_pending ON sync_outbox(connection_id,status)',
    ]
    for statement in statements:c.execute(statement)
    if 'article_id' not in {r[1] for r in c.execute('PRAGMA table_info(orders)')}:c.execute('ALTER TABLE orders ADD COLUMN article_id INTEGER REFERENCES articles(id)')
    c.execute('INSERT INTO schema_migrations(version) VALUES(6)')
