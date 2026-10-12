# Baseline vóór V5

11 oktober 2026, commit e914d1549ad2102a2e6311bd6ddea036b57179b3. Alle 45 manifestbestanden gecontroleerd; geen bronwijzigingen aangetroffen. Snapshot en consistente SQLite-backup staan privé buiten het project in /workspace/roefs-recovery-v5. Het snapshot bevat lokale demoaccounts en hoort niet in de distributie.

Uitgevoerd: `python3 run_tests.py --load`. PASS: 65 oorspronkelijke API-controles, 18 planningcontroles, logo-controle, 51 unittests (waaronder 10 Chromium-tests), 24/24 leesverzoeken met vier gelijktijdige clients. 250 fictieve medewerkers, 800 klanten, 1250 diensten; mediaan 423,4 ms, maximum 1283,1 ms. Dit bewijst geen productiecapaciteit.

| Bestaand onderdeel | Klasse | Bevinding |
|---|---|---|
| 21 modules: eenvoudige CRUD, validatie, opslag | A | Regressietests, herstel na herstart |
| Persoonlijke scope, admin/medewerker | A | Servercontroles en escalatietests |
| Amocean-start, menu, logo, navigatie | A | Chromium; geen echte iOS/Android-test |
| Planning week, overlap, verlof, beschikbaarheid | A | Gemeenschappelijke serverregels |
| Suggesties | C | Geen kwalificaties, teams, materieel of betrouwbare reistijd |
| CRM, contracten, materieel | C | Basisvelden; geen volledige procesketen |
| Werkbon, uren, factuur | C | Losse CRUD; ontbreken statusmachine, tijdintervallen en factuurregels |
| Documenten | C | Alleen metadata, geen bestandsopslag |
| Berichten en widgets | A | Opgeslagen berichten en regelgebaseerde inzichten |
| Rondleiding | C | Contextueel, geen opgeslagen voortgang |
| Negen rollen, cookieauth, CSRF | E | Twee rollen en bearer-sessies |
| Certificeringen, reserveringen, meldingen | E | Ontbreken |
| Drag/drop, maandweergave, bulk, versieconflicten | E | Ontbreken |
| Publieke Cloudflare-verificatie | F | DNS voor tunnelservice in omgeving geblokkeerd |
| Volledige E2E, duurbelasting, Safari, herstel-oefening | E | Geen bewijs voor uitgebreide scope |

Afhankelijkheden: server.py → domain.py → SQLite; app.js → ui.js → HTTP. start.py → server.py, optioneel cloudflared. Browser gebruikt geen bedrijfsdata als gezaghebbende lokale opslag. Grootste risico's: monolithische routes, beperkte rollen, onvoorwaardelijke updates, alle tabellen in geheugen, inline scripts/CSP, bekende fallbackwachtwoorden bij direct server-starten. Geen aanwijzing voor noodzaak SQLite te vervangen.
