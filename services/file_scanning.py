"""ClamAV-interface: geen shell, geen vrijgave bij scannerfouten."""
import os,shutil,subprocess

def scan(path,mime):
    command=shutil.which('clamdscan')
    if not command:
        # UTF-8 tekst wordt uitsluitend als attachment met nosniff aangeboden.
        return ('Tekstbijlage','Geen actieve inhoud; geen malwarescan uitgevoerd.') if mime=='text/plain' else ('Quarantaine','ClamAV is niet beschikbaar; downloaden geblokkeerd.')
    try:result=subprocess.run([command,'--no-summary','--fdpass',str(path)],capture_output=True,timeout=15)
    except (OSError,subprocess.TimeoutExpired):return 'Quarantaine','Scanner niet bereikbaar of tijdslimiet overschreden.'
    if result.returncode==0:return 'Schoon','ClamAV-controle voltooid.'
    if result.returncode==1:return 'Geblokkeerd','Scanner heeft een bedreiging gemeld.'
    return 'Quarantaine','Scannercontrole mislukt; bestand niet vrijgegeven.'
