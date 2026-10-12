# V6 finale prestatiemetingen

Getest op de beschikbare Linux-cloudmachine met Python 3.12.14, loopback HTTP en SQLite/WAL. Fictieve data; geen leverancier-API, productiehardware of 250 gelijktijdige gebruikers.

## Volledige migratie via HTTP

| Categorie | Records | Daadwerkelijk bestand | Eerste import incl. upload/proefrun/bevestiging/batches (s) | Herimport ongewijzigd |
|---|---:|---|---:|---:|
| customers | 800 | CSV | 0.556 | 800 |
| employees | 250 | XLSX | 0.199 | 250 |
| objects | 2000 | CSV | 1.37 | 2000 |
| contracts | 1000 | XLSX | 0.822 | 1000 |
| workorders | 5000 | CSV | 5.411 | 5000 |
| shifts | 5000 | XLSX | 9.902 | 5000 |
| hours | 10000 | CSV | 19.355 | 10000 |

Totaal **24050 externe identiteiten**. Bemonsterde piek server-RSS **94.23 MiB** (werkelijke piek kan hoger liggen). Alle 7 gelijktijdige klantwrites tijdens proefruns gaven HTTP 201; gemeten latency 0.0055–0.0103 s. Geen zichtbare lockfout. Dit zijn korte afzonderlijke concurrerende requests, geen langdurige gemengde migratiebelasting.

Herstart en backup/herstel geslaagd; SQLite integrity_check = ok, foreign_key_check = 0 fouten. Aanvullende expliciete controles verifiëren TEXT-relaties uit de behouden legacy-tabellen. CSV én XLSX-fixtures zijn meegeleverd. Per categorie werd afwisselend één formaat op volle schaal uitgevoerd; de templateketentest verwerkt beide formaten voor alle 26 categorieën.

## Bestaande gemengde belastingproef

De actuele afzonderlijke loadproef: 100 requests, 8 gelijktijdig, 80% lezen/20% schrijven. Fouten 0, HTTP 503 0; p95 1215.43 ms, p99 1515.74 ms. Zie `reports/load-enterprise.json` en `reports/load-smoke.json` voor de meest recente exacte run. Oudere trapmetingen 1/8/16/32 blijven historische bestanden en zijn geen herhaalde eindmeting.

## Interpretatie

Geen aanleiding uit deze proef om Python/SQLite te vervangen. Schrijven blijft geserialiseerd; batches beperken de schrijftransactie, en de proefrun valideert op een tijdelijke databasekopie. Dat vermijdt een langdurige schrijflock tijdens de proefrun maar kost geheugen evenredig aan de database. Eén proefrun per serverproces begrenst gelijktijdige kopieën. Sommige ondersteunende lijsten laden nog alle rijen. Meet grotere databases, meerdere processen, echte rapportagepatronen, herstelduur en doelhardware vóór een productieoordeel.
