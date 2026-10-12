# V6 — traceerbaar issueregister

Start: 12 oktober 2026. V5-rollback: `619db082438051d45b76d7f29615486cfc1b6536`, branch `roefs-one-enterprise-v5`. Werkbranch: `roefs-one-enterprise-v6`. OPEN betekent intern werk, geen klantblokkade. Severity geeft risico/prioriteit aan, geen onafhankelijke CVSS-score.

| ID | Module / ernst | Huidig → verwacht / oorzaak | Bestanden / implementatie | Teststrategie | Verificatie |
|---|---|---|---|---|---|
| SEC-01 | MFA / hoog | Verlies authenticator blokkeert herstel → eenmalige herstelcodes; ontbrekende opslag/route | mfa.py, server.py, enterprise.js; 128-bit codes, alleen hashes, atomair verbruik, rotatie | Twee gelijktijdige logins, hergebruik, onjuist wachtwoord, sessie-intrekking | PASS gerichte tests; volledige eindtest volgt |
| SEC-02 | Login / hoog | Begrenzing alleen RAM/IP → persistent per account; herstart/distributie omzeilt oude teller | security_v6.py, server.py; SQLite teller, begrensd venster | Tien fouten, correcte login geweigerd, persistentie/herstart | PASS gerichte tests; volledige eindtest volgt |
| SEC-03 | Login / hoog | Wachtwoordcontrole vóór transactie → account kan tussentijds geblokkeerd/gewijzigd zijn | server.py; actieve gebruiker, hash/rol/MFA opnieuw vergelijken onder schrijflock | Gelijktijdige accountwijziging en login | IMPLEMENTED, specifieke racetest OPEN |
| SEC-04 | Web / hoog | script-src unsafe-inline → centrale toegestane UI-acties; bestaande HTML-eventhandlers | server.py, events.js en JS-schermen; geen eval/Function | CSP + XSS + volledige Chromiumregressie | PASS ontwikkelrun; onafhankelijke review open |
| SEC-05 | Autorisatie / hoog | Organisatiebrede rolmatrix → configureerbare object-/afdelingsscope | access.py, routes.py, legacy routes; centraal beleid | Alle routes en horizontale/verticale negatieve tests | OPEN; uiteindelijke beleidskeuze klant |
| SEC-06 | Opslag / middel | Onversleutelde bestanden/backups → onderhouden optionele encryptie met sleutelherstel | manage.py, documents.py, deploymentdocs | Versleutelen/herstellen, verkeerde sleutel, beschadiging | OPEN |
| SEC-07 | Audit / middel | Auditrijen wijzigbaar → aantoonbare integriteitscontrole | common.py, server.py, migratie; integriteitsketen/verificatie | Wijziging/verwijdering detecteren | OPEN |
| DOC-01 | Documenten / hoog | Alleen signatuurcontrole, geen scanner → scaninterface/quarantaine; limiet vast 600kB | documents.py, routes.py, UI; scanstatus, veilige preview, configureerbare limiet | Malafide/ongescand bestand weigeren, rechten, storingen | OPEN |
| DOC-02 | Documenten / middel | Retentiedatum zonder uitvoering → geautoriseerde verwijdering en retentieschema | documents.py, worker, UI | Retentie/rollback, ongeautoriseerde verwijdering | OPEN |
| PLN-01 | Planning / hoog | Alleen zelfde dag/tijdvak → meerdaagse reeksen, herhaling/uitzonderingen | planning.py, migrations, enterprise.js | Overlap, verlof, materieel, annuleren/herstellen, versieconflict, herstart | OPEN |
| PLN-02 | Planning / middel | Geen configureerbare arbeidstijdregels → maxima/rust/pauzes/weeklimieten | planning.py, nieuwe regelsservice, instellingen | Grensgevallen, fictieve regels, atomair weigeren | OPEN; juridische acceptatie apart |
| PLN-03 | Planning / middel | Formulierresize/kopie → visuele resize en toetsenbordalternatief | enterprise.js/css | Pointer/toetsenbord → API/opslag/reload | OPEN |
| BIZ-01 | CRM/contract / middel | Basisrelaties → lifecycle, meerlocatiecontract, verlengworkflow, exports | routes.py, notifications.py, UI | Complete contractketen, duplicaat/import/export/paginering | OPEN |
| BIZ-02 | Uren / middel | Handmatige registratie → inklokken/uitklokken en expliciete afwijzing | timekeeping.py, UI | Dubbele klok, DST, middernacht, herstart, rechten | OPEN |
| BIZ-03 | Financieel / middel | Conceptnummer vast, beperkte kosten → configureerbare conceptnummering/kosten | finance.py, UI | Concurrentie, btw/credit, geen fiscale activering | OPEN |
| BIZ-04 | Rapporten / middel | Deelrapportages → klant/contract/materieel/financieel, exacte drilldowns | reporting.py, dashboard.py, UI | Berekenen uit opgeslagen fixtures, filters, PDF/CSV | OPEN |
| SYN-01 | Sync / hoog | Outbox/retries aanwezig; geen dead-letter/incremental adaptercontract | synchronization.py, connectors, integrations.js | Fault recovery, verlopen tokens, cursor, hervatten/dead-letter | OPEN; echte leveranciers BLOCKED BY CUSTOMER |
| UX-01 | Interface / middel | Nederlands/emulatie aanwezig → volledige strings/controls-audit, a11y, WebKit | Alle JS/CSS, browsertests | Elke handeling met API/db/reload; 8 breedten, focus/reduced-motion | OPEN; fysieke apparaten NOT TESTED |
| PERF-01 | Schaal / middel | Oude lijsten onbegrensd; 8 requests concurrentie → paginering, trapsgewijze belasting/p99 | routes.py, server.py, UI, loadtests | 250 medewerkers/800 klanten/duizenden regels, latency/locks/CPU/RSS | OPEN |
| REL-01 | Distributie / hoog | V5 schoon getest → V6 migratie/backup/restore/schone ZIP opnieuw bewezen | tests, builder, docs, Docker | Volledige operationele keten, restart, rollen, alle regressies | OPEN |

