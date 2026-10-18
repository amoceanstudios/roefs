# Spatial Canvas: uitgevoerde controles

Datum: 18 oktober 2026. Bestaande V6-code als uitgangspunt. Tests gebruiken uitsluitend fictieve gegevens en geïsoleerde tijdelijke databases.

| Controle | Uitkomst |
| --- | --- |
| `npm ci --cache /tmp/roefs-npm-cache` en `npm run build` | Geslaagd; lokaal meegeleverd Three.js-browserbestand |
| `npm run test:spatial` | 3 geslaagd: 800 unieke posities, relaties via sleutels, urgentie/bedrag zonder bronmutatie |
| `test_spatial_browser.py` | 4 geslaagd: WebGL/raycasting, werkelijke opslag en versieconflict, slepen/aantikken checklist, mobiele weergave, ontoegankelijke medewerkersrol, bruikbare fallback zonder WebGL |
| `test_startup.py` | 4 geslaagd |
| `test_client_case*.py` | 5 geslaagd, inclusief de bestaande klantcase via browser |
| `test_scope_http.py` | 4 geslaagd, positieve en negatieve servercontroles |
| `test_enterprise_browser.py` | 5 geslaagd, bestaande modules en schermbreedtes 320–1920 pixels |
| `npm audit` | 0 gemelde kwetsbaarheden voor de gepinde npm-afhankelijkheden op dit controlemoment |
| Python `pip check`, `node --check spatial.js`, `git diff --check` | Geslaagd |
| `start.py --check --quiet` | Python-server, database en startpagina gecontroleerd |
| Docker-build `roefs-one:spatial` en containercontrole | Geslaagd als UID 10001: health-endpoint, startpagina en beide ruimtelijke bestanden via HTTP bereikbaar |

Totaal: **25 tests geslaagd, 0 definitief mislukt, 0 overgeslagen** in de geselecteerde suites. De volledige historische testsuite is voor deze uitbreiding niet opnieuw uitgevoerd.

De eerste canvaspixeltest las een door WebGL weggegooid framebuffer uit en meldde daardoor 0 pixels. De test gebruikt nu een browseropname van het samengestelde canvas. De definitieve desktop- en mobiele tests tellen daadwerkelijk zichtbare pixels. Opnames zijn ook visueel bekeken. Camera-slepen wordt afzonderlijk gecontroleerd en mag geen klikselectie veroorzaken.

Bewijs: `spatial-*-tests.txt`, `spatial-desktop.png`, `spatial-mobile.png` en `spatial-mobile-panel.png` in deze map. Browser: Chromium met software-WebGL. Desktop: 1440×1000; mobiel: 390×844, met aanraakondersteuning voor de checklisttest.

Dockerbewijs: `spatial-docker-build.txt` en `spatial-docker-smoke.txt`. Er zijn geen externe poorten gepubliceerd tijdens de containercontrole.

Niet gevalideerd: live Render, fysieke iPhone/Android, Safari, VR-headsets, representatieve GPU-prestaties op een volledig bedrijfsbestand of productiegeschiktheid. De 800-recordproef betreft de pure gegevensadapter en is geen renderbelastingtest.
