# V6 — traceerbaar issueregister

Start: 12 oktober 2026. V5-rollback: `619db082438051d45b76d7f29615486cfc1b6536`, branch `roefs-one-enterprise-v5`. Werkbranch: `roefs-one-enterprise-v6`. OPEN betekent intern werk, geen klantblokkade. Severity geeft risico/prioriteit aan, geen onafhankelijke CVSS-score.

| ID | Module / ernst | Huidig → verwacht / oorzaak | Bestanden / implementatie | Teststrategie | Verificatie |
|---|---|---|---|---|---|
| SEC-01 | MFA / hoog | Verlies authenticator blokkeert herstel → eenmalige herstelcodes; ontbrekende opslag/route | mfa.py, server.py, enterprise.js; 128-bit codes, alleen hashes, atomair verbruik, rotatie | Twee gelijktijdige logins, hergebruik, onjuist wachtwoord, sessie-intrekking | PASS gerichte tests; volledige eindtest volgt |
| SEC-02 | Login / hoog | Begrenzing alleen RAM/IP → persistent per account; herstart/distributie omzeilt oude teller | security_v6.py, server.py; SQLite teller, begrensd venster | Tien fouten, correcte login geweigerd, persistentie/herstart | PASS gerichte tests; volledige eindtest volgt |
| SEC-03 | Login / hoog | Wachtwoordcontrole vóór transactie → account kan tussentijds geblokkeerd/gewijzigd zijn | server.py; actieve gebruiker, hash/rol/MFA opnieuw vergelijken onder schrijflock | Gelijktijdige accountwijziging en login | IMPLEMENTED, specifieke racetest OPEN |
| SEC-04 | Web / hoog | script-src unsafe-inline → geen onnodige inline uitvoering; bestaande HTML-eventhandlers | server.py, app.js, ui.js, enterprise.js, integrations.js; handlers migreren | CSP + XSS + browserregressie | OPEN |
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
