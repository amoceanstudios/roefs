# V6 tussenstand installeren

Dit pakket bouwt voort op V5. Het is **geen afgeronde V6-FINAL of productieverklaring**. Lees V6-FUNCTIEMATRIX.md en V6-CONTINUATION.md voor open implementatie en validatie. De voorbereide afdeling-/rayonmodule is inactief; bestaande serverrollen blijven van kracht.

1. Pak de ZIP uit in een nieuwe map. Behoud de bestaande V5-map en database als rollback.
2. Gebruik Python 3.10+ (hier getest met 3.12.14). Installeer `python3 -m pip install -r requirements.txt`; op Linux zijn voor de basisapp geen extra runtimepakketten nodig.
3. Start `python3 start.py --quiet`. Het startscript genereert bij eerste gebruik fictieve demoaccounts en bewaart de private wachtwoorden in `data/demo-accounts.json`. Bewaar dit bestand privé. `python3 start.py --check --quiet` start, controleert HTTP/database en stopt weer.
4. Open lokaal `http://localhost:8765`. Gebruik de oorspronkelijke dagelijkse Amocean-startpagina. Gratis tunnel: bestaand `START-GRATIS-24U.command` of `python3 start.py --tunnel`. De client blijft ondersteund; een daadwerkelijke tunnelregistratie kon hier niet worden gevalideerd wegens DNS/netwerkbeperking.
5. Voor automatische tests: `python3 -m pip install -r requirements-dev.txt`; installeer Chromium met Playwright of wijs `ROEFS_TEST_BROWSER` naar een geschikte systeembrowser. Voer `python3 run_tests.py --load` uit. Dit gebruikt tijdelijke fictieve databases. `--backend-only` voert geen browsertests uit.

## Bestaande gegevens behouden

Stop de eigen app voordat je naar de nieuwe bronmap overschakelt. Maak eerst met `manage.py backup --db <database> --output <nieuw-backup.zip>` een consistente backup inclusief bijlagen. Herstel met `manage.py restore --archive <backup.zip> --target <nieuwe-datamap>`. Start V6 met `ROEFS_DB` naar de herstelde `roefs.db`. Herstel wist sessies en pauzeert externe koppelingen bewust; beoordeel deze vóór opnieuw activeren. Een migratie van een tijdelijke V5-demodatabase is getest; dit vervangt geen proef met een geschoonde representatieve klantbackup.

## Optionele backupencryptie

Installeer `requirements-security.txt`. Maak met `python3 manage.py generate-backup-key --key-file <privé-sleutelbestand>` een sleutel en gebruik `--key-file` bij backup en restore. Bewaar de sleutel apart; zonder sleutel kunnen backups niet worden hersteld. Op Unix vereist de sleutel beperkte bestandsrechten (0600).

Docker: `docker build -t roefs-one:v6 .`. De basisimage werkt zonder pip-runtimepakket. `--build-arg WITH_BACKUP_ENCRYPTION=1` vereist tijdens bouwen toegang tot PyPI. Hier faalde die download door Docker-DNS; dezelfde officiële wheels zijn via de werkende hostverbinding opgehaald en zonder internet in een aanvullende image geïnstalleerd. Backup en restore in die image zijn daadwerkelijk getest als UID 10001. Zie reports/v6-docker-encrypted-restore.txt. TLS-controle is niet uitgeschakeld.

## Configuratie en grenzen

- `ROEFS_MAX_REQUEST_WORKERS`: 4–128, standaard 64; bij bezetting HTTP 503 met `Retry-After`.
- `ROEFS_SESSION_IDLE_MINUTES`: standaard 30; daarnaast blijft de absolute sessieduur gelden.
- `ROEFS_UPLOAD_MAX_BYTES`: standaard 600000, maximaal 10000000. PDF/afbeeldingen blijven in quarantaine zonder geslaagde scannercontrole.
- Integraties zijn standaard inactief. Zie INTEGRATIES.md voor generiek API-contract, leidende systemen, conflicten, uitvalwachtrij en incrementele cursors. Echte leverancierskoppelingen vereisen hun API-contract en bevoegde toegang.
- Arbeidstijdregels zijn configureerbare demonstratieregels, geen juridisch gevalideerd cao-profiel.
- Gebruik uitsluitend fictieve gegevens in deze cloudontwikkelomgeving.
