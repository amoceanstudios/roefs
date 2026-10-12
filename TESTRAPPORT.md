> Historisch meetpunt. Actuele migratieversie: zie V6-FINAL-FUNCTIEMATRIX.md, V6-FINAL-TESTRAPPORT.md en V6-MIGRATION-REPORT.md.

# Testrapport — V5 en automatische synchronisatie

12 oktober 2026. Alleen fictieve gegevens. Tests gebruiken eigen tijdelijke databases en lokale HTTP-servers. Ruwe uitvoer: `reports/all-tests.txt` en afzonderlijke rapporten. Distributiecontrole: `reports/package-check.txt`.

## Uitgevoerde controles

Vanuit een schoon uitgepakte distributie zijn **82 tests geslaagd** (153,866 s), plus **65 oorspronkelijke API-controles**, **18 oorspronkelijke planningcontroles**, de logocontrole en beide belastingproeven. Geen mislukte of overgeslagen tests. Vers opstarten en opnieuw starten met reservekopie zijn eveneens geslaagd. Geen productiegeschiktheid vastgesteld.

Gedekt: oorspronkelijke modules; accountkoppeling/eigenaarschap/rollen, CSRF/cookies, sessies/TOTP; planningoverlap, afwezigheid, certificaten, materieel, batchrollback/versies; checklist, private bestanden, uren/DST/middernacht, beoordeling/factuurbedragen; klantimport/herstart; backup/herstel; automatische sync met echte lokale test-API, dubbelpreventie, twee kanten gewijzigd, If-Match, verloren antwoord, backoff/lease/herstart.

Browsertests gebruiken echte Chromium tegen Python, geen gemockte bedrijfs-API. Acht breedten: 320, 375, 390, 430, 768, 1024, 1440 en 1920 px. Navigatie, touchconfiguratie, focus, formulieren, opgeslagen XSS, rondleiding, werkruimte, checklist/upload, planningskopie en inactieve connectorconfiguratie zijn gecontroleerd. Geen Safari/WebKit of fysieke toestellen.

## Procesketen

`test_full_role_chain_persists_restart`: fictieve klant met twee locaties/contract, team/medewerker/VCA/machine, opdracht, planner kiest geschikte medewerker, medewerker start/checklist/bestand/3,5 uur na pauze/afronding, leidinggevende keurt werk en uren, financieel beheer bereidt en beoordeelt concept, directeur leest rapport en andere medewerker wordt geweigerd. Netto 3,5 × 35,25 + 2 × 3,10 = 129,58; btw 27,21; totaal 156,79. Na herstart blijven workflow, bedrag, bestanden en rapport behouden. Backendketen en afzonderlijke browserhandelingen getest; niet de hele keten op elk fysiek apparaat.

## Belasting

250 medewerkers, 800 klanten, 1600 locaties, 5001 werkopdrachten/diensten/urenregels per tabel inclusief oorspronkelijke demo. 100 verzoeken, concurrency 8, 80% lezen/20% schrijven. Na de 20 inserts zijn er 820 klanten.

Eerste p95: 7204,95 ms. Losse rapportvragen per dienst en onnodig uitlezen van opdrachten zijn verminderd. Zware rapportberekeningen worden gecoördineerd om SQLite/Python-threadcontention te beperken. Actuele cijfers: `reports/load-enterprise.json`; eerste meting: `reports/load-enterprise-before-optimization.json`.

Geen duurtest, 250 gelijktijdige gebruikers of productiehardware. Contention via zichtbare HTTP 503; interne wachttijd niet apart gemeten. RSS bemonsterd; CPU omvat serverleven met startup/fixtures. Geen productie-SLA.

## Gevonden fouten en grenzen

Tijdens ontwikkeling hersteld: rollenlijst selecteerde onbedoeld beheer; tour sluiten wachtte op netwerk; beperkte rollen konden via oude routes beheerberichten/medewerkersdetails zien. De laatste volledige uitvoer is leidend voor eindresultaten.

Echte leveranciers, publieke tunnel, onafhankelijke pentest, juridische/fiscale beoordeling, e-mail/push, duurbelasting, Safari en fysieke telefoons zijn BLOCKED/NOT TESTED. Zie FUNCTIEMATRIX.md; hiervoor worden geen resultaten verzonnen.
