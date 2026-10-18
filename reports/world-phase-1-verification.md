# Fase 1: modulewereld, definitieve controle

18 oktober 2026. Basis: bestaande V6-branch na commit `7e05463`.

| Uitgevoerde controle | Resultaat |
| --- | --- |
| `npm ci`, build en syntaxcontrole | Geslaagd; React/Three-presentatie als lokaal browserbestand |
| JavaScript-adapter- en camerabeleidtests | 7 geslaagd |
| Nieuwe wereldbrowsertests | 6 verschillende tests geslaagd; eerste vijf samen, raycasttest aanvullend en laadtest opnieuw |
| Bestaande ruimtelijke werkplek | 4 geslaagd |
| Bestaande enterprise-browsertests | 5 geslaagd |
| Bestaande klantcase, inclusief browser | 5 geslaagd |
| npm-audit | 0 gemelde kwetsbaarheden op dit controlemoment |

**27 verschillende geselecteerde tests geslaagd, 0 definitief mislukt, 0 overgeslagen.** De volledige historische suite is voor deze presentatie-uitbreiding niet opnieuw uitgevoerd.

De wereldbrowsertests controleren alle 45 toegankelijke beheermodules, bestaande route-identiteiten, geen schrijvende requests bij verkennen, WebGL-pixels op desktop/mobiel, compilatie van de volledige effectenstack zonder shaderfouten, stilstaande pixels bij reduced motion, touch, focus/lifecycle, de medewerkerrol, WebGL-fallback en vertraagd laden met een bestaande sessie.

Een eerste regressierun vond een ontbrekende startknop na cookie-herladen. Oorzaak: de grotere bundel kon later aankomen dan de oorspronkelijke boot. De presentatie-initialisatie is idempotent gemaakt. De definitieve herhaling van alle vier ruimtelijke regressietests slaagt; de nieuwe vertraagde-bundeltest slaagt eveneens.

Broncodecontrole: geen wijzigingen in `app.js`, `ui.js`, `enterprise.js`, `integrations.js`, `events.js`, `server.py` of `services/`. De bestaande backend, auth-implementatie, database en bedrijfsfuncties zijn behouden. De bestaande router wordt aangeroepen vanuit de wrapper; de eigenlijke route-implementaties zijn ongewijzigd.

Bewijslogs: `world-model-tests.txt`, `world-browser-tests.txt`, `world-raycast-tests.txt`, `world-spatial-regression.txt`, `world-enterprise-regression.txt`, `world-case-regression.txt`. `world-raycast-check.json` toont een echte canvasklik op het object Medewerkersportaal met navigatie naar de bestaande route `employeeportal`.

Beelden: `world-desktop.png` op 1440×1000, `world-mobile.png` op 390×844 en `world-effects.png` met de volledige postprocessing-stack. De cloud gebruikt software-WebGL en kiest daarom standaard de lichte weergave. De gebalanceerde voorbeeldweergave staat apart in `world-desktop-balanced.png`.

De korte framecadansmeting staat in `world-frame-sample.json`: circa 66,7 ms mediaan en 83,4 ms p95 in de uiteindelijke software-renderingrun. Dit is ongeveer 15 frames per seconde op deze cloudrenderer, **geen behaalde 60/30-fps-claim**. Een eerdere gelijktijdige browsertestrun was nog trager. De lichte modus gebruikt daarom eenvoudige geometrie, minder materialen/draw calls, lagere DPR en geen postprocessing. Werkelijke prestaties op een middelgrote laptop en moderne telefoon zijn nog niet gevalideerd; optimalisatie en apparaatmetingen blijven nodig.

Niet gevalideerd: fysieke iOS/Android-sensoren, Safari, fotografische/video-assets, KTX2/Draco-streaming, modulevluchten, module-UI in 3D, geluid en live Render. De vervolgfases en hun afbakening staan in `CINEMATIC-WORLD-PHASE-1.md`.
