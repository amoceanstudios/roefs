# V6 beveiligingsrapport — tussentijdse stand

Geen onafhankelijke pentest of productiegeschiktheid vastgesteld. Zie V6-ISSUEREGISTER.md voor open intern werk.

## In code gerealiseerd

- MFA-herstel: tien onafhankelijke 128-bit codes, SHA-256 met accountbinding, één keer getoond, atomair verbruikt onder SQLite-transactie. Rotatie trekt sessies in. Verloren authenticator ontkoppelen is een expliciete login-keuze en vereist wachtwoord plus ongebruikte herstelcode; oude codes vervallen.
- Persistente limiet van tien accountpogingen per vijf minuten, naast bestaande IP-/naambegrenzing. Dit kan doelbewuste tijdelijke accountblokkering niet geheel voorkomen; geen permanente automatische blokkade.
- Hash/actief/rol/MFA opnieuw gecontroleerd vóór sessieafgifte. Session cookie blijft HttpOnly/SameSite=Strict; Secure bij HTTPS/tunnel. Standaard dertig minuten inactiviteit naast de bestaande acht uur absolute levensduur.
- Script-CSP zonder unsafe-inline/eval. events.js gebruikt alleen geregistreerde UI-acties en beperkte letterlijke argumenten; HTML kan geen JavaScript uitvoeren. Inline stijlen zijn nog toegestaan. Geen algemene JS-interpreter of Function-constructor.
- Auditcontroleketen met externe ankerexport. Detecteert wijzigingen/verwijderingen ten opzichte van de keten. Volledige databasecontrole kan beide tabellen herschrijven; een extern bewaard anker en onafhankelijk logarchief blijven nodig voor sterkere garanties.
- ClamAV-interface: PDF/afbeeldingen zonder succesvolle scan blijven ondownloadbaar. ClamAV ontbreekt hier; geen geslaagde echte malwarescan geclaimd. UTF-8-tekst wordt als attachment met nosniff aangeboden, expliciet zonder antivirusclaim.
- Geversioneerde documentverwijdering, opt-in retentiescheduler, private opslag, bestandslengte en hashcontrole. Backups hebben een afzonderlijk bewaarbeleid nodig.
- Optionele Fernet-backupencryptie via cryptography 50.0.0. Gecontroleerd herstel, onjuiste sleutel en beschadiging getest. Dit versleutelt backups, niet automatisch de actieve SQLite-database of uploadmap.

## Backupencryptie en sleutelbeheer

Installeer `python3 -m pip install -r requirements-security.txt` indien encryptie wordt gebruikt. Bewaar sleutels buiten broncode, database, ZIP en backupbestemming:

```bash
python3 manage.py generate-backup-key --key-file /veilige/aparte/map/backup.key
python3 manage.py backup --db data/roefs.db --output /veilige/backups/roefs.enc --key-file /veilige/aparte/map/backup.key
python3 manage.py restore --archive /veilige/backups/roefs.enc --target data-hersteld --key-file /veilige/aparte/map/backup.key
```

Sleutelbestand op Unix: alleen eigenaar toegang (0600). Verlies maakt ontsleutelen onmogelijk. Bewaar een afzonderlijke gecontroleerde herstelkopie in de gekozen secretbeheerder. Rotatie: genereer een nieuwe sleutel voor nieuwe backups; bewaar oude sleutels zolang bijbehorende backups nodig zijn. Test herstel vóór oude sleutels worden vernietigd. Tijdelijke ontsleutelde bestanden staan in een private tijdelijke map en worden verwijderd; wissen van SSD-blokken wordt niet gegarandeerd. Gebruik voor actieve data/backups een beheerd versleuteld volume (bijvoorbeeld LUKS/BitLocker of cloudvolume-encryptie), waarvan inrichting en sleutelbeheer bij de infrastructuurkeuze horen. Geen eigen SQLite-cryptografie toegevoegd.

Docker kan de optionele backupafhankelijkheid meenemen met `--build-arg WITH_BACKUP_ENCRYPTION=1`. Sleutels uitsluitend runtime als private mount aanleveren.

## Uitgevoerde pakketcontrole

pip-audit meldde geen bekende kwetsbaarheden in Playwright 1.62.0, cryptography 50.0.0 en de vijf opgeloste indirecte afhankelijkheden. Ruwe JSON: reports/v6-dependency-audit.json. Dit is een momentopname van bekende meldingen, geen bewijs van afwezigheid van kwetsbaarheden. OS/container/CSP-stijlen, volledige objectbeleid-audit en onafhankelijke aanvallersvalidatie blijven afzonderlijke controles.
