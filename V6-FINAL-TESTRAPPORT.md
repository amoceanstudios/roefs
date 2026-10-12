# V6 finaal testrapport — migratiepakket

12 oktober 2026. Uitsluitend fictieve gegevens, tijdelijke databases en lokale HTTP-servers. Geen productiecertificering.

## Uitgevoerd op de bijgewerkte bron

| Controle | Resultaat |
|---|---|
| `python run_tests.py --load` | 153 unittests/integratie-/browsertests geslaagd; geen skips of verwachte fouten; 192,949 s voor de unittest-suite |
| Oorspronkelijke API-controles | 65 geslaagd |
| Oorspronkelijke planning/rechten | 18 geslaagd |
| Logo/Nederlandse velden/navigatie/widgetcontrole | Geslaagd |
| Beide korte belastingproeven | Geslaagd; exacte metingen in reports/load-*.json |
| `python tests/migration_volume.py` | 24.050 echte imports, gelijke herimport ongewijzigd, herstart, relaties en backup/herstel geslaagd |
| Alle categorieën | 26 XLSX-templateimports + 26 CSV-herimports; beide templateformaten parseerbaar en downloadbaar |
| Nieuwe wizard/beheerschermen | 4 Chromium-browserproeven geslaagd: CSV-mapping, XLSX, downloads, schoolafspraken, onboarding, boekhoudconfiguratie en scopebeleid |
| Schoolafspraken | 3 API-/databasetests geslaagd, incl. 40 weken/460 uur, uitzonderingen, vier glasbezoeken, geen dubbele werkbonnen en rollback |
| Scopebeleid | 10 beleidskerntests + 4 negatieve/positieve HTTP-tests geslaagd, inclusief alle oorspronkelijke modules |
| Migratie-API | 8 tests geslaagd, inclusief conflicten, twee gelijktijdige bevestigingen, reimport, herstel en verboden toegang |
| Spreadsheetveiligheid | 5 tests geslaagd, incl. uitpaklimiet, XML-entiteiten, externe relaties, padtraversal, beschadiging, Excel-datum/tijd/voorloopnullen en werkbladvolgorde |
| Onboarding | 2 API-tests geslaagd: bewijs, afhankelijkheden, intrekken, herstart, versies en rechten |
| Boekhoudcontract | 4 mockadaptertests geslaagd: inactieve configuratie, goedkeuring, idempotentie na timeout, herhaling, statussen, automatische cyclus en pauzeren bij herstel |
| Docker | Nieuwe image gebouwd; UID 10001, health/login, 26 categorieën, echte CSV-import en XLSX-herimport geslaagd; geen publieke deployment |
| Startscript | Twee geïsoleerde starts met `--check --quiet` geslaagd |

De genoemde deeltests zijn inbegrepen in de 153; tel ze niet nogmaals op. Raw uitvoer: `reports/all-tests.txt`, `legacy-api.txt`, `legacy-planning.txt`, `logo.txt`; volumebewijs in `reports/migration-volume.json`; containerbewijs in `reports/v6-migration-docker.json`.

## Schone ZIP-controle

`tools/verify_package.py` controleert archiefpaden/manifest/hash, pakt uit in een volledig nieuwe tijdelijke map, maakt een nieuwe venv, installeert de dependencies en voert **alle tests met load én de volledige HTTP-volumemigratie** uit. De browser-/migratietests bevatten echte CSV/XLSX-import, modulezichtbaarheid, herimport, autorisatie, herstart en herstel. Het resultaat voor de exacte ZIP-hash wordt naast het ZIP gepubliceerd als `V6-MIGRATION-PACKAGE-VERIFICATION.json` met de bijbehorende tekstlogs. Een bron-ZIP bevat bewust geen eigen zelfverwijzende hashverklaring.

## Mislukte tussenruns en herstel

- Baseline: 123 tests, één mislukte browserassertie na documentupload. De assertie liep vóór verversen van de werkruimte; expliciet wachten op de opgeslagen bestandsnaam herstelde dit. De vijf betreffende tests slaagden daarna.
- Templateproeven: leeg noodbeschikbaarheidsveld blokkeerde medewerkers en afhankelijke records. Vervolgens veroorzaakten automatisch klantnummer/lege pauze onterechte herimportverschillen. Normalisatie hersteld; alle 26 categorieën slagen nu met beide formaten.
- Een volledige tussenrun met 153 tests had vijf subtestfouten doordat nieuwe vertaalde veldlabels onbedoeld pagina's werden. Labels zijn uit het paginaregister gehaald. De tien schermtests en daarna de volledige 153-testssuite slaagden. Er zijn geen tests verwijderd of uitgeschakeld om dit groen te maken.

- Extra beveiligingsproef: een bestandsnaam met een img-tag werd aanvankelijk als HTML-element weergegeven. Bestandsnaam-escaping toegevoegd; dezelfde browserassertie controleert nu letterlijk weergegeven tekst en nul geïnjecteerde elementen.

## Niet uitgevoerd of niet bewezen

Geen echte NoCore-export of live boekhoudprovider; mocksucces is geen leveranciersacceptatie. Geen fysieke iPhone/Android, WebKit/Safari-eindacceptatie, screenreaderacceptatie, onafhankelijke pentest of langdurige productiebelasting. Eerdere WebKit-download werd HTTP 403 geweigerd; Cloudflare-registratie was DNS-geblokkeerd. ClamAV ontbreekt; geen geslaagde malwarescan claimen. Oudere dependency-/V5-migratie-/traploadrapporten blijven historische meetpunten, geen nieuw uitgevoerde controles.

De fictieve migratievoorzieningen zijn technisch getest. Een klantpilot met echte gegevens vereist vooraf goedgekeurde exports, mapping, rechtenindeling, beveiligde persistente omgeving en terugvalplan. Go-live vereist afzonderlijke inhoudelijke, beveiligings-, leveranciers- en belastingacceptatie.
