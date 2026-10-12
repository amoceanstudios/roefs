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
