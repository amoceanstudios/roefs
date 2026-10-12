"""Additieve, transactionele migraties. De originele tabellen blijven bestaan."""
EXTRA={
 'customers':{'customer_number':'TEXT','billing_address':'TEXT','service_categories':'TEXT','notes':'TEXT'},
 'contracts':{'contract_number':'TEXT','renewal_date':'TEXT','frequency':'TEXT','service':'TEXT','manager_id':'INTEGER REFERENCES employees(id)'},
 'employees':{'department':'TEXT','team_id':'INTEGER','skills':'TEXT','region':'TEXT','emergency_available':'INTEGER NOT NULL DEFAULT 0'},
 'objects':{'region':'TEXT'},
 'workorders':{'workflow':'TEXT','priority':"TEXT DEFAULT 'Normaal'",'service':'TEXT','team_id':'INTEGER','required_skills':'TEXT','required_certifications':'TEXT','required_assets':'TEXT','capacity':'INTEGER DEFAULT 1','start_time':'TEXT','end_time':'TEXT','completion_notes':'TEXT','approved_by':'INTEGER REFERENCES users(id)'},
 'shifts':{'workorder_id':'INTEGER REFERENCES workorders(id)','planner_notes':'TEXT'},
 'hours':{'workorder_id':'INTEGER REFERENCES workorders(id)','starts_at':'TEXT','ends_at':'TEXT','break_minutes':'INTEGER','reason':'TEXT','approved_by':'INTEGER REFERENCES users(id)'},
 'assets':{'category':'TEXT','maintenance_date':'TEXT'},
 'vehicles':{'category':'TEXT','maintenance_date':'TEXT'},
 'invoices':{'net_amount':'TEXT','vat_amount':'TEXT','workorder_id':'INTEGER REFERENCES workorders(id)','review_status':'TEXT','credit_of':'INTEGER REFERENCES invoices(id)'},
}
def migrate(c,modules):
    c.execute('CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT DEFAULT CURRENT_TIMESTAMP)')
    if c.execute('SELECT 1 FROM schema_migrations WHERE version=5').fetchone():return
    for table in modules:
        columns={r[1] for r in c.execute('PRAGMA table_info('+table+')')}
        for name,kind in {'version':'INTEGER NOT NULL DEFAULT 1',**EXTRA.get(table,{})}.items():
            if name not in columns:c.execute(f'ALTER TABLE {table} ADD COLUMN {name} {kind}')
        c.execute(f'''CREATE TRIGGER IF NOT EXISTS version_{table} AFTER UPDATE ON {table}
          WHEN NEW.version=OLD.version BEGIN UPDATE {table} SET version=OLD.version+1 WHERE id=NEW.id; END''')
    statements=[
      'CREATE TABLE IF NOT EXISTS teams(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE,department TEXT NOT NULL DEFAULT \'\',version INTEGER NOT NULL DEFAULT 1)',
      'CREATE TABLE IF NOT EXISTS contacts(id INTEGER PRIMARY KEY,customer_id INTEGER NOT NULL REFERENCES customers(id),name TEXT NOT NULL,email TEXT,phone TEXT,notes TEXT,version INTEGER NOT NULL DEFAULT 1)',
      'CREATE TABLE IF NOT EXISTS certifications(id INTEGER PRIMARY KEY,employee_id INTEGER NOT NULL REFERENCES employees(id),name TEXT NOT NULL,expires_on TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,UNIQUE(employee_id,name))',
      'CREATE TABLE IF NOT EXISTS checklist(id INTEGER PRIMARY KEY,workorder_id INTEGER NOT NULL REFERENCES workorders(id),title TEXT NOT NULL,done INTEGER NOT NULL DEFAULT 0,done_by INTEGER REFERENCES users(id),done_at TEXT,version INTEGER NOT NULL DEFAULT 1)',
      'CREATE TABLE IF NOT EXISTS reservations(id INTEGER PRIMARY KEY,asset_id INTEGER NOT NULL REFERENCES assets(id),workorder_id INTEGER NOT NULL REFERENCES workorders(id),date TEXT NOT NULL,start_time TEXT NOT NULL,end_time TEXT NOT NULL,UNIQUE(asset_id,workorder_id))',
      'CREATE TABLE IF NOT EXISTS workorder_events(id INTEGER PRIMARY KEY,workorder_id INTEGER NOT NULL REFERENCES workorders(id),actor_id INTEGER NOT NULL REFERENCES users(id),old_state TEXT,new_state TEXT,reason TEXT,at TEXT DEFAULT CURRENT_TIMESTAMP)',
      'CREATE TABLE IF NOT EXISTS schedule_history(id INTEGER PRIMARY KEY,shift_id INTEGER NOT NULL REFERENCES shifts(id),actor_id INTEGER NOT NULL REFERENCES users(id),before_json TEXT NOT NULL,after_version INTEGER NOT NULL,undone INTEGER NOT NULL DEFAULT 0,at TEXT DEFAULT CURRENT_TIMESTAMP)',
      'CREATE TABLE IF NOT EXISTS invoice_lines(id INTEGER PRIMARY KEY,invoice_id INTEGER NOT NULL REFERENCES invoices(id),description TEXT NOT NULL,quantity TEXT NOT NULL,rate TEXT NOT NULL,vat_rate TEXT NOT NULL,net TEXT NOT NULL,vat TEXT NOT NULL)',
      'CREATE TABLE IF NOT EXISTS files(id INTEGER PRIMARY KEY,name TEXT NOT NULL,storage_key TEXT NOT NULL UNIQUE,mime TEXT NOT NULL,size INTEGER NOT NULL,sha256 TEXT NOT NULL,category TEXT NOT NULL,customer_id INTEGER REFERENCES customers(id),employee_id INTEGER REFERENCES employees(id),workorder_id INTEGER REFERENCES workorders(id),created_by INTEGER NOT NULL REFERENCES users(id),created_at TEXT DEFAULT CURRENT_TIMESTAMP,retention_until TEXT)',
      'CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),event_key TEXT NOT NULL,title TEXT NOT NULL,target TEXT NOT NULL,read_at TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(user_id,event_key))',
      'CREATE TABLE IF NOT EXISTS preferences(user_id INTEGER PRIMARY KEY REFERENCES users(id),tour_step INTEGER NOT NULL DEFAULT 0,tour_completed INTEGER NOT NULL DEFAULT 0,notifications INTEGER NOT NULL DEFAULT 1)',
      'CREATE TABLE IF NOT EXISTS travel_estimates(id INTEGER PRIMARY KEY,from_object INTEGER NOT NULL REFERENCES objects(id),to_object INTEGER NOT NULL REFERENCES objects(id),minutes INTEGER NOT NULL CHECK(minutes>=0),source TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,UNIQUE(from_object,to_object))',
      "CREATE UNIQUE INDEX IF NOT EXISTS unique_billed_workorder ON invoices(workorder_id) WHERE workorder_id IS NOT NULL AND credit_of IS NULL",
      "CREATE UNIQUE INDEX IF NOT EXISTS customer_number_unique ON customers(customer_number) WHERE customer_number IS NOT NULL AND customer_number!=''",
      'CREATE INDEX IF NOT EXISTS workorder_shifts ON shifts(workorder_id)',
      'CREATE INDEX IF NOT EXISTS workorder_hours ON hours(workorder_id)',
      'CREATE INDEX IF NOT EXISTS notification_user ON notifications(user_id,read_at)',
      'CREATE INDEX IF NOT EXISTS reservation_period ON reservations(asset_id,date,start_time,end_time)',
    ]
    for statement in statements:c.execute(statement)
    c.execute('INSERT INTO schema_migrations(version) VALUES(5)')
