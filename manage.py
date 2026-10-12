#!/usr/bin/env python3
"""Maak een consistente private backup of herstel naar een NIEUWE projectdatamap."""
import argparse,hashlib,json,os,re,sqlite3,tempfile,zipfile
from pathlib import Path

def digest(data):return hashlib.sha256(data).hexdigest()
def check(db):
    with sqlite3.connect('file:'+str(db.resolve())+'?mode=ro',uri=True) as c:
        integrity=c.execute('PRAGMA integrity_check').fetchall();foreign=c.execute('PRAGMA foreign_key_check').fetchall()
        if integrity!=[('ok',)] or foreign:raise ValueError('Database-integriteitscontrole mislukt.')

def backup(db,output):
    if not db.is_file():raise ValueError('Database niet gevonden.')
    if output.exists():raise ValueError('Uitvoer bestaat al; kies een nieuwe naam.')
    with tempfile.TemporaryDirectory() as temp:
        snapshot=Path(temp)/'roefs.db'
        with sqlite3.connect('file:'+str(db.resolve())+'?mode=ro',uri=True) as source,sqlite3.connect(snapshot) as target:source.backup(target)
        check(snapshot);files={'roefs.db':snapshot.read_bytes()}
        with sqlite3.connect(snapshot) as c:
            if c.execute("SELECT 1 FROM sqlite_master WHERE name='files'").fetchone():
                for key,expected in c.execute('SELECT storage_key,sha256 FROM files'):
                    if not re.fullmatch('[a-f0-9]{64}',key):raise ValueError('Ongeldige bestandsreferentie.')
                    path=db.parent/'uploads'/key
                    if path.is_symlink():raise ValueError('Symbolische link in bestandsopslag.')
                    data=path.read_bytes()
                    if digest(data)!=expected:raise ValueError('Bestandsintegriteit mislukt.')
                    files['uploads/'+key]=data
        fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        try:
            with os.fdopen(fd,'wb') as stream,zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
                for name,data in files.items():archive.writestr(name,data)
                archive.writestr('backup-manifest.json',json.dumps({'format':1,'sha256':{name:digest(data) for name,data in files.items()}},indent=2))
        except Exception:output.unlink(missing_ok=True);raise

def restore(archive,target):
    if target.exists():raise ValueError('Herstelmap bestaat al. Gebruik een nieuwe, lege locatie; bestaande gegevens worden nooit overschreven.')
    with zipfile.ZipFile(archive) as source:
        names=source.namelist()
        if len(names)!=len(set(names)):raise ValueError('Dubbele archiefnamen.')
        if any(n not in ('roefs.db','backup-manifest.json') and not re.fullmatch('uploads/[a-f0-9]{64}',n) for n in names):raise ValueError('Onveilige of onbekende archiefpaden.')
        if sum(x.file_size for x in source.infolist())>1024**3:raise ValueError('Backup overschrijdt de herstelgrens van 1 GB.')
        manifest=json.loads(source.read('backup-manifest.json'))
        if manifest.get('format')!=1 or set(manifest.get('sha256',{}))!=set(names)-{'backup-manifest.json'}:raise ValueError('Ongeldig backupmanifest.')
        contents={n:source.read(n) for n in manifest['sha256']}
        if any(digest(data)!=manifest['sha256'][n] for n,data in contents.items()):raise ValueError('Backup-controlesom mislukt.')
    target.mkdir(mode=0o700,parents=True)
    try:
        for name,data in contents.items():
            path=target/name;path.parent.mkdir(mode=0o700,parents=True,exist_ok=True);fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'wb') as f:f.write(data)
        check(target/'roefs.db')
        # Herstelde koppelingen starten gepauzeerd; voorkom onbedoelde replay naar externe systemen.
        with sqlite3.connect(target/'roefs.db') as c:
            if c.execute("SELECT 1 FROM sqlite_master WHERE name='sync_connections'").fetchone():c.execute('UPDATE sync_connections SET enabled=0,lease_owner=NULL,lease_until=NULL')
            c.execute('DELETE FROM sessions')
    except Exception:
        import shutil
        shutil.rmtree(target);raise

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    b=sub.add_parser('backup');b.add_argument('--db',type=Path,default=Path('data/roefs.db'));b.add_argument('--output',type=Path,required=True)
    r=sub.add_parser('restore');r.add_argument('--archive',type=Path,required=True);r.add_argument('--target',type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.command=='backup':backup(args.db,args.output);print('Backup gemaakt en integriteit gecontroleerd. Bewaar dit bestand privé.')
        else:restore(args.archive,args.target);print('Hersteld en gecontroleerd. Sessies ingetrokken; externe koppelingen gepauzeerd.')
        return 0
    except (OSError,ValueError,sqlite3.Error,zipfile.BadZipFile,KeyError) as exc:print('Niet uitgevoerd:',exc);return 1
if __name__=='__main__':raise SystemExit(main())
