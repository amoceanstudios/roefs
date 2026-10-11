"""Test het logo, de Nederlandse velden, navigatiecode en de backend op een tijdelijke database."""
import os,re,subprocess,tempfile,time,urllib.request
from pathlib import Path
D=Path(__file__).resolve().parent
html='\n'.join((D/f).read_text() for f in ('index.html','app.js','ui.js'))
assert 'lang="nl"' in html
assert 'function veldnaam(k)' in html
assert 'function initRoefsHistory()' in html
assert 'popstate' in html
assert 'async function refreshSmart()' in html
assert (D/'assets'/'amocean-mark.png').read_bytes()[:8]==b'\x89PNG\r\n\x1a\n'
with tempfile.TemporaryDirectory() as tmp:
 env={**os.environ,'PORT':'19895','ROEFS_DB':tmp+'/roefs.db','ROEFS_DEMO_GATE':''}
 proc=subprocess.Popen(['python3',str(D/'server.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
 try:
  for i in range(30):
   try:
    with urllib.request.urlopen('http://127.0.0.1:19895/assets/amocean-mark.png?v=2',timeout=1) as response:
     logo=response.read();assert response.status==200;assert response.headers.get_content_type()=='image/png';assert logo[:8]==b'\x89PNG\r\n\x1a\n';break
   except Exception:
    if proc.poll() is not None:raise RuntimeError(proc.stderr.read().decode())
    time.sleep(.15)
  else:raise RuntimeError('Logo HTTP-test mislukt')
 finally:
  proc.terminate();proc.wait(timeout=5)
print('PASS: logo HTTP 200, PNG, Nederlandse veldnamen, navigatiegeschiedenis, slim-widget-vernieuwing')
