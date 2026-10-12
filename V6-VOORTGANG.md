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
