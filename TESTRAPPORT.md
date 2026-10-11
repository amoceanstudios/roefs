# Testrapport — ROEFS ONE

Datum: 11 oktober 2026. Getest op de bijgewerkte broncode uit dit pakket. Alle gegevens zijn fictief. De oorspronkelijke documentatieclaims zijn niet als testbewijs overgenomen.

## Definitieve resultaten

| Controle | Resultaat | Bewijs |
| --- | --- | --- |
| Uitgebreide suite | **51 geslaagd, 0 mislukt, 0 overgeslagen** | `reports/all-tests.txt` |
| Bestaande API-controles | **65 geslaagd** | `reports/legacy-api.txt` |
| Bestaande planning/rechten-controles | **18 geslaagd** | `reports/legacy-planning.txt` |
| Logo via HTTP, PNG en codecontroles | Geslaagd | `reports/logo.txt` |
| Python-compilatie, JavaScript- en shellsyntax | Geslaagd | `py_compile`, `node --check app.js/ui.js`, `bash -n` daadwerkelijk uitgevoerd |
| Docker-build en draaiende container | Geslaagd: HTTP-gereedheid, login en zes webbestanden | `reports/docker-build.txt`, `reports/docker-runtime.json` |
| Korte lokale schaalproef | **24 van 24 verzoeken geslaagd**, database-integriteit `ok` | `reports/load-smoke.json` |
| Externe Cloudflare Tunnel | **Geblokkeerd: DNS/netwerktoegang**, geen publieke link gevalideerd | `reports/tunnel.txt` |

De 51 tests bestaan uit **37 backend-/beveiligingstests, 10 echte Chromium-browsertests en 4 installatietests**. Subtests bestrijken onder meer alle 21 CRUD-modules en meerdere schermbreedtes. De 65 en 18 bestaande controles overlappen inhoudelijk deels met de uitgebreidere suite; tel dit niet als 134 onafhankelijke bedrijfsprocessen.

## Daadwerkelijk gecontroleerd

- Aanmaken, lezen, wijzigen en verwijderen voor elke module, inclusief opgeslagen beschikbaarheid. Opnieuw starten behoudt gegevens.
- Onbekende velden, ongeldige JSON, getallen, datums, verwijzingen en statussen worden geweigerd. Gekoppelde records kunnen niet zomaar worden verwijderd.
- Eigen-recordrechten en objectafscherming, accountkoppeling ondanks naamswijziging, geen toegang via alleen een gelijke naam, beperkte dashboardtellers en admin-only API's.
- Uren indienen/goedkeuren, dubbele uren, daggrens, werkbonafronding, berichten/leesstatus en actuele meldingswidgets.
- Overlap, tijdnotatie, verlof en beschikbaarheid; SOS en werkstromen kunnen de controle niet omzeilen. Gelijktijdige overlappende aanvragen slaan precies één dienst op.
- Voorstellen goedkeuren en maximaal eenmaal uitvoeren; conceptfactuur en werkbon worden werkelijk opgeslagen.
- Sessietokenhashes, sessieverval/uitloggen, accountblokkering, wachtwoordwijziging, behoud laatste beheerder, loginbegrenzing, origin-/contenttypecontrole en browserheaders.
- Opgeslagen XSS-invoer verschijnt als tekst; CSV-formulevelden worden afgeschermd. Dit is regressiedekking, geen volledige penetratietest.
- Browser tegen echte HTTP-server en SQLite: alle beheerschermen, CRUD, medewerkersuren/beschikbaarheid, plannersuggestie → dienst, accountbeheer, rondleiding, terug/vooruit, menufocus en Escape.
- Schermbreedtes 320, 375, 390, 412, 768, 1024 en 1440 px: geselecteerde hoofdschermen zonder horizontale pagina-overloop; menu-items bereikbaar. Tabellen en weekkolommen mogen binnen hun eigen gebied horizontaal schuiven.
- Start met nieuwe/bestaande database, consistente backup, additive migratie van oud accountschema, bestaande poort correct weigeren en bestaande server ongemoeid laten. Tunnelstart in `--check`-modus controleert de lokale app met een reeds ingestelde toegangscode en drukt die niet af.

De lokale app is ook rechtstreeks gestart vanuit de uiteindelijke werkmap. Screenshotbewijs staat in `reports/mobile.png` en `reports/desktop.png`.

## Beperkte schaalproef

250 fictieve medewerkers, 800 fictieve klanten en 1.250 diensten. Vier gelijktijdige verzoeken, 24 leesverzoeken verdeeld over dashboard, planning, klanten en slimme inzichten. Mediaan: 386.8 ms; langzaamste verzoek: 1484.6 ms; totale meetduur: 2.93 s. Deze cijfers horen bij deze lokale machine en dit scenario; het zijn geen capaciteitstoezeggingen.

Er is geen duurtest met 250 gelijktijdig actieve medewerkers, gemengde echte schrijfbelasting, WAN-vertraging, storingen of herstel onder piekbelasting uitgevoerd. Er is op basis hiervan geen reden vastgesteld om Python of SQLite voor deze ontwikkelversie te vervangen, en evenmin bewijs dat de uiteindelijke productiebelasting al wordt ondersteund.

## Niet geslaagd of niet gevalideerd

- **Cloudflare:** geverifieerde officiële client gestart; registratie op `api.trycloudflare.com` faalt door geweigerde DNS in de cloudmachine. De startcode en lokale extra toegang zijn getest, de publieke tunnel niet. Er is geen 24-uursbeschikbaarheidstest uitgevoerd.
- **Echte mobiele apparaten:** geen fysieke iPhone, Android, Safari/WebKit, VoiceOver of TalkBack getest. Chromium met mobiele viewport bewijst die compatibiliteit niet. Het downloaden van aanvullende Playwright-browsers werd door het netwerk geblokkeerd; systeem-Chromium is gebruikt.
- **Productie:** geen onafhankelijke penetratietest, AVG-audit, juridische CAO-validatie, volledige toegankelijkheidsaudit of langdurige productiebelastingtest.
- **Integraties:** geen externe klantaccounts, echte SMS/e-mail, bankbetalingen, boekhoudkoppeling, loonstrookverwerking of beveiligde documentupload geïmplementeerd of getest. Bestaande demonstratiemodules blijven behouden en slaan hun eigen gegevens op.
- **Migratie:** de meegeleverde ZIP bevatte geen bestaande database. Een synthetisch oud accountschema en herstart/backup zijn getest; een onbekende gebruikersdatabase is niet gevalideerd.

## Uitvoeren

`python3 run_tests.py --load` voert de volledige suite uit en bewaart echte uitvoer. Playwright/Chromium zijn daarvoor nodig; zie INSTALLATIE.md. `--backend-only` laat browsertests expliciet onuitgevoerd. Fouten behouden een niet-nul exitcode.

Er zijn tijdens ontwikkeling gevonden fouten hersteld, waaronder mobiele focus, Docker-bestandsrechten en de bezette-poortcontrole. De tabel bovenaan beschrijft de **laatste geslaagde uitvoering**, niet eerder afgebroken ontwikkelruns. Er zijn geen falende assertions uitgeschakeld om deze uitkomst te bereiken.
