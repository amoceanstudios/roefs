# V6 voortgang — 12 oktober 2026

V5 is behouden op commit 619db082438051d45b76d7f29615486cfc1b6536. Werk vindt plaats op roefs-one-enterprise-v6. Dit is een lopend implementatielog, geen eindacceptatie.

## Geïmplementeerd

- MFA: tien 128-bit herstelcodes, alleen hashes, eenmalig atomair verbruik, rotatie met wachtwoord + TOTP, sessies ingetrokken. Herstelcodes worden eenmaal in de interface getoond.
- Login: persistente accountbegrenzing en hercontrole van actieve account/hash/rol/MFA binnen de sessietransactie.
- Planning: atomaire meerdaagse/wekelijkse dagsegmenten, uitzonderingen, optioneel opdrachtsjabloon per segment, versies, annuleren/herstellen zonder overschrijven. Nederlandse bediening voor dienstreeksen.
- Configureerbare dag-/week-/rust-/pauzegrenzen, standaard uit; fictief profiel is niet juridisch gevalideerd. Oude en nieuwe planningsroutes gebruiken dezelfde controle.
- Auditcontroleketen met controleanker en detectie van gewijzigde/ontbrekende records. Geen claim van onveranderbaarheid tegenover volledige databasecontrole.
- Optionele Fernet-backupencryptie via cryptography, privésleutelbestand, gecontroleerd herstel. SQLite zelf blijft ongewijzigd; volumes moeten afzonderlijk beveiligd worden.
- Bestanden: configureerbare limiet, ClamAV-interface, quarantaine voor PDF/afbeeldingen zonder geslaagde scan, expliciete scanstatus, opnieuw scannen, geautoriseerde geversioneerde verwijdering. UTF-8-tekst uitsluitend als attachment; geen malwarescanclaim.
- Synchronisatie: vastgelopen verzendingen apart ter beoordeling, oorspronkelijke idempotentiesleutel behouden bij hervatten, pauzeren bij HTTP 401/403.
- Persistente tijdklok, dubbele start geweigerd, servergestuurd uitklokken via bestaande urenregels, annuleren met reden.
- Configureerbare interne conceptnummerreeks; geen fiscale activering/verzending.

## Daadwerkelijk uitgevoerde controles

- Eerste volledige ontwikkelrun: 92 tests geslaagd in 133,457 s; daarnaast 65 oorspronkelijke API-controles, 18 planningcontroles en logo geslaagd. Deze run was vóór de laatste klok/nummering/UI-aanvullingen, dus geen eindtest van de laatste bronstand.
- 12 gerichte V6-backendtests geslaagd (10,266 s): beveiliging, herstelcodes/herstart, planningsreeksen/regels, audit, encryptie, quarantaine/verwijdering, tijdklok/nummering.
- 2 nieuwe Chromium-tests geslaagd (10,504 s): reeksen via formulieren/reload/annuleren; instellingen/nummerprofiel daadwerkelijk opgeslagen.
- 10 bestaande synchronisatietests geslaagd na syncwijzigingen (12,159 s). Specifieke nieuwe uitvaltests nog toevoegen.

## Nog geen afronding

Zie V6-ISSUEREGISTER.md. Onder meer strikte CSP, afdelings-/rayonbeleid, verdere contract-/rapportagefunctionaliteit, volledige controlsaudit, schaal/paginering en de schone V6-einddistributie staan nog open. Niet als klantblokkade wegschrijven. Externe leveranciersvalidatie en klantregels zijn afzonderlijke afhankelijkheden.

## Tweede implementatieblok

- Inline JavaScript-handlers vervangen door events.js met expliciete actie-allowlist en letterlijke argumenten; script-CSP nu alleen self, geen eval/Function. Inline CSS blijft toegestaan. Volledige ontwikkelrun: 97 tests geslaagd in 147,427 s, plus oorspronkelijke controles. Dit was vóór de volgende aanvullingen.
- Contractlocaties/frequenties, geversioneerde verlenging/activering/beëindiging met reden en historie, expliciete contractkoppeling van werkopdrachten en factuurconcepten.
- Managementrapporten voor medewerkers, materieel, klanten, contracten en financiële voorbereiding met definities en rolgebonden financiële inzage; CSV/PDF.
- Paginering en zoeken in oorspronkelijke CRUD-schermen; SQL-objectscope blijft van kracht. 37 oorspronkelijke regressietests geslaagd.
- Opt-in automatische documentretentie; fysieke verwijdering na duurzaam tombstone, toekomstig bewaarde documenten blijven bestaan. 4 document-/integriteitstests geslaagd.
- Generieke incrementele synchronisatie met geadverteerde delta_tokens-capability en duurzame controlepunten; 13 synctests geslaagd inclusief uitval, verlopen toegang en herstart.
- Gesloten werkopdrachten vergrendelen nu ook wijzigingen/annulering van gekoppelde diensten.
- Sessie-inactiviteit (standaard 30 minuten, configureerbaar 5–480), HSTS uitsluitend in Secure-cookieconfiguratie, herstel van verloren authenticator met wachtwoord en ongebruikte herstelcode.
- Dependency-scan via pip-audit: geen bekende kwetsbaarheden gemeld in de 7 opgeloste Pythonpakketten (reports/v6-dependency-audit.json). Geen container-/OS-/onafhankelijke pentestclaim.
- WebKit-download opnieuw geprobeerd en mislukt (reports/v6-webkit-install.txt). Chromium-resultaten bewijzen geen Safari- of fysieke toestelwerking.

## Trapsgewijze belasting vóór laatste sessie-/contractaanvullingen

100 verzoeken per proef, 80% lezen/20% schrijven; 250 medewerkers, aanvankelijk 800 klanten, 1600 locaties en 5001 records per operationele hoofdtabel. Geen fouten of zichtbare HTTP 503 in de vier proeven.

| Gelijktijdig | Mediaan ms | p95 ms | p99 ms | RSS MB |
|---|---:|---:|---:|---:|
| 1 | 5,17 | 151,96 | 173,40 | 35,12 |
| 8 | 28,69 | 1591,95 | 1660,81 | 64,28 |
| 16 | 57,67 | 2003,88 | 2261,88 | 77,45 |
| 32 | 212,29 | 3764,51 | 3862,63 | 98,70 |

Ruwe resultaten: reports/load-enterprise-{1,8,16,32}.json. Dit zijn korte lokale proeven, geen duurtest, productieschaalgarantie of 250 gelijktijdige gebruikers.
