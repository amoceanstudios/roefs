# Cinematisch portaal: definitieve validatie fase 2–4

Datum: 18 oktober 2026. Bestaande V6-code behouden en uitgebreid in de presentatie.

Vervolg: de renderingbesparing en de opnieuw uitgevoerde controles staan in [world-render-budget-verification.md](world-render-budget-verification.md). De 45 hieronder zijn de geselecteerde tests van de eerdere fase-2–4-run, geen claim dat die volledige selectie na iedere vervolgstap opnieuw is uitgevoerd. `world-frame-sample.json` en `cinematic-docker-smoke.json` worden door latere controles vernieuwd; de hieronder genoemde circa 15 fps betreft de eerdere software-WebGL-meting.

| Uitgevoerde controle | Uitkomst |
| --- | --- |
| JavaScript-adapters, kwaliteitsbeleid, noise en entry-paths | 8 geslaagd |
| Ruimtelijke module-integratie | 8 geslaagd |
| Extra logout-race met bewust vertraagd echt serverantwoord | 1 geslaagd |
| Wereld, WebGL, effecten, touch en fallback | 6 geslaagd |
| Bestaande ruimtelijke gegevenswerkplek | 4 geslaagd |
| Bestaande enterprise-browsertests | 5 geslaagd |
| Bestaande klantcase, HTTP en browser | 5 geslaagd |
| Positieve en negatieve serverrechten | 4 geslaagd |
| Bestaande start-/herstartcontroles | 4 geslaagd |

**45 verschillende geselecteerde tests geslaagd, 0 definitief mislukt en 0 overgeslagen.** De laatste drie navigatie-/CRUD-/planningtests zijn na de overgangsafwerking opnieuw uitgevoerd en slagen. Die herhalingen worden niet extra geteld. `cinematic-validation-summary.json` bevat de unieke Python-testidentiteiten en de totaaltelling.

De volledige historische testsuite is voor deze frontenduitbreiding niet opnieuw uitgevoerd. Dit verslag stelt geen productiegeschiktheid vast.

## Wat daadwerkelijk is uitgeoefend

- Alle **45 toegankelijke beheermodules** geopend binnen dezelfde wereld. Iedere bestemming heeft één verbonden oorspronkelijk `#root` in het ruimtelijke HTML-paneel. Zie `world-module-coverage.json`.
- Authenticated deep links, herladen, snel achtereen navigeren, handmatig wijzigen van het URL-fragment, browser-terug en vooruit, sluiten tijdens een vlucht en teruggaan naar het wereld­overzicht.
- Een nieuwe fictieve klant opgeslagen via het oorspronkelijke formulier, opnieuw geladen en teruggevonden na terug-/vooruitnavigatie. Pointeracties in een formulier openen geen achtergrondobject.
- Een echte dienst in de bestaande planner naar een andere dag gesleept. De nieuwe datum is via de bestaande server-API teruggelezen.
- Checklisttaak bij een opgeslagen werkopdracht toegevoegd en afgerond via de oorspronkelijke werkbonmodal. De opgeslagen waarde is via de API gecontroleerd.
- WebGL2-fallback, mobiele panelen, aanraakbediening, opt-in Web Audio met flight/arrival-events, reduced motion zonder flits, originele modals en focus/lifecycle.
- Een medewerker geweigerd voor datamigratie; de server geeft 403 op klantgegevens. Uitloggen ruimt de wereld op. Een vertraagd privéantwoord herstelt na uitloggen geen modulescherm; `/api/me` geeft daarna 401.
- Hoge kwaliteit met effectenshader en transmissief frame zonder gerapporteerde shaderfouten. De regeling mag op de software-GPU automatisch terugschakelen.

## Herstelde fouten tijdens validatie

De eerste tussenruns vonden conflicten bij URL-fragmenten, een te vroege `inside`-melding voordat de tweede React-root het echte DOM had gekoppeld, traag uitgerekte tweens bij shadercompilatie en native drag/drop in een CSS3D-vlak. De bootstrap registreert nu vroeg, DOM-koppeling heeft een expliciete bevestiging, vluchten volgen werkelijke tijd en een beperkte pointer-adapter delegeert naar de oorspronkelijke drag/drop-acties. De definitieve betrokken controles slagen.

## Build, container en broncontrole

- Lokale browserbundel gebouwd met de gepinde npm-afhankelijkheden. Syntaxcontrole en controle op whitespace in handgeschreven wijzigingen slagen. Meegeleverde vendor-shaders/licenties worden niet handmatig geformatteerd.
- npm-audit: 0 gemelde kwetsbaarheden op het controlemoment. Dit vervangt geen onafhankelijke beveiligingsbeoordeling.
- Docker-image `roefs-one:cinematic` gebouwd. Een tijdelijke container als UID 10001 controleert health, HTML, de vroege bootstrap en HTTP-bereikbaarheid van de bundel en stylesheet. Beide SHA-256-hashes komen overeen met de uiteindelijke workspacebestanden. Geen externe poort gepubliceerd. Zie `cinematic-docker-build.txt` en `cinematic-docker-smoke.json`.
- Geen bronwijzigingen in `app.js`, `ui.js`, `enterprise.js`, `events.js`, `integrations.js`, `server.py` of `services/`. De wijziging betreft presentatiecode, stijlen, frontenddependencies, scriptvolgorde en ontwikkel-/testdocumentatie.

## Beelden en prestaties

Actuele beelden: `cinematic-desktop-final.png`, `cinematic-mobile-final.png`, `world-integrated-glass.png`. Desktop en mobiel zijn visueel bekeken. Een extra mobiele controle bevestigt dat de audioknop bereikbaar is en de gegevenstabel horizontaal schuift zonder paginabrede overflow. Het historische fase-1-bewijs staat in `phase-1/`.

De korte cloudmeting in `world-frame-sample.json` heeft circa 66,7 ms mediaan en 100 ms p95 op software-WebGL in de lichte modus. Dit is ongeveer 15 fps op deze cloudrenderer. **60 fps op middelgrote laptops en 30 fps op echte telefoons zijn niet aangetoond.** Instancing, een atlas, lagere DPR en automatische kwaliteitsverlaging zijn geïmplementeerd; fysieke apparaatmetingen blijven nodig.

Fotografische/video-assets en KTX2/Basis-/Draco-bestanden en decoders zijn niet toegevoegd. De werkende wereld gebruikt procedurele geometrie en de bestaande merkafbeelding. Een echte gecomprimeerde assetbibliotheek is een resterend onderdeel van de oorspronkelijke visuele ambitie. Safari, fysieke gyrosensoren, representatieve duurbelasting en live Render zijn niet gevalideerd. De latere GitHub-publicatie wordt apart met het commitnummer bevestigd; deze lokale controles bewijzen geen actuele Render-deployment.