## Voortgang

- V5-rapporten gelezen en vergeleken met MFA/login/planning/documentcode; bestaande werkende architectuur behouden.
- SEC-01/02/03 geïmplementeerd; geen eindacceptatie vóór tests.
- V5 kende 82 tests; dit is historische baseline, geen V6-testuitslag.

## Aanvullende bevindingen tijdens V6

| ID | Module / ernst | Huidig → verwacht / oorzaak | Bestanden / implementatie | Teststrategie | Verificatie |
|---|---|---|---|---|---|
| SEC-08 | Bestandsmigratie / hoog | Nieuwe quarantaine kon bij herstart voor tekst opnieuw worden vrijgegeven → scannerstatus behouden; initialisatie draaide te breed | security_v6.py; alleen bij eerste toevoeging van scankolommen initialiseren | Tekst in quarantaine, herstart, download blijft 423 | PASS gerichte test |
| SEC-09 | Planning / hoog | Dienst van goedgekeurd werk kon via planning worden geannuleerd → afgesloten werk vergrendeld | planning.py; vorige opdrachtstatus controleren vóór mutatie | Goedgekeurde opdracht annuleren via shift-API → 409 | PASS gerichte test |
| SEC-10 | Sessies / middel | Geen inactiviteitslimiet → persistente last_seen naast absolute levensduur | security_v6.py, server.py, manage.py | Verlopen idle-sessie → 401 en verwijdering; restore zonder verweesde sessiedata | PASS gerichte test; laatste totale run 106 tests |
| PLN-04 | Teamplanning / middel | Gekoppelde eindtijd alleen na annuleren wijzigen → atomair oudertijdvak en alle teamdiensten aanpassen | planning.resize, routes, schuifbediening | Conflict draait ouder+diensten terug; versieconflict geweigerd | PASS 6 planningtests; browserresize nog open |

Open regels in het oorspronkelijke register zijn geen actuele eindstatusclaim; V6-FUNCTIEMATRIX en V6-VOORTGANG beschrijven de inmiddels gerealiseerde deelimplementaties. Bij afronding moeten alle regels een afzonderlijke eindstatus krijgen.

## Hervatting — afzonderlijke verificatie

| ID | Uitkomst in deze tussenstand | Bewijs |
|---|---|---|
| SEC-05 | PARTIAL: scopebeleidskern voorbereid, bewust inactief; routebrede integratie nog OPEN | 10 kern-tests; geen HTTP-scopeclaim |
| SEC-11 | PASS: gelijktijdige HTTP-werkers begrensd, overbelasting geeft 503/Retry-After en herstelt | tests/test_v6_http.py |
| UX-02 | PASS: mislukte klokstart houdt formulier en invoer vast; navigatie alleen na succesvolle opslag | tests/test_v6_browser.py |
| PLN-04 | PASS voor resizeschuif met toetsenbord/opslag en bestaande API-teamtests | tests/test_v6_browser.py, test_v6_planning.py |
| BIZ-01 | PASS voor contractlocaties en verlengbesluit via mobiele Chromium; overige scope blijft PARTIAL | tests/test_v6_browser.py |
| BIZ-04 | PASS voor Nederlandse management-CSV/PDF en formulebescherming; financiële acceptatie blijft open | tests/test_v6_operations.py |
| REL-01 | PASS voor V5-demomigratie en Dockerbasis/versleuteld herstel; FINAL blijft OPEN | reports/v6-migration.json, v6-docker-runtime.json, v6-docker-encrypted-restore.txt |

## Actuele migratiesprint — vervangt bovenstaande openstatus waar vermeld

SEC-05 is technisch aangesloten: actorbinding/reset, scopebeleid en indelingen in beheer, lijsten/tellingen/lookups, directe mutaties, gekoppelde payloads, planning, exports/rapporten/documenten en negatieve HTTP-proeven. Klantspecifieke recordindeling en onafhankelijke securityacceptatie blijven nodig. Zie V6-FINAL-SECURITY.md en tests/test_scope_http.py.

Het centrale CSV/XLSX-migratiecentrum, nieuwe operationele doelmodellen, templates, onboarding en providerneutrale boekhoudvoorbereiding zijn geïmplementeerd. NoCore is geen blijvende operationele afhankelijkheid. Zie V6-MIGRATION-REPORT.md voor bewijzen en grenzen. De finale testuitslag staat in V6-FINAL-TESTRAPPORT.md; oude meetpunten hierboven blijven historisch.
