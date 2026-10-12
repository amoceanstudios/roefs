# V6 functiematrix — nog geen eindacceptatie

PASS betekent een concreet genoemd scenario is uitgevoerd. PARTIAL betekent verdere implementatie/validatie open. BLOCKED BY CUSTOMER is alleen voor echte klantafhankelijkheden; onafhankelijke en omgevingscontroles hebben eigen status.

| Onderdeel | Status | Bewijs / grens |
|---|---|---|
| V5-modulebehoud, Amocean-start/logo, rolketen en herstart | PASS ontwikkelrun | Volledige regressie, oorspronkelijke API/planning, Chromium |
| MFA-herstelcodes, accountlimiet, sessieverval, CSRF | PASS gerichte en volledige tests | Geen onafhankelijke pentest |
| Script-CSP zonder inline/eval | PASS Chromium | Inline CSS blijft; allowlistdispatcher vereist verdere onafhankelijke review |
| Afdelings-/rayonbeleid | PARTIAL — intern open | Rollen/objectscope bestaan; configureerbare organisatiegrenzen nog niet volledig geïntegreerd |
| Auditcontroleketen | PASS scenario | Mutatie gedetecteerd; geen onveranderbaar extern auditarchief |
| Backupencryptie en restore | PASS scenario | Fernet optioneel; actieve volumes niet automatisch versleuteld |
| Scaninterface/quarantaine/verwijderen/retentie | PASS scenario | Werkende quarantainelogica; echte ClamAV-scan ENVIRONMENT BLOCKED |
| Veilige inline PDF-preview | PARTIAL — intern open | Beveiligde download; geen gescande ingebouwde preview |
| Herhaalde/meerdaagse dagsegmenten, uitzonderingen/rollback | PASS scenario | Eindige reeksen ≤100 segmenten; doorlopende nacht-/meerdaagse tijdvakken niet volledig |
| Configureerbare arbeidstijdregels | PASS scenario | Demonstratie, geen cao-/juridische validatie |
| Grafische eindtijdschuif / teamresize | PASS API + Chromium | Eindtijd met toetsenbord opgeslagen; teamconflict/rollback via API getest |
| CRM/contractlocaties/verlengbesluiten/koppelingen | PASS API-scenario | Locatie- en verlengformulier via Chromium opgeslagen; beleidsworkflow niet uitputtend gevalideerd |
| Tijdklok en bestaande urenbeoordeling | PASS API + Chromium | Startweigering, start/opslag/annulering; geen hardwareklok/extern systeem |
| Conceptnummering, Decimal/btw, credit | PASS scenario | Definitieve fiscale activering BLOCKED BY CUSTOMER |
| Managementrapporten | PASS deelberekeningen | CSV/PDF aanwezig; geen complete accounting-/financiële acceptatie |
| Automatische/incrementele sync, uitval/hervatten | PASS 13 contracttests | Eigen generiek contract; leveranciersadapters BLOCKED BY CUSTOMER |
| Nederlandse UI/toegankelijkheid/alle controls | PARTIAL | Bestaande + nieuwe Chromium-handelingtests; volledige strings-/controls-audit open |
| Oude CRUD-paginering | PASS gerichte test | Ondersteunende keuzelijsten/rapporten niet overal begrensd |
| Belasting 1/8/16/32 gelijktijdig | PASS korte proeven | Geen duurtest of 250 gelijktijdige gebruikers |
| Dependencies | PASS bekende-meldingencontrole | Geen onafhankelijke OS/container-audit |
| WebKit | ENVIRONMENT BLOCKED | Browserdownload HTTP 403 |
| Fysieke apparaten/pentest/klantacceptatie | NOT TESTED | Afzonderlijke validatie noodzakelijk |
| V5-demo-migratie / Dockerbasis / encryptieherstel | PASS scenario | 51 tabellen behouden; UID 10001; Docker-encryptie via offline wheels |
| Schone tussenstand-ZIP | PASS | Nieuwe venv/installatie; 123 tests + legacy/load geslaagd |
| Definitieve V6-FINAL | PENDING | Interne open implementatie blijft; geen productieclaim |
