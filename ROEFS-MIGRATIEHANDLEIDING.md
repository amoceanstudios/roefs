# ROEFS ONE V6 — migratiehandleiding

Deze versie bouwt verder op de bestaande Python-/SQLite-app. NoCore is een eenmalige bron, geen runtime-afhankelijkheid. Gebruik eerst uitsluitend fictieve bestanden; echte exports vereisen de afspraken en goedkeuringen in ROEFS-NODIG.md.

## Start en veilige voorbereiding

Pak het volledige bronpakket uit. Installeer Python 3.12 en voer in de projectmap uit:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python start.py
```

Windows: `py -3 -m venv .venv`, daarna `.venv\Scripts\python.exe`. De start maakt bij een nieuwe database fictieve voorbeelden en willekeurige wachtwoorden. `START.bat` en `START.command` blijven werken. Voor updates: stop de server, maak een volledige backup, pak de bron in een aparte map uit en behoud de bestaande database/documentopslag. Zie INSTALLATIE.md en V6-INSTALLATIE.md. Deel geen accountbestanden of echte data mee.

Een volledige backup en herstel in een **nieuwe** map:

```bash
.venv/bin/python manage.py backup --db data/roefs.db --output /veilige/map/voor-migratie.zip
.venv/bin/python manage.py restore --archive /veilige/map/voor-migratie.zip --target data-hersteld
```

Herstel trekt sessies in en pauzeert externe sync én automatische boekhoudverwerking. Controleer externe referenties vóór heractivering. Een bron-ZIP is geen databackup.

## Wizard: Beheer / Instellingen → Datamigratie

1. Log in als systeem- of bedrijfsbeheerder. Kies **+ Nieuwe gegevens importeren**.
2. Geef een vaste bronnaam op, bijvoorbeeld `Fictieve NoCore-export`. Gebruik bij alle vervolgbestanden exact dezelfde bronnaam. Een andere bron is een andere identiteit, niet een manier om duplicaten te omzeilen.
3. Kies de gegevenscategorie en download desgewenst de CSV- of Excel-template. Dezelfde templates staan in `templates/migration/`.
4. Upload UTF-8 CSV (eventueel BOM; komma, puntkomma, tab of pipe) of XLSX. Maximaal 10 MiB, 25.000 gegevensrijen, 100 kolommen en 2.000 tekens per cel. XLSX: het eerste werkblad in werkmapvolgorde bevat de data; geen macro's, formules of externe koppelingen. Bewaar bronidentiteiten als tekst; numerieke Excel-cellen kunnen al vóór export voorloopnullen verloren hebben. Een nul-opmaak zoals `00000` wordt ondersteund.
5. Controleer **alle** voorgestelde kolomkoppelingen. Kopnamen/synoniemen, schema, eenduidig e-mailtype en eerder opgeslagen profielen helpen; ambigue velden worden niet geraden. Niet gekoppelde kolommen worden genegeerd. Een ster markeert verplichte doelvelden.
6. `external_id` is de stabiele bronsleutel. Relatievelden bevatten de **bronsleutel van de ouder**, nooit zomaar het interne ROEFS-nummer. `existing_id` is alleen voor een expliciet gecontroleerde koppeling met een reeds bestaand doelrecord. Er wordt niet automatisch op namen samengevoegd.
7. Kies conflictbeleid: **Blokkeren** (standaard), **Behouden/overslaan** of **Expliciet bijwerken**. Lege gekoppelde velden kunnen waarden leegmaken; controleer dit in de proefrun. Uitzonderingen: leeg klantnummer laat een bestaand automatisch klantnummer staan; lege pauze betekent nul bij tijdvakken; lege noodbeschikbaarheid betekent 0.
8. Klik **Testmigratie uitvoeren**. De volledige validatie draait op een tijdelijke SQLite-kopie. De echte bedrijfsrecords blijven ongewijzigd. Proefresultaten, mapping en audit worden wel opgeslagen. Per serverproces draait maximaal één proefrun tegelijk; een tweede krijgt een Nederlandse melding (HTTP 429).
9. Los ontbrekende ouders en alle fouten op. Een profielnaam bewaart de expliciet gekozen mapping alleen na een foutloze proefrun. Download het verslag; corrigeer zo nodig het bronbestand en upload opnieuw. Een geslaagde proefrun is geen klantacceptatie.
10. Vink de bevestiging aan en kies **Definitief importeren**. De server controleert rol, jobversie, conflictregels en doelversies opnieuw. Elke batch van maximaal 100 rijen wordt atomair opgeslagen.
11. Controleer werkelijke aantallen en het verslag en open de betreffende module. Registreer inhoudelijke aansluiting en goedkeuring in **Roefs onboarding**.

## Afhankelijkheden en volgorde

De wizard toont afhankelijkheden uit de echte relaties. Importeer een ingevulde ouderreferentie eerst. Een bruikbare volgorde is klanten → contacten/locaties → ruimtes; teams → medewerkers; diensttypen → contracten → werkprogramma's → werkinstructies; open opdrachten → planning → uren. Ongekoppelde categorieën kunnen onafhankelijk worden verwerkt. Planning mag eerder als deze geen werkopdrachtreferentie bevat. Er worden geen ontbrekende ouders verzonnen.

26 ondersteunde categorieën: klanten, locaties, contracten, offertes, medewerkers, planning, uren, inspecties, logboek, open werkopdrachten, bestellingen, materieel, sleutels, voertuigen, documentmetadata, verlof, beschikbaarheid, meldingen, contacthistorie, artikelen, teams, contactpersonen, ruimtes, diensttypen, werkprogramma's en werkinstructies.

Documentimport betreft metadata; bestanden gaan via de bestaande private upload. Financiële boekingen, historische facturen en salarisregels zijn geen vrije migratiecategorie: gebruik afgestemde boekhoudprocedures. Nieuwe werkopdrachten beginnen in **Concept**; de import bootst geen historische goedkeuringen na. Uren met tijdvakken volgen de bestaande opdrachttoewijzing, overlap- en pauzeregels; legacy dagtotalen blijven mogelijk volgens het bestaande model.

## Onderbreking en herstel

Sluit de browser of herstart de app: bevestigde batches en cursor blijven behouden. Open de import in de geschiedenis en hervat. Een fout rolt uitsluitend de **lopende batch** terug; eerdere batches blijven staan. Gewijzigde doelrecords blokkeren de volgende batch. Voer na beoordeling een nieuwe proefrun uit op de resterende rijen. Kolomkoppelingen van een gedeeltelijk uitgevoerde import zijn vergrendeld; conflictbeleid kan expliciet worden herzien. Herhaal nooit blind een bestand met een andere bronnaam.

Er is geen algemene knop om een voltooide migratie met alle opvolgwijzigingen ongedaan te maken. Bij een inhoudelijk verkeerde migratie: stop mutaties, bewaar een incidentbackup en beoordeel gericht herstel of herstel van de volledige voormigratiebackup. Dat laatste vervangt ook andere latere wijzigingen; doe dit uitsluitend in de gecontroleerde herstelprocedure.

## Afdelingen/rayons en boekhouding

Beheer → **Afdelingen en rayons**: deel bestaande records bewust in en leg daarna gebruikersbeleid vast. Afdeling én rayon moeten passen als beide beperkingen zijn ingevuld. Niet ingedeelde records zijn bij een actief beleid niet zichtbaar. Nieuwe scoped records krijgen een toegestane ouderindeling of ingestelde standaard. Ook gekoppelde gegevens moeten passen. Beheeraccounts zijn organisatiebreed; de scope is geen aparte database per organisatie. Beleidswijzigingen trekken de sessies van die gebruiker in.

**Boekhoudkoppeling** bewaart providerkeuze, administratie en de naam van een beveiligde omgevingsvariabele. Vul daar nooit de sleutel zelf in. Er is nog geen live adapter geïnstalleerd. Automatisch activeren wordt daarom geweigerd. Het providerneutrale contract en outbox zijn met een mock getest, inclusief timeout na ontvangst, idempotentie, herhaling, statussen en pauzeren na backupherstel. Een echte adapter moet eerst met de gekozen leverancier worden geïmplementeerd en geaccepteerd. Een geteste en expliciet geactiveerde adapter verwerkt goedgekeurde facturen via de achtergrondcyclus (ongeveer iedere minuut zolang de app draait).

## Proefbestanden en reproduceerbare tests

`fixtures/migration/` bevat CSV én XLSX voor de fictieve volumetest: 800 klanten, 250 medewerkers, 2.000 locaties, 1.000 contracten, 5.000 opdrachten, 5.000 planningsregels, 10.000 urenregels. Dit is geen echt NoCore-schema.

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python run_tests.py --load
.venv/bin/python tests/migration_volume.py
```

Browsertests vereisen Chromium; `ROEFS_TEST_BROWSER` kan naar een geïnstalleerde binary wijzen. Zonder browser: `run_tests.py --backend-only`; dat bewijst geen UI. Bewaar originele bronexports, verslagen en goedkeuringen buiten een publiek bronrepository.
