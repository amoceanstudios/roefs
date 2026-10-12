> Historisch meetpunt. Actuele migratieversie: zie V6-FINAL-FUNCTIEMATRIX.md, V6-FINAL-TESTRAPPORT.md en V6-MIGRATION-REPORT.md.

# V6 testrapport — ontwikkelstand

12 oktober 2026. Alleen fictieve gegevens. Dit document is geen eindacceptatie van een V6-FINAL.zip: die schone distributiecontrole moet nog worden uitgevoerd.

## Laatst afgeronde volledige run

`python3 run_tests.py --load`: **106 tests geslaagd in 165,295 seconden**, plus **65 oorspronkelijke API-controles**, **18 planningcontroles**, logocontrole en beide lokale belastingproeven. Geen mislukte of overgeslagen controles in die run. Ruwe uitvoer: reports/all-tests.txt en de afzonderlijke rapporten.

Daarna zijn de quarantaine-herstartcontrole en visuele/planningresize toegevoegd. Hun gerichte tests worden afzonderlijk bijgehouden; het aantal 106 wordt daarom niet als eindtest van latere code gepresenteerd.

## Afgedekte scenario’s

Bestaande rolketen van klant/contract/locaties/opdracht/materieel/planning tot uitvoering, urenbeoordeling, factuurconcept en rapport; databaseherstart en private bestanden. Negatieve serverrollen, CSRF/cookies, TOTP-hergebruik, gehashte eenmalige herstelcodes, parallel gebruik van dezelfde code, herstelrotatie, verloren authenticator, persistente accountlimiet en inactiviteit.

Planningsreeksen met uitzonderingen, atomair weigeren bij conflict, annulering/herstel met versies en herstart; dag/week/rust/pauzegrenzen en oude API-bypasscontrole. Tijdklok met dubbele start/ownership/herstart/uitklokken, factuurconceptnummering en rollback. Contractlocaties, verlenging, verkeerde klant/looptijd geweigerd, opgeslagen managementrapportcijfers.

Backups en restore, verkeerde encryptiesleutel, beschadiging, auditwijziging, bestandquarantaine, geversioneerde verwijdering en retentie. Synccontract tegen echte lokale HTTP-testserver: verloren antwoord na externe commit, idempotentie, versieconflict, uitval/hervatten, verlopen toegang, incrementeel controlepunt, workerlease en herstart. Dit zijn fictieve connectorcontracttests, geen echte leveranciersintegraties.

Chromium voert echte browserhandelingen tegen Python uit: bestaande CRUD/rollen/navigatie/tour/planning/upload, acht schermbreedten, nieuwe reeksen/instellingen/nummering, blokkeerproeven voor inline scripts en niet-toegestane interfaceacties. Niet elk toegevoegd bedieningspad heeft al een afzonderlijke browsertest; geen claim dat ieder knopscenario compleet bewezen is.

## Externe en onafhankelijke grenzen

WebKit-download faalde met HTTP 403 Domain forbidden voor cdn.playwright.dev. Safari/WebKit, fysieke iPhone/Android, screenreaderacceptatie, echte ERP-accounts, onafhankelijke pentest en duurbelasting zijn niet uitgevoerd. ClamAV-engine ontbreekt; PDF/afbeeldingen blijven daarom in quarantaine. Geen echte antivirus-succesclaim. Pakketmeldingen en prestatieresultaten staan in afzonderlijke rapporten.

## Tijdens ontwikkeling herstelde regressies

Een te brede bronvervanging voor sessiecontrole veroorzaakte een inspringfout in de demoserverroute. De gerichte teststart faalde aantoonbaar; de fout is teruggebracht tot de bedoelde authfunctie en de beveiligingstests zijn opnieuw geslaagd. Een nieuwe synctest gebruikte aanvankelijk een verkeerde fixture-eigenschap; die testfout is hersteld en alle dertien synctests slaagden daarna. Geen van deze mislukte ontwikkelpogingen wordt als geslaagde eindrun geteld.

## Hervatting: geverifieerde ontwikkeltussenstand

`python3 run_tests.py --load`: **123 tests geslaagd, 0 mislukt**, 168,362 seconden; daarnaast 65 oorspronkelijke API-controles, 18 planningcontroles, logo en beide korte loadproeven geslaagd. Uitvoer: reports/v6-resumed-full.txt. De tien scopetests betreffen uitsluitend de INACTIEVE beleidskern; ze bewijzen geen routebrede afdeling-/rayonhandhaving.

Nieuwe Chromiumtests toetsen daadwerkelijke opslag voor eindtijdresize, contractlocaties/verlenging en tijdklok (inclusief een geweigerde start). Nederlandse managementexport en CSV-formulebescherming zijn getest. BoundedHTTPServer is getest op verzadiging (503) en herstel (200).

Migratieproef: V5-commit 619db082438051d45b76d7f29615486cfc1b6536 geïnitialiseerd met tijdelijke demonstratiegegevens plus een fictieve klant. 51 bestaande tabellen vergeleken: bestaande kolommen/waarden behouden; integriteit ok, nul foreign-key-fouten; tweede initialisatie identiek. Zie reports/v6-migration.json en tools/verify_v5_migration.py. Geen migratieclaim voor een echte klantdatabase.

Dockerbasis: health, login, elf frontendbestanden inclusief events.js gecontroleerd als UID 10001. Optionele encryptie-installatie rechtstreeks tijdens Docker-build faalde op DNS, ook met hostnetwerk. Officiële wheels via werkende hostverbinding gedownload, offline in aanvullende image geïnstalleerd; daadwerkelijke manage.py-backup en restore daarin geslaagd. Zie reports/v6-docker-runtime.json en reports/v6-docker-encrypted-restore.txt. Geen uitgezette TLS-validatie.

Schone ZIP-controle volgt afzonderlijk; bovenstaande is nog geen ZIP-eindacceptatie.

## Schone tussenstand-ZIP: daadwerkelijk uitgevoerd

ZIP uitgepakt in een nieuwe tijdelijke map; alle manifestpaden, byteaantallen en SHA-256-hashes gecontroleerd. Nieuwe venv gemaakt en requirements-dev.txt plus requirements.txt daadwerkelijk geïnstalleerd. Daarin `python run_tests.py --load`: **123 tests geslaagd, 0 mislukt, 211,580 seconden**, plus 65 API-controles, 18 planningcontroles, logo en beide loadproeven. Zie reports/v6-package-validation*. Installatie gebruikte nieuw opgeloste transitieve pakketten, waaronder greenlet 3.5.6 en pycparser 3.11.

Na deze proef zijn uitsluitend documentatie en rapportbestanden bijgewerkt en is het manifest opnieuw gegenereerd. De uitvoerbare pakketinhoud wordt byte-voor-byte met de geteste ZIP vergeleken. De SHA-256 in v6-package-validation.json identificeert de oorspronkelijk geteste ZIP vóór die rapportaanvulling; de afzonderlijke SHA256-zijfile identificeert de geleverde ZIP. Dit is acceptatie van een **TUSSENSTAND**, geen afronding van de interne V6-openpunten.
