# Ruimtelijke werkplek

Deze handleiding beschrijft de bestaande gegevensruimte. Het aanvullende moduleportaal met React Three Fiber, cameravluchten en de oorspronkelijke werkende schermen wordt beschreven in `CINEMATIC-WORLD-IMPLEMENTATION.md`.

Open na inloggen **Ruimtelijke werkplek** op het startscherm of in het zijmenu.
Het bestaande Amocean-startscherm en de overige modules blijven beschikbaar.

## Gebruik

- Klanten zijn turquoise, opdrachten paars en facturen goud. Spoedopdrachten en vervallen onbetaalde facturen zijn oranje.
- Sleep het canvas om te draaien, scroll of gebruik de zoomknoppen om te zoomen. Twee vingers verplaatsen/zoomen op een aanraakscherm.
- Klik op een knooppunt of gebruik de doorzoekbare knoppenlijst. De camera beweegt naar het dossier en het HTML-paneel volgt de wereldpositie. Verbonden klant-, opdracht- en factuurgegevens worden met lijnen verbonden.
- Pas klantnaam, contactpersoon, e-mail en telefoon aan en kies **Wijzigingen opslaan**.
- Open een opdracht. Sleep checklisttaken tussen **Te doen** en **Afgerond**, of tik op de taak. Nieuwe taken worden via **Taak opslaan** toegevoegd.
- **Volledige werkbon openen** brengt je naar het bestaande uitvoeringsscherm voor planning, uren, beoordeling en factuurvoorbereiding. Deze uitgebreide werkstappen zijn nog geen eigen ruimtelijke panelen.
- **Overzicht** of Esc sluit het paneel en brengt de camera terug. **Sluiten** opent het oorspronkelijke startscherm.
- De zoeklijst ondersteunt toetsenbordbediening en werkt ook zonder WebGL. Op mobiel staat het paneel onderin; het scrolt zelfstandig.

## Architectuur en bestaande gegevens

De bestaande frontend gebruikt gewone JavaScript. Daarom gebruikt deze uitbreiding Three.js en OrbitControls rechtstreeks, zonder React-migratie of extra frontendserver.

| Onderdeel | Verantwoordelijkheid |
| --- | --- |
| `spatial/model.mjs` | Pure adapter van bestaande records naar unieke posities, kleuren, urgentie en relaties |
| `SpatialDataSource` | Bestaande API’s ophalen, inclusief alle pagina’s en bestaande serverrechten |
| `SpatialCanvas` | Scene, raycasting, camera, pointer/touch-events, selectie, formulieren en lifecycle |
| `SpatialHtmlLayer` | Gewone DOM-panelen en labels projecteren vanuit 3D-coördinaten; mobiele positionering |
| `spatial.css` | Donkere volledige viewport, glazen panelen en responsieve bediening |
| `spatial.js` | Lokaal gebundeld browserbestand, inclusief Three.js; geen CDN of externe runtimeverzoeken |

De herbruikbare classes staan ook op `window.ROEFSSpatial`.
Een eigen source implementeert `load(signal)` met `{customers, workorders, invoices, objects}`.
De action-adapter biedt `request(path, method, body)`, `metadata()`, `home()`, `work(id)` en `invoice(id)`.
Recordidentiteiten en foreign keys bepalen relaties, nooit overeenkomstige namen. Deze app heeft werkopdrachten, geen afzonderlijke projectentiteit; de paarse sector gebruikt daarom de bestaande werkopdrachten.

De Python-bedrijfslogica, SQLite-schema’s, API-contracten en authenticatie zijn ongewijzigd. In `server.py` zijn alleen de twee nieuwe statische bestanden aan de bestaande expliciete bestandslijst toegevoegd. De Dockerfile kopieert de gebouwde bestanden mee.
Alle wijzigingen gebruiken bestaande API’s, CSRF, sessies, serverrechten en versienummers. Een versieconflict toont een fout en overschrijft geen nieuwere gegevens. Er worden geen financiële transacties vanuit het canvas uitgevoerd.

## Ontwikkelen en starten

Vereist: bestaande Python-omgeving en Node.js 22 of nieuwer voor het herbouwen.

```sh
cd /workspace/roefs
npm ci --cache /tmp/roefs-npm-cache
npm run build
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python start.py --check --quiet
.venv/bin/python start.py --quiet
```

Gebruik de bestaande lokale accountvoorziening van `start.py`; zet wachtwoorden en databasebestanden niet in Git. Render/Docker heeft Node niet nodig omdat `spatial.js` wordt meegeleverd. Na wijzigingen in `spatial/` altijd opnieuw bouwen en het gebouwde bestand meenemen.

```sh
npm run test:spatial
.venv/bin/python -m unittest discover -s tests -p test_spatial_browser.py -v
.venv/bin/python -m unittest discover -s tests -p 'test_client_case*.py' -v
```

Chromium: `/usr/bin/chromium`. Browsertests gebruiken een tijdelijke database met uitsluitend fictieve gegevens en software-WebGL. Screenshots staan in `reports/spatial-*.png`.

## Afbakening

Dit is een werkende frontendbasis, geen volledige omzetting van alle modules naar 3D. Formulieren voor klantcontactgegevens en checklisttaken werken rechtstreeks in het ruimtelijke paneel. Andere processen gebruiken de bestaande schermen. Gegevens verversen bij openen, handmatig vernieuwen en na opslaan; er is geen realtime push-abonnement.

De adapter is op 800 unieke klantposities getest. Dit bewijst geen renderprestaties met een volledig bedrijfsbestand: daarvoor zijn representatieve GPU-, browser- en belastingmetingen nodig. Er zijn maximaal 30 zichtbare DOM-labels per categorie, terwijl alle knooppunten en zoekresultaten beschikbaar blijven. Geen WebXR/VR-headsetintegratie of fysieke iPhone-/Android-/Safari-validatie uitgevoerd. Productiegeschiktheid volgt niet uit deze tests.
