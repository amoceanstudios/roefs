"""Additieve doelmodellen; dezelfde werkruimte en rechten als hun bovenliggende module."""
from domain import Problem
from .common import text,record,money
MODELS={
 'rooms':('Ruimtes','objects',['object_id','name','floor','area','status']),
 'service_types':('Diensttypes','contracts',['name','description','status']),
 'work_programs':("Werkprogramma's",'contracts',['object_id','contract_id','service_type_id','name','frequency','status']),
 'work_instructions':('Werkinstructies','workorders',['program_id','room_id','name','instructions','status']),
}
REFS={'object_id':'objects','contract_id':'contracts','service_type_id':'service_types','program_id':'work_programs','room_id':'rooms'}
REQUIRED={'rooms':['object_id','name'],'service_types':['name'],'work_programs':['object_id','name'],'work_instructions':['program_id','name','instructions']}

def migrate(c):
 for table,(_,permission,fields) in MODELS.items():
  cols=['id INTEGER PRIMARY KEY','version INTEGER NOT NULL DEFAULT 1']
  for field in fields:cols.append(field+(' INTEGER REFERENCES '+REFS[field]+'(id)' if field in REFS else " TEXT NOT NULL DEFAULT ''"))
  c.execute('CREATE TABLE IF NOT EXISTS '+table+'('+','.join(cols)+')')
  for field in fields:
   if field in REFS:c.execute('CREATE INDEX IF NOT EXISTS idx_'+table+'_'+field+' ON '+table+'('+field+')')

def validate(c,table,row):
 for field in REQUIRED[table]:text(row.get(field,''),2000,True)
 for field,parent in REFS.items():
  if field in row:
   row[field]=int(row[field]) if row[field] else None
   if row[field]:record(c,parent,row[field])
 row['status']=row.get('status') or 'Actief'
 if row['status'] not in ('Actief','Inactief'):raise Problem('Kies Actief of Inactief.')
 if table=='rooms' and row.get('area'):row['area']=str(money(row['area']))
 if table=='work_programs' and row['contract_id']:
  contract=record(c,'contracts',row['contract_id']);obj=record(c,'objects',row['object_id'])
  if str(contract['customer_id'])!=str(obj['customer_id']) or (str(contract['object_id'])!=str(obj['id']) and not c.execute('SELECT 1 FROM contract_locations WHERE contract_id=? AND object_id=?',(contract['id'],obj['id'])).fetchone()):raise Problem('Werkprogramma en contract moeten bij dezelfde contractlocatie horen.',409)
 if table=='work_instructions' and row['room_id']:
  if record(c,'rooms',row['room_id'])['object_id']!=int(record(c,'work_programs',row['program_id'])['object_id']):raise Problem('Ruimte hoort niet bij de locatie van dit werkprogramma.',409)
 return row
