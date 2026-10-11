# Installatie en bediening

## 1. Lokaal starten

1. Pak de volledige ZIP uit in een eigen map. Laat `assets/` en de JavaScript-/CSS-bestanden bij `server.py` staan.
2. Installeer Python 3.10 of nieuwer. De geteste versie is Python 3.12.
3. Open een terminal in die map en voer `python3 start.py` uit. Windows: `py -3 start.py`.
4. Open het adres dat het script toont. De standaardpoort is 8765.
5. Nieuwe databases krijgen fictieve voorbeeldgegevens. Het script genereert twee willekeurige accountwachtwoorden: beheerder `Roefs` en medewerker `Bart van Aalde` (fictieve demonstratiepersoon uit de bron-ZIP). De wachtwoorden verschijnen uitsluitend in je terminal en staan lokaal in `data/demo-accounts.json`.
6. Stop met Ctrl+C. Bij de volgende start blijven gegevens en wachtwoorden behouden.

`bash START.command` en `START.bat` zijn snelkoppelingen naar dezelfde Python-start. Voor een geautomatiseerde start zonder wachtwoorden in logs: `python3 start.py --quiet`. Een losse starttest is `python3 start.py --check --quiet`; deze sluit het eigen proces weer af.

Je kunt `PORT`, `ROEFS_DB` en `ROEFS_HOST` instellen. Standaard luistert de app alleen op 127.0.0.1. Stel `ROEFS_ADMIN_PASSWORD` en `ROEFS_EMPLOYEE_PASSWORD` vóór de eerste start in wanneer je eigen demowachtwoorden wilt gebruiken. Deze variabelen wijzigen bestaande accounts niet. Gebruik daarvoor Gebruikers en rechten → Account beheren. Direct starten met `server.py` blijft mogelijk voor ontwikkeling, maar gebruikt zonder variabelen de oorspronkelijke bekende demowachtwoorden; gebruik het nieuwe startscript voor demonstraties.

## 2. Bestaande versie bijwerken

1. Stop de oude server en tunnel.
2. Bewaar de hele oude projectmap als reservekopie.
3. Pak de nieuwe versie in een aparte map uit. Kopieer uitsluitend de bestaande `data/`-map en eventueel `.demo_gate` naar die map. Gebruik geen echte bedrijfsgegevens.
4. Start met `python3 start.py`. Vóór iedere start van een bestaande database maakt het script een consistente SQLite-backup in `data/backups/`, inclusief reeds gecommitteerde WAL-inhoud.
5. De migratie voegt tabellen/indexen en `employee_id`/`active` aan accounts toe. Bestaande records, wachtwoorden en namen blijven behouden. Bij de eerste migratie wordt een medewerkersaccount alleen automatisch gekoppeld bij exact één bestaand dossier met dezelfde naam. Controleer daarna de koppelingen onder Gebruikers en rechten. Latere koppelingen gebeuren uitsluitend expliciet via het beheer.
6. Oude sessies worden niet hergebruikt: log opnieuw in. De nieuwe versie slaat sessietokens gehasht op.

Nieuwe installaties krijgen eenmaal demonstratiegegevens. Het verwijderen van de laatste klant of het opnieuw starten voegt geen onverwachte voorbeelden toe. Backups worden niet automatisch verwijderd; beheer de bewaartermijn zelf.

### Een backup terugzetten

Stop alle processen. Bewaar de huidige data-map eerst apart. Maak vervolgens een lege data-map en plaats één gecontroleerde backup als `roefs.db`; neem geen oude `roefs.db-wal` of `roefs.db-shm` mee. Accountwachtwoorden staan in de database en blijven die van het backupmoment. Bewaar het bijbehorende lokale accountbestand desgewenst afzonderlijk. Start opnieuw en controleer inloggen, relaties, planning en `PRAGMA integrity_check`. De geautomatiseerde tests controleren backupintegriteit en migratie; een volledige calamiteitenoefening op echte bedrijfsdata is niet uitgevoerd.

## 3. Gratis Cloudflare Tunnel

Op macOS:

```bash
brew install cloudflared
bash START-GRATIS-24U.command
```

Op Linux of Windows: installeer de officiële Cloudflare Tunnel-client volgens https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/ en voer `python3 start.py --tunnel` uit (Windows: `py -3 start.py --tunnel`). `CLOUDFLARED_BIN` kan naar een eigen geïnstalleerde client wijzen.

Het startscript:

- start de lokale server en controleert een echte HTTP-respons;
- gebruikt een willekeurig extra toegangswachtwoord in `.demo_gate`;
- toont eerst de HTTP-toegang met gebruikersnaam `demo`, daarna log je in met een ROEFS-account;
- start `cloudflared tunnel --no-autoupdate --url ...` en stopt eigen processen bij afsluiten;
- gebruikt op macOS de bestaande `caffeinate`-route om slapen tijdens de demonstratie te voorkomen.

De URL is tijdelijk en wijzigt bij opnieuw starten. Deel `.demo_gate`, accountbestanden of wachtwoorden niet mee in de ZIP. De accountloze tunnel heeft geen beschikbaarheidsgarantie.

**Status van de uitgevoerde controle:** cloudflared 2026.10.0 is via de officiële GitHub-release gedownload en de SHA-256 is vergeleken met de releasepagina. De registratie bij `api.trycloudflare.com` mislukte in de cloudmachine door geweigerde DNS-toegang. Er is dus geen werkende publieke URL of externe end-to-endtest bewezen. Test dit op je eigen machine en telefoon. Benodigde netwerktoegang omvat de Cloudflare-registratieservice en de door Cloudflare gedocumenteerde tunnelbestemmingen (`argotunnel.com`, doorgaans TCP/UDP 7844); een HTTPS-proxy alleen volstaat niet altijd. TLS-controles zijn niet uitgeschakeld.

## 4. Docker

```bash
docker build -t roefs-one .
docker volume create roefs-demo-data
docker run --rm --name roefs-one -p 127.0.0.1:8765:8080 \
  -v roefs-demo-data:/app/data roefs-one
```

De container draait als UID 10001, bindt intern op 0.0.0.0:8080 en schrijft alleen in `/app/data`. De hostpoort blijft lokaal. Laat de tunnel desgewenst op de host verbinden met die poort; configureer dan ook `ROEFS_DEMO_GATE` in de container. De standaard lokale Docker-start publiceert zelf geen tunnel. De image-build, containerstart, login en levering van alle statische bestanden zijn daadwerkelijk getest.

## 5. Tests uitvoeren

Backend en installatie vereisen alleen Python:

```bash
python3 run_tests.py --backend-only
```

Voor de volledige suite in een eigen virtualenv:

```bash
python3 -m venv .venv
# macOS/Linux:
. .venv/bin/activate
# Windows gebruikt: .venv\Scripts\activate
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python run_tests.py --load
```

Op Linux kunnen systeemlibraries nodig zijn; volg daarvoor de Playwright-installatiehandleiding. Een bestaande Chromium kan worden gebruikt via `ROEFS_TEST_BROWSER=/pad/naar/chromium`. In de ontwikkelomgeving is `/usr/bin/chromium` gebruikt omdat de browserdownloadserver werd geblokkeerd.

De tests starten eigen servers met tijdelijke databases. `run_tests.py` bewaart uitvoer in `reports/` en geeft een niet-nul exitcode bij fouten. De optionele korte schaalproef staat in `tests/load_smoke.py`. Geen enkele test gebruikt productiegegevens of verstuurt e-mail/SMS.
