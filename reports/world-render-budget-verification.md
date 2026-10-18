# Vervolg: minder renderwerk bij een stilstaand portaal

Datum: 18 oktober 2026. Deze vervolgstap bouwt voort op fase 2–4; hij vervangt geen bestaande module of bedrijfsfunctie.

## Wijziging

Het R3F-canvas rendert op aanvraag. Bij **Beweging aan** vraagt de camera het volgende frame aan voor drift, licht en effecten. Bij **Beweging uit** stopt die lus zodra het beeld stabiel is. Navigatie, korte GSAP-overgangen, hover, kwaliteitskeuze en resize kunnen het canvas opnieuw laten tekenen. Ook de instanced moduleobjecten vragen bij een wijziging zelf een frame aan. Een verborgen document stopt de lus en zichtbaarheid hervat deze.

`ROEFSSpatial.metrics()` meldt `renderMode`, een cumulatieve `renderedFrames`-teller en `fps: null` voor een stilstaand beeld. De kwaliteitsregeling verlaagt geen kwaliteit op basis van opzettelijk schaarse frames. De teller begint opnieuw wanneer een nieuwe wereldsessie ontstaat, bijvoorbeeld na herladen.

## Daadwerkelijk uitgevoerd

- `npm run build`: browserbundel opnieuw gebouwd.
- `npm run test:spatial`: 8 JavaScript-tests geslaagd.
- `test_world_render_budget.py`: 2 nieuwe Chromium-tests geslaagd. Beweging hervat en stopt daadwerkelijk; een fictieve klant wordt met het oorspronkelijke formulier opgeslagen en blijft na herladen bestaan.
- `test_world_browser.py`: 6 Chromium-tests geslaagd. Werkelijke canvasselectie, alle moduleobjecten, shaders, mobiele reduced motion, toetsenbord, fallback en vertraagd laden gecontroleerd.
- `test_cinematic_integration.py`: 9 Chromium-integratietests geslaagd. Alle 45 beheermodules, directe links, browsergeschiedenis, snel wisselen, klantopslag, serverrechten, uitloggen tijdens een lopend verzoek, mobiele panelen, geluid, planning verslepen en werkbonchecklists gecontroleerd. Zie `cinematic-demand-regression.txt`.
- Docker-image opnieuw gebouwd. Tijdelijke container onder UID 10001: health, scriptvolgorde en JS/CSS geslaagd. SHA-256 van de werkelijk geserveerde bundel komt overeen met de werkmap. Zie `world-demand-container-test.txt` en `cinematic-docker-smoke.json`.

De nieuwe rendertest mat na stabilisatie telkens **0 extra frames gedurende 1,1 seconden**, zowel in het overzicht als in het klantpaneel en na terugkeer. Zie `world-render-budget.json`. Dit toont dat de WebGL-renderlus stopt; het is geen meting van totaal stroomverbruik of totale browser-CPU.

Totaal van deze vervolgstap: **25 verschillende tests geslaagd (17 Python-browsertests en 8 JavaScript-tests), 0 definitief mislukt, 0 overgeslagen**. De Docker-controle is aanvullend en wordt niet als extra unittest geteld.

De eerste versie van één nieuwe test verwachtte het verkeerde klantlabel (`Klanten` in plaats van het bestaande `Klanten en relaties`). Alleen die verwachting is gecorrigeerd; de definitieve rendertests slagen allebei.

## Grenzen en resterend werk

De tests draaien in Chromium met software-WebGL, niet op een fysieke iPhone, Android of laptop-GPU. De korte RAF-meting in `world-frame-sample.json` draaide tegelijk met andere GPU-browsertests en is geen vergelijkbare prestatiebenchmark. Deze stap bewijst geen verbetering van actieve fps en geen 60/30-fps-garantie. Het stoppen en hervatten bij werkelijke tabbladwisselingen is geïmplementeerd, maar niet apart automatisch getest.

De oorspronkelijke Python-backend, SQLite, API-implementaties en bedrijfsmodules zijn niet gewijzigd. De volledige historische testselectie van 45 tests is niet opnieuw uitgevoerd; deze stap rapporteert zijn eigen uitgevoerde selectie.

Fotografie, video en gecomprimeerde GLB/KTX2/Draco-assets zijn nog niet toegevoegd. De standaard KTX2/Draco-loaders gebruiken blob-workers, terwijl de huidige CSP alleen eigen scripts toestaat. Een werkende decoder-/assetpipeline vraagt daarom een afzonderlijke implementatie en validatie; er wordt geen actieve koppeling of geschikte assetbibliotheek geclaimd.

De wijzigingen zijn lokaal getest. De GitHub-publicatie wordt apart bevestigd met het commitnummer bij oplevering. Deze controles werken de actieve Render-deployment niet bij en valideren die ook niet.

## Voorbereiding GitHub, 19 oktober 2026

De bundel is opnieuw gebouwd en de 8 JavaScript-tests zijn opnieuw geslaagd; dit zijn herhalingen en geen 8 extra unieke tests. De containercontrole is opnieuw geslaagd en bevestigt SHA-256 `3f5eac97a78ca022844cd514ef9259e4e58aa58406cd2206b527d415c177cf26` voor de geserveerde `spatial.js`. Zie `github-release-build.txt`, `github-release-model-tests.txt` en `github-release-container-test.txt`. De eerder uitgevoerde 17 browsertests betreffen dezelfde presentatiecode en bundel. Alleen de README en publicatietekst zijn daarna verduidelijkt. Handgeschreven wijzigingen hebben geen gemelde whitespacefouten; ongewijzigd overgenomen leverancierslicenties behouden hun oorspronkelijke regelafbrekingen.
