#!/usr/bin/env python3
"""Start de bestaande Python-app lokaal of met een gratis tijdelijke Cloudflare Tunnel."""
import argparse,base64,datetime,json,os,secrets,shutil,signal,sqlite3,subprocess,sys,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def private_write(path,text):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:f.write(text)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tunnel',action='store_true',help='Start een tijdelijke Cloudflare-link met extra toegangswachtwoord')
    parser.add_argument('--check',action='store_true',help='Start, controleer HTTP en database en sluit af')
    parser.add_argument('--quiet',action='store_true',help='Toon geen inloggegevens in de uitvoer')
    args=parser.parse_args()
    if sys.version_info<(3,10):parser.error('Python 3.10 of nieuwer is vereist.')
    env=os.environ.copy();env['ROEFS_INSTANCE_ID']=secrets.token_hex(16);env.setdefault('PORT','8765');env.setdefault('ROEFS_HOST','127.0.0.1');env.setdefault('ROEFS_DB',str(ROOT/'data'/'roefs.db'))
    db=Path(env['ROEFS_DB']).resolve();db.parent.mkdir(parents=True,exist_ok=True)
    if os.name!='nt':db.parent.chmod(0o700)
    credentials=db.parent/'demo-accounts.json';fresh=not db.exists()
    if fresh and not credentials.exists():
        private_write(credentials,json.dumps({'ROEFS_ADMIN_PASSWORD':env.get('ROEFS_ADMIN_PASSWORD') or secrets.token_urlsafe(18),'ROEFS_EMPLOYEE_PASSWORD':env.get('ROEFS_EMPLOYEE_PASSWORD') or secrets.token_urlsafe(18)},indent=2))
    if credentials.exists():
        stored=json.loads(credentials.read_text())
        for name in ('ROEFS_ADMIN_PASSWORD','ROEFS_EMPLOYEE_PASSWORD'):env.setdefault(name,stored[name])
    if db.exists():
        # SQLite backup neemt ook reeds gecommitteerde WAL-inhoud mee.
        backup_dir=db.parent/'backups';backup_dir.mkdir(exist_ok=True)
        backup=backup_dir/('roefs-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.db')
        with sqlite3.connect(db) as source,sqlite3.connect(backup) as target:source.backup(target)
        if os.name!='nt':backup.chmod(0o600)
        print('Reservekopie gemaakt in',backup_dir)
    cloudflared=None
    if args.tunnel:
        cloudflared=os.environ.get('CLOUDFLARED_BIN') or shutil.which('cloudflared')
        if not cloudflared:parser.error('Installeer cloudflared: op macOS met brew install cloudflared; zie INSTALLATIE.md voor andere systemen.')
        gatefile=ROOT/'.demo_gate'
        if not env.get('ROEFS_DEMO_GATE'):
            if not gatefile.exists():private_write(gatefile,secrets.token_urlsafe(24))
            env['ROEFS_DEMO_GATE']=gatefile.read_text().strip()
        env['ROEFS_HOST']='127.0.0.1'
    gate=env.get('ROEFS_DEMO_GATE','');headers={}
    if gate:headers['Authorization']='Basic '+base64.b64encode(('demo:'+gate).encode()).decode()
    host='127.0.0.1' if env['ROEFS_HOST'] in ('127.0.0.1','0.0.0.0') else env['ROEFS_HOST']
    url=f"http://{host}:{env['PORT']}"
    children=[]
    def interrupted(*_):raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,interrupted)
    try:
        server=subprocess.Popen([sys.executable,'-u',str(ROOT/'server.py')],cwd=ROOT,env=env);children.append(server)
        for _ in range(100):
            if server.poll() is not None:raise RuntimeError('Server kon niet starten. Controleer of de poort vrij is.')
            try:
                with urllib.request.urlopen(urllib.request.Request(url+'/api/health',headers=headers),timeout=1) as r:
                    status=json.load(r)
                if status.get('ok') and status.get('instance')!=env['ROEFS_INSTANCE_ID']:
                    raise RuntimeError('Poort is bezet door een andere server. Kies een andere PORT.')
                if status.get('ok'):
                    with urllib.request.urlopen(urllib.request.Request(url+'/',headers=headers),timeout=1) as r:assert b'ROEFS ONE' in r.read()
                    # Ook bevestigen dat onze eigen server nog draait.
                    time.sleep(.1)
                    if server.poll() is not None:raise RuntimeError('Poort al in gebruik.')
                    break
            except (OSError,ValueError):time.sleep(.1)
        else:raise RuntimeError('Server reageert niet op de gereedheidscontrole.')
        print('Gereed: Python-server, database en startpagina gecontroleerd.',flush=True)
        if not args.quiet:
            if fresh or credentials.exists():
                print('Fictieve demoaccounts (bewaar deze gegevens privé):')
                print('Roefs /',env['ROEFS_ADMIN_PASSWORD'])
                print('Bart van Aalde /',env['ROEFS_EMPLOYEE_PASSWORD'])
                if not fresh:print('Bij een eerder gebruikte database blijven de bestaande wachtwoorden van kracht.')
            else:print('Bestaande database: gebruik de bestaande accountwachtwoorden.')
            if gate:print('Extra linkbeveiliging: gebruikersnaam demo / wachtwoord',gate)
        if args.check:return 0
        if args.tunnel:
            print('Cloudflare maakt een tijdelijke HTTPS-link. Houd dit venster open; stoppen met Ctrl+C.',flush=True)
            tunnel=subprocess.Popen([cloudflared,'tunnel','--no-autoupdate','--url',url],cwd=ROOT);children.append(tunnel)
        else:print('Lokaal openen:',url,'— stoppen met Ctrl+C.',flush=True)
        while True:
            for proc in children:
                if proc.poll() is not None:raise RuntimeError('Een server- of tunnelproces is gestopt (code '+str(proc.returncode)+').')
            time.sleep(.25)
    except KeyboardInterrupt:return 0
    except Exception as e:print('Starten mislukt:',e,file=sys.stderr);return 1
    finally:
        for proc in reversed(children):
            if proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
        if db.exists() and os.name!='nt':db.chmod(0o600)
if __name__=='__main__':sys.exit(main())
