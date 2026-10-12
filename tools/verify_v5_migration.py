#!/usr/bin/env python3
"""Valideer een V5-bronmap → huidige migratie met uitsluitend tijdelijke demo-opslag."""
import argparse,json,os,sqlite3,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def initialize(source,db):
 subprocess.run([sys.executable,'-c','import server; server.init()'],cwd=source,env={**os.environ,'ROEFS_DB':str(db),'ROEFS_ADMIN_PASSWORD':'FictieveMigratie12!','ROEFS_EMPLOYEE_PASSWORD':'FictieveMedewerker12!'},check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
def snapshot(db):
 with sqlite3.connect(db) as c:
  tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
  return {table:([r[1] for r in c.execute('PRAGMA table_info("'+table+'")')],c.execute('SELECT * FROM "'+table+'" ORDER BY rowid').fetchall()) for table in tables}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--report',type=Path,required=True);args=p.parse_args()
 with tempfile.TemporaryDirectory(prefix='roefs-v5-migration-') as temp:
  db=Path(temp)/'demo.db';initialize(args.baseline,db)
  with sqlite3.connect(db) as c:c.execute("INSERT INTO customers(name,status) VALUES('Fictieve migratieklant','Actief')")
  before=snapshot(db);initialize(ROOT,db)
  preserved=[]
  with sqlite3.connect(db) as c:
   for table,(columns,rows) in before.items():
    if table=='schema_migrations':continue
    actual=c.execute('SELECT '+','.join('"'+x+'"' for x in columns)+' FROM "'+table+'" ORDER BY rowid').fetchall()
    if actual!=rows:raise AssertionError('Bestaande waarden gewijzigd: '+table)
    preserved.append({'table':table,'rows':len(rows),'columns':len(columns)})
   assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
   assert c.execute('PRAGMA foreign_key_check').fetchall()==[]
  migrated=snapshot(db);initialize(ROOT,db);assert snapshot(db)==migrated,'Herhaalde initialisatie verandert gegevens'
  result={'source':'V5 demo-initialisatie','target':'huidige broncode','preserved':preserved,'integrity_check':'ok','foreign_key_errors':0,'repeatable':True,'production_data_used':False}
  args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,indent=2)+'\n');print('PASS: '+str(len(preserved))+' bestaande tabellen behouden; integriteit, foreign keys en herhaalde migratie gecontroleerd.')
if __name__=='__main__':main()
