"""Expliciete beheeracceptatie met bewijs en afhankelijkheden; nooit automatisch afvinken."""
import datetime as dt
from domain import Problem
from .common import text,version,audit
from .data_migration import admin
STEPS={
 'sources':('Bronsystemen vastgesteld',[]),
 'exports':('Bronexports ontvangen',['sources']),
 'validated':('Bronbestanden gevalideerd',['exports']),
 'mapping':('Mappingprofielen goedgekeurd',['validated']),
 'trial':('Testmigratie afgerond',['mapping']),
 'reconciliation':('Gegevensaansluiting goedgekeurd',['trial']),
 'workflows':('Operationele processen geaccepteerd',['reconciliation']),
 'accounting':('Boekhoudkoppeling geconfigureerd',['sources']),
 'final':('Definitieve migratie goedgekeurd',['workflows']),
 'golive':('Ingebruikname goedgekeurd',['final','accounting']),
}
def migrate(c):
 c.execute("CREATE TABLE IF NOT EXISTS onboarding_steps(key TEXT PRIMARY KEY,status TEXT NOT NULL DEFAULT 'Open',owner TEXT NOT NULL DEFAULT '',evidence TEXT NOT NULL DEFAULT '',completed_at TEXT,version INTEGER NOT NULL DEFAULT 1)")
 c.executemany('INSERT OR IGNORE INTO onboarding_steps(key) VALUES(?)',[(key,) for key in STEPS])
def listing(c):
 data={r['key']:dict(r) for r in c.execute('SELECT * FROM onboarding_steps')}
 return {'steps':[{**data[key],'label':label,'dependencies':deps,'blocked_by':[STEPS[d][0] for d in deps if data[d]['status']!='Goedgekeurd']} for key,(label,deps) in STEPS.items()]}
def save(c,user,key,body):
 admin(user)
 if key not in STEPS:raise Problem('Onbekende onboardingstap.',404)
 row=dict(c.execute('SELECT * FROM onboarding_steps WHERE key=?',(key,)).fetchone());version(row,body.get('version'))
 status=body.get('status');owner=text(body.get('owner',''),150);evidence=text(body.get('evidence',''),2000)
 if status not in ('Open','In uitvoering','Goedgekeurd'):raise Problem('Kies een geldige status.')
 if status=='Goedgekeurd':
  if not owner or not evidence:raise Problem('Goedkeuring vereist een verantwoordelijke en bewijs of referentie.')
  step=next(s for s in listing(c)['steps'] if s['key']==key)
  if step['blocked_by']:raise Problem('Eerst goedkeuren: '+', '.join(step['blocked_by']),409)
 c.execute('UPDATE onboarding_steps SET status=?,owner=?,evidence=?,completed_at=?,version=version+1 WHERE key=?',(status,owner,evidence,dt.datetime.now(dt.timezone.utc).isoformat() if status=='Goedgekeurd' else None,key))
 if row['status']=='Goedgekeurd' and status!='Goedgekeurd':
  invalid={key}
  for child,(label,deps) in STEPS.items():
   if invalid.intersection(deps):
    invalid.add(child);c.execute("UPDATE onboarding_steps SET status='Open',completed_at=NULL,version=version+1 WHERE key=?",(child,));audit(c,user,'onboarding_reopen','settings',0,child)
 audit(c,user,'onboarding_update','settings',0,key+': '+status);return listing(c)
