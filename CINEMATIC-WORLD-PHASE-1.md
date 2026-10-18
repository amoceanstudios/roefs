# Cinematische modulewereld: fase 1

Dit is het historische fase-1-ontwerp. De actuele navigatie, geïntegreerde schermen en afwerking staan in `CINEMATIC-WORLD-IMPLEMENTATION.md`. Het bevroren fase-1-bewijs staat in `reports/phase-1/`.

Open na inloggen **3D-portaal** op het bestaande startscherm.
Deze eerste fase toont het wereldontwerp. De bestaande ruimtelijke gegevenswerkplek blijft afzonderlijk bereikbaar via **Ruimtelijke werkplek**.

## Gebouwd

- Een live React Three Fiber-wereld met één fysiek object per bestaande toegankelijke module. Het beheeraccount ziet momenteel 45 objecten in de zeven bestaande navigatiegroepen. Labels, route-identiteiten en zichtbaarheid komen rechtstreeks uit `GROUPS`, `NAMES` en `canView`.
- Een donkere industriële ruimte met monolieten, procedurele beton- en metaalmaterialen, moduleborden in de 3D-wereld, een hard aan de camera gekoppeld voorlicht, snelle lichtafname en een ingetogen warme kleurstelling.
- Een CatmullRom-pad voor de langzame establishing shot. De GSAP-intro trekt rustig naar de uitgangspositie. Continue value noise zorgt voor zeer kleine positie- en rotatieafwijkingen. Hover geeft een kleine lift, belichtingsaccent en camera-push.
- ACES-tonemapping. Hoog: bloom, autofocus/scherptediepte, korrel, vignet en subtiele radiale chromatische aberratie. Gebalanceerd: zonder scherptediepte en kleurafwijking. Licht: eenvoudige geometrie en Phong-materialen, minder draw calls, lagere DPR en geen postprocessing.
- Automatische initiële kwaliteit op basis van viewport, beschikbare hardware-informatie en rendereridentificatie. Aanhoudend lage gemeten framesnelheid schakelt de kwaliteit terug. De gebruiker kan zelf een kwaliteitsniveau kiezen; automatisch terugschakelen blijft actief.
- Een typografische preloader, muisparallax en optioneel kantelen na een expliciete gebruikershandeling. Geen automatische sensorpermissie.
- Een doorzoekbare modulelijst, toetsenbordbediening, focusbegrenzing, Escape, focusherstel en inert maken van het onderliggende portaal zolang de wereld open is.
- `prefers-reduced-motion` en een eigen bewegingsknop schakelen drift, shake, hover-push en bewegende intro uit. De vereenvoudigde scène is in de browsertest daadwerkelijk op stilstaande pixels gecontroleerd.
- Zonder WebGL2 blijft dezelfde toegankelijke modulelijst beschikbaar. Bestaande schermen openen via hun oorspronkelijke routefunctie.

## Wat is veranderd

De presentatiecode staat in `spatial/World.jsx`, met een pure module-adapter en kwaliteitsbeleid in `spatial/world-model.mjs`. `spatial/index.js` voegt alleen de toegangsknop en lifecycle-wrapper toe. `spatial.css` bevat uitsluitend afgeschermde `.cinema-*` en `.world-*` stijlen. De runtime blijft één lokaal gebouwd `spatial.js`-bestand, zonder CDN of extra backendroute.

React, React DOM, React Three Fiber, Drei, React Three Postprocessing, postprocessing, GSAP en Zustand zijn gepind. `package-lock.json` bewaart de volledige afhankelijkheden. `tools/frontend_notices.mjs` verzamelt de upstreamlicenties in `THIRD-PARTY-LICENSES.txt`.

Een regressietest vond een race bij cookie-herladen: de originele startpagina kon klaar zijn voordat de grotere presentatiebundel was geladen. De presentatielaag voegt de toegangsknoppen nu ook na eigen initialisatie idempotent toe. De oorspronkelijke boot- en authenticatiefuncties zijn daarvoor niet herschreven. Een aparte test vertraagt de bundel bewust en controleert dat beide knoppen precies eenmaal verschijnen.

**Niet gewijzigd:** Python-backend, SQLite-schema/data, auth-implementatie, API-contracten, oorspronkelijke route-identiteiten, rechtencontroles en bedrijfslogica. De wereld maakt zelf geen bedrijfsgegevens aan of bij. De browsertest controleert dat openen/verkennen geen schrijvende requests uitvoert. Tests voor bestaande formulieren, planning, werkbonnen en de klantcase worden daarnaast uitgevoerd.

## Bewust nog niet onderdeel van fase 1

Klikken opent nu het bestaande scherm. Dit is nog geen ononderbroken vlucht naar een module. Per-module entry-splines, fly-out/Back, URL-gestuurde vluchten en deep links horen bij fase 2. De huidige URL verandert niet bij openen of sluiten van het wereldontwerp; selectie van een module gebruikt de bestaande router.

De bestaande module-UI's zijn nog niet ingebouwd als refracterende, zwevende werkpanelen: fase 3. Een frosted CSS-paneel is geen fysieke refractie en wordt hier ook niet zo beschreven.

Fotografische assets, video- en depth-planes, KTX2/Basis-texturen, Draco-GLB's, assetstreaming per module, motion blur, flitsmomenten/exposure-settle en geluid zijn nog niet geïmplementeerd. Deze fase gebruikt lichte procedurele geometrie en zelf opgebouwde texturen, geen verzonnen foto- of videobibliotheek. Deze onderdelen moeten in de vervolgfases worden toegevoegd en getest.

60 fps op een middelgrote laptop en 30 fps op telefoons zijn **ontwerpdoelen, nog geen bewezen resultaat**. De cloudmachine gebruikt software-WebGL; de opgenomen framecadans staat in `reports/world-frame-sample.json`. Dat is geen representatieve GPU- of fysieke-apparaatbenchmark. Er wordt geen productiegeschiktheid vastgesteld.

## Bouwen en controleren

```sh
npm ci --cache /tmp/roefs-npm-cache
node tools/frontend_notices.mjs
npm run build
npm run test:spatial
.venv/bin/python -m unittest discover -s tests -p test_world_browser.py -v
.venv/bin/python -m unittest discover -s tests -p test_spatial_browser.py -v
```

Starten blijft via het bestaande `start.py`. Docker/Render heeft geen Node.js nodig omdat de browserbundel wordt meegeleverd. Er zijn in deze fase geen nieuwe statische endpoints of externe verzoeken toegevoegd.

Beelden: `reports/world-desktop.png`, `reports/world-mobile.png`, `reports/world-effects.png`. Zie `reports/world-phase-1-verification.md` voor de definitieve uitgevoerde controles. Dit wereldontwerp is nog niet vanuit deze wijziging naar GitHub of Render gepubliceerd.
