# V6 migratiecentrum — implementatie en bewijs

12 oktober 2026. Voortgebouwd op `42362d9fa716b433ab539169ae7d3f9f1b1bcdff`, branch `roefs-one-enterprise-v6`. Geen herbouw of databasevervanging. Python, SQLite/WAL, rollen, processen, Amocean-startscherm, eerdere synchronisatie en Cloudflare-startscripts behouden. NoCore is uitsluitend een eenmalige bron.

## Nieuw

- Native Dutch adminwizard: CSV/XLSX, deterministische mapping, inhoudstypehulp, profielen, voorbeeldrijen, volledige proefrun, expliciete bevestiging, conflictbeleid, transactiebatches van 100, controlepunten, hervatten, geschiedenis, echte aantallen en downloadverslag met beheerder/tijden/bron.
- Stabiele aparte bronidentiteiten en gevalideerde relaties. Ontbrekende ouders, dubbele bron-ID's en gewijzigde doelversies blokkeren verwerking. Geen stille overschrijving.
- 26 categorieën; 52 downloadbare en meegeleverde templates. Additieve tabellen `rooms`, `service_types`, `work_programs`, `work_instructions` met echte CRUD in de bestaande werkruimte.
- Schoolcontractdiensten: 40 expliciete fictieve lesweken, 11,5 uur/week, 460 afgesproken uren; uitzonderingen; vier expliciet te kiezen glasbezoeken met drie bestektaken. Geen verzonnen schoolkalender, starttijden of medewerkers. Generatie maakt echte Conceptwerkopdrachten en checklists, idempotent en atomair.
- Opgeslagen onboardingchecklist met verantwoordelijke, bewijs, datum, versie en afhankelijkheden. Intrekken heropent afhankelijke goedkeuringen. Niets automatisch geaccepteerd.
- Actieve serverhandhaving van configureerbare afdeling/rayonbeperkingen en beheerscherm. Negatieve HTTP-tests naast de bestaande beleidskerntests.
- Providerneutrale boekhoudinterface met goedgekeurde facturen, debiteurreferenties, outbox, statussen, herhaling, lease/idempotentiesleutel en historie. Live adapters ontbreken bewust tot provider/toegang bekend zijn.

## Herstelde fouten

1. Bestaande browseruploadtest las de werkruimte vóór de asynchrone verversing klaar was; nu wacht de assertie op het werkelijk opgeslagen bestand.
2. Een leeg optioneel noodbeschikbaarheidsveld blokkeerde import; genormaliseerd naar 0.
3. Een leeg automatisch klantnummer en een lege pauze veroorzaakten onterechte herimportconflicten; normalisatie volgt nu de doelmodellen.
4. De eerdere scopekern was niet op HTTP aangesloten; actorbinding/reset, lijstfilters/tellingen, objectcontroles, mutaties, gekoppelde payloads, exports, documenten en rapporten zijn aangesloten. Organisatiebrede vrije logboeken blijven voor beperkte accounts gesloten.
5. Backupherstel pauzeert nu ook de nieuwe boekhoudcyclus; een herstelde database verzendt niet automatisch naar een externe administratie.
6. XLSX volgt de werkmapvolgorde van het eerste gegevensblad, ook als dat fysiek niet `sheet1.xml` is.

7. Een bestandsnaam kon als HTML in de importtitel verschijnen. De titel ontsmet nu de naam; de browserregressie controleert een bestandsnaam met een img-tag.

## Daadwerkelijke migratie

`tests/migration_volume.py` genereert bestanden en gebruikt de echte HTTP-API voor upload → mapping → proefrun → bevestiging → batches. De proefrun verandert geen bedrijfsrecords. De volledige dataset omvat **24.050 records**. Dezelfde bestanden worden opnieuw verwerkt zonder duplicaten. Herstart, externe-sleutelrelaties, SQLite-integriteit, echte foreign keys en backup/herstel worden gecontroleerd. Metingen staan in `reports/migration-volume.json`; zie V6-FINAL-PERFORMANCE.md.

Voor **elk van de 26 categorieën** maakt de templateketentest een XLSX-record aan en verwerkt daarna de CSV-template als ongewijzigde herimport. Aanvullende CSV/XLSX-tests controleren ouders, updates, foutblokkades, versies, onderbreking, autorisatie en daadwerkelijke modulezichtbaarheid. De browserproef oefent handmatige kolomcorrectie, CSV én XLSX, bevestiging, downloads en bewaren na herladen.

## Grenzen

Bronbestanden zijn fictief en niet met een echte NoCore-export vergeleken. Een volledige proefrun kopieert de database in het servergeheugen; voor veel grotere databases opnieuw geheugen/belasting meten. Maximaal één proefrun per serverproces. Herstel is per gecommitteerde batch, geen globale migratie-undo. Bronbestanden worden als gevalideerde rijen en bestandshash opgeslagen; bewaar het oorspronkelijke exportbestand zelf.

Er is geen live boekhoudintegratie, fysieke mobiele acceptatie, onafhankelijke pentest of productie-duurtest bewezen. WebKit-download was door netwerkbeleid geblokkeerd. Het pakket is geschikt om een gecontroleerde fictieve proefmigratie uit te voeren; migratie van goedgekeurde echte exports vereist eerst klantafspraken, inhoudelijke aansluiting, beveiligde opslag en acceptatie. Geen productiegeschiktheidsclaim.
