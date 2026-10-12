"""Optionele geauthenticeerde backupencryptie met cryptography.Fernet."""
import os,tempfile
from pathlib import Path

def fernet(keyfile):
    from cryptography.fernet import Fernet
    if keyfile.is_symlink() or not keyfile.is_file():raise ValueError('Sleutelbestand ontbreekt of is een symbolische link.')
    if os.name!='nt' and keyfile.stat().st_mode&0o077:raise ValueError('Sleutelbestand moet privé zijn (chmod 600).')
    return Fernet(keyfile.read_bytes().strip())

def generate(keyfile):
    from cryptography.fernet import Fernet
    fd=os.open(keyfile,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as out:out.write(Fernet.generate_key()+b'\n')

def backup(db,output,keyfile):
    from manage import backup as plain
    cipher=fernet(keyfile)
    if output.exists():raise ValueError('Uitvoer bestaat al.')
    with tempfile.TemporaryDirectory() as temp:
        archive=Path(temp)/'private.zip';plain(db,archive);encrypted=cipher.encrypt(archive.read_bytes())
        fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as out:out.write(encrypted)

def restore(archive,target,keyfile):
    from manage import restore as plain
    from cryptography.fernet import InvalidToken
    try:data=fernet(keyfile).decrypt(archive.read_bytes())
    except InvalidToken:raise ValueError('Verkeerde sleutel of beschadigde versleutelde backup.') from None
    with tempfile.TemporaryDirectory() as temp:
        decoded=Path(temp)/'private.zip';fd=os.open(decoded,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as out:out.write(data)
        plain(decoded,target)
