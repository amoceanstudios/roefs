"""Validate the built frontend in a temporary container without exposing a port."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--image',default='roefs-one:cinematic')
p.add_argument('--docker-config',default='/tmp/roefs-docker')
args=p.parse_args()
code='''import subprocess,sys,time,urllib.request,json,os,hashlib
p=subprocess.Popen([sys.executable,"start.py","--quiet"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
base="http://127.0.0.1:8080"
try:
 ready=False
 for attempt in range(100):
  try:
   health=json.load(urllib.request.urlopen(base+"/api/health",timeout=2));ready=health["ok"];break
  except OSError:time.sleep(.1)
 assert ready
 asset=urllib.request.urlopen(base+"/spatial.js").read();css=urllib.request.urlopen(base+"/spatial.css").read();html=urllib.request.urlopen(base).read().decode()
 design={}
 for name,mime in [("amocean-display.ttf","font/ttf"),("amocean-night.webp","image/webp")]:
  response=urllib.request.urlopen(base+"/assets/"+name);data=response.read();assert response.headers.get_content_type()==mime
  design[name]=hashlib.sha256(data).hexdigest()
 assert "AMOCEAN INTEL" in html
 assert len(asset)>1000000 and len(css)>1000 and html.index("/spatial.js")<html.index("/app.js") and os.getuid()==10001
 print(json.dumps({"health":True,"spatial_js":True,"spatial_css":True,"early_bootstrap":True,"uid":os.getuid(),"asset_sha256":hashlib.sha256(asset).hexdigest(),"css_sha256":hashlib.sha256(css).hexdigest(),"design_assets":design}))
finally:
 p.terminate();p.wait(timeout=10)
'''
run=subprocess.run(['docker','--config',args.docker_config,'run','--rm','-e','ROEFS_COOKIE_SECURE=0',args.image,'python','-c',code],capture_output=True,text=True,check=True)
result=json.loads(run.stdout)
for file,key in [('spatial.js','asset_sha256'),('spatial.css','css_sha256')]:
    assert result[key]==hashlib.sha256((ROOT/file).read_bytes()).hexdigest(),file+' differs from the workspace'
for name,digest in result['design_assets'].items():
    assert digest==hashlib.sha256((ROOT/'assets'/name).read_bytes()).hexdigest(),name+' differs from the workspace'
(ROOT/'reports/cinematic-docker-smoke.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
