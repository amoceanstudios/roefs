# Database en herstel

SQLite blijft de gezaghebbende bedrijfsopslag. Elke toepasselijke verbinding zet foreign keys aan; WAL, transacties en een busy-timeout van 15 seconden beperken schrijfconflicten. Bewaar de database op een betrouwbare lokale schijf, niet op een gedeeld netwerkbestandssysteem.

## Additieve migraties

`schema_migrations` registreert versies. Bij opstart wordt vooraf via `start.py` een consistente SQLite-backup gemaakt.

- V5: `version` op alle 21 bestaande tabellen; CRM-, contract-, medewerker-, werkopdracht-, uren- en factuurkolommen. Nieuwe tabellen voor teams, contacten, certificaten, checklists, reserveringen, statushistorie, planningshistorie, factuurregels, bestanden, meldingen, voorkeuren en reistijden.
- V6: artikelen, connectorconfiguraties, recordkoppelingen, synchronisatieruns, gebeurtenissen, conflicten, duurzame outbox; artikelreferentie op bestellingen.
- V7: TOTP-instellingen en per-account hash-iteraties.
- V8: handmatige contacthistorie, snapshots vóór synchronisatieconflictoplossing en aanvullende zoekindexen.

Nieuwe relationele tabellen gebruiken gedeclareerde foreign keys en unieke indexen waar passend. De historische tekst-ID’s zijn niet destructief herbouwd; zij blijven door servervalidatie beschermd. Handmatige SQL kan de historische applicatieregels omzeilen. Er is geen automatische reparatie/verwijdering van bestaande inconsistente gegevens.

Uniek: klantnummer indien ingevuld, artikelcode, certificaat per medewerker/naam, teamnaam, meldingssleutel per ontvanger, factuurvoorbereiding per werkopdracht en synckoppeling per externe én lokale identiteit. Factuurnummers in oude records blijven applicatiegevalideerd.

## Private volledige backup

```bash
python3 manage.py backup --db data/roefs.db --output /veilige/map/roefs-backup.zip
python3 manage.py restore --archive /veilige/map/roefs-backup.zip --target data-hersteld
```

Backup maakt eerst een SQLite-snapshot, controleert integriteit, kopieert alle bestanden waarnaar die snapshot verwijst en schrijft SHA-256-controlesommen. Bestanden zijn onveranderlijk; aanmaak en referentieopslag worden gecoördineerd. De backup bevat accounts, hashes, TOTP-geheimen, bedrijfsgegevens en bestanden: behandel hem als vertrouwelijk. Omgevingsvariabelen met externe API-tokens worden niet meegenomen.

Herstel weigert een bestaande doelmap, paden buiten de toegestane structuur, dubbele ZIP-namen, een totale uitgepakte grootte boven 1 GB en afwijkende controlesommen. Na herstel worden sessies ingetrokken en externe koppelingen gepauzeerd. Controleer uitstaande outbox/conflicten en het externe systeem vóór heractivering; herstel mag geen onverwachte verzending starten.

Start een herstelde demo met `ROEFS_DB=/absoluut/pad/data-hersteld/roefs.db python3 start.py`. Gebruik geen losse oude WAL/SHM-bestanden. De per-startbackup bevat alleen de database; gebruik `manage.py` voor database plus documenten. Geen automatische verwijdering van backups; configureer een bewaarbeleid buiten de app. Documentbewaartermijnen worden opgeslagen maar bestanden worden niet ongemerkt vernietigd.

## Controle

`PRAGMA integrity_check` en `PRAGMA foreign_key_check` worden in herstel- en belastingtests uitgevoerd. SQLite voldoet in de uitgevoerde lokale proef, maar die is geen bewijs voor 250 gelijktijdige gebruikers, multi-hostwrites, langdurige belasting of productiegeschiktheid.
