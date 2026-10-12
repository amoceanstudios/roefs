#!/usr/bin/env python3
"""Voer controles uit en bewaar de ongewijzigde uitvoer; fouten geven een niet-nul exitcode."""
import argparse,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--backend-only',action='store_true');p.add_argument('--load',action='store_true');args=p.parse_args()
commands=[('legacy-api',[sys.executable,'test_api.py']),('legacy-planning',[sys.executable,'test_planning.py']),('logo',[sys.executable,'TEST-HERSTEL.py'])]
if args.backend_only:
 commands.extend((name,[sys.executable,'-m','unittest','discover','-s','tests','-p',name+'.py','-v']) for name in ('test_regression','test_startup','test_enterprise','test_sync','test_security_recovery','test_v6_security','test_v6_planning','test_v6_integrity','test_v6_operations','test_v6_http','test_v6_scopes'))
else:commands.append(('all-tests',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_*.py','-v']))
if args.load:commands.extend([('load-smoke',[sys.executable,'tests/load_smoke.py']),('load-enterprise',[sys.executable,'tests/load_enterprise.py'])])
(ROOT/'reports').mkdir(exist_ok=True);failed=[]
for name,command in commands:
 print('\nControle:',name,flush=True)
 run=subprocess.run(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (ROOT/'reports'/(name+'.txt')).write_text(run.stdout)
 print(run.stdout,flush=True)
 if run.returncode:failed.append(name)
print('Mislukt: '+', '.join(failed) if failed else 'Alle geselecteerde controles geslaagd.')
if args.backend_only:print('Browsertests niet uitgevoerd (--backend-only).')
sys.exit(1 if failed else 0)
