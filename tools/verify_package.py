#!/usr/bin/env python3
"""Pak een bronpakket veilig uit, controleer manifest en test in een nieuwe venv."""
import argparse,hashlib,json,os,subprocess,sys,tempfile,zipfile
from pathlib import Path,PurePosixPath

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('archive',type=Path);p.add_argument('--report',type=Path,required=True);args=p.parse_args();archive=args.archive.resolve();report=args.report.resolve();report.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='roefs-package-check-') as temp:
  temp=Path(temp)
  with zipfile.ZipFile(archive) as z:
   names=z.namelist();assert len(names)==len(set(names)),'Dubbele archiefnamen'
   assert sum(x.file_size for x in z.infolist())<200_000_000,'Pakket te groot'
   for item in z.infolist():
    path=PurePosixPath(item.filename)
    assert not path.is_absolute() and '..' not in path.parts and '\\' not in item.filename,'Onveilig archiefpad'
    assert not (item.external_attr>>16)&0o170000==0o120000,'Symbolische link'
    assert not {'.git','.env','data','node_modules','__pycache__'}&set(path.parts),'Private/runtime-inhoud'
    assert path.suffix not in ('.db','.pyc','.zip'), 'Runtime/nested archive'
   roots={PurePosixPath(x).parts[0] for x in names};assert len(roots)==1,'Meerdere projectmappen';z.extractall(temp)
  root=temp/roots.pop();manifest=json.loads((root/'MANIFEST.json').read_text());listed={x['path'] for x in manifest['files']};actual={str(x.relative_to(root)) for x in root.rglob('*') if x.is_file()}-{'MANIFEST.json'};assert listed==actual,'Manifestlijst wijkt af'
  for item in manifest['files']:
   data=(root/item['path']).read_bytes();assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256'],'Manifest-hash wijkt af: '+item['path']
  venv=temp/'venv';subprocess.run([sys.executable,'-m','venv',str(venv)],check=True);python=venv/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
  commands=[('install',[str(python),'-m','pip','install','-r','requirements-dev.txt','-r','requirements.txt']),('tests',[str(python),'run_tests.py','--load']),('migration-volume',[str(python),'tests/migration_volume.py'])]
  checks=[]
  for label,command in commands:
   log=report.with_name(report.stem+'-'+label+'.txt')
   with log.open('w') as stream:run=subprocess.run(command,cwd=root,stdout=stream,stderr=subprocess.STDOUT)
   checks.append({'check':label,'exit_code':run.returncode,'log':log.name})
   if run.returncode:raise RuntimeError(label+' mislukt; zie '+str(log))
  result={'archive':archive.name,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'manifest_files':len(listed),'fresh_venv':True,'checks':checks,'production_claim':False}
  report.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
