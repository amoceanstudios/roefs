#!/usr/bin/env python3
"""Broncode-ZIP met manifest; zonder private runtimegegevens."""
import argparse,hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
EXCLUDE={'.git','.venv','data','__pycache__','.pytest_cache','node_modules'}
def files():
    for path in sorted(ROOT.rglob('*')):
        rel=path.relative_to(ROOT)
        if not path.is_file() or path.is_symlink() or set(rel.parts)&EXCLUDE:continue
        if path.name in ('MANIFEST.json','.demo_gate','.env') or path.suffix in ('.zip','.db','.pyc') or path.name.endswith(('.db-wal','.db-shm')):continue
        if path.name.startswith('.env.'):continue
        yield path

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT.parent/'ROEFS-ONE-ENTERPRISE-V6-TUSSENSTAND.zip');args=parser.parse_args()
    selected=list(files());manifest={'format':1,'product':'ROEFS ONE V6 — tussenstand, geen eindacceptatie','files':[{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in selected]};(ROOT/'MANIFEST.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    with zipfile.ZipFile(args.output,'w',zipfile.ZIP_DEFLATED) as z:
        for path in selected+[ROOT/'MANIFEST.json']:
            info=zipfile.ZipInfo('ROEFS-ONE-ENTERPRISE-V6-TUSSENSTAND/'+str(path.relative_to(ROOT)),date_time=(2026,10,12,0,0,0));info.external_attr=0o100644<<16;info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,path.read_bytes())
    print(json.dumps({'archive':str(args.output),'files':len(selected)+1,'bytes':args.output.stat().st_size,'sha256':hashlib.sha256(args.output.read_bytes()).hexdigest()},indent=2))
if __name__=='__main__':main()
