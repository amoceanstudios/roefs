# V6 hervatpunt

12 oktober 2026. Werk is NIET klaar. Geen V6-FINAL.zip gemaakt of als afgerond aangeboden.

Commit: ed516d1ce3550fc113994731b18001a4eaf07622, branch roefs-one-enterprise-v6, gepusht naar origin. V5 blijft 619db082438051d45b76d7f29615486cfc1b6536 op roefs-one-enterprise-v5. Zie V6-VOORTGANG en V6-ISSUEREGISTER; begin niet opnieuw.

## Afgerond in code

MFA/herstel/sessionhardening; script-CSP + events.js; auditchain; Fernet-backups; ClamAV-interface/quarantaine/retentie; planningsregels/series/resize; tijdklok; contractlocaties/lifecycle/koppelingen; conceptnummering; managementrapportage; paginering oorspronkelijke CRUD; syncuitval/credentialpause/deltacursors. Broncode en gerichte tests staan in Git.

## Tests

Laatste volledige ontwikkelrun: `python3 run_tests.py --load` → 106 tests OK (165,295 s), 65 legacy API, 18 legacy planning, logo en twee loadproeven geslaagd. Daarna quarantaineherstart- en resizetests toegevoegd: tests/test_v6_integrity.py 5 OK, tests/test_v6_planning.py 6 OK. Specifieke nieuwe browserresize/contractbediening nog toevoegen. Geen finale bronstand- of schone V6-ZIP-claim.

Trapsgewijze load 1/8/16/32 gelijktijdig: nul fouten, p95 circa 152/1592/2004/3765 ms. JSON onder reports/. Geen 250 gelijktijdige gebruikers, duurtest of productie-SLA. pip-audit: geen bekende meldingen in opgeloste Pythonpakketten. WebKit-download 403 Domain forbidden; fysieke toestellen en onafhankelijke pentest niet uitgevoerd. ClamAV ontbreekt: binary uploads blijven in quarantaine.

## Eerstvolgende implementatie

1. Resterende configureerbare afdeling-/rayonscope architectuur en volledige routecontrole uitwerken; geen fictieve Roefs-rechtenregels activeren. Dit is nog intern werk, niet enkel een klantblokkade.
2. Tests en UX voor nieuwe contract-, resize-, klok-, retentie-, herstel- en rapportknoppen afronden; actionallowlist in events.js bij elke nieuwe functie expliciet aanvullen. Gebruik data-roefs-attributes, geen inline handlers/eval.
3. Evalueren: veilige PDF-preview na geslaagde scan, bredere rapport-/CRM-compleetheid, resterende paginering/keuzelijsten, nacht-/meerdaagse planning, contractworkflowconfiguratie en volledige Nederlandse controlsaudit. Registreer echte grenzen; presenteer onvoltooid intern werk niet als externe blokkade.
4. Schone V5→V6-migratie, laatste Docker/start/backuprestore, finale regressie/load en echte ZIP-uitpakvalidatie uitvoeren.
5. Finaliseer verplichte V6-docs, manifest en ROEFS-ONE-ENTERPRISE-V6-FINAL.zip; push dezelfde V6-branch en verifieer download. Werk cloud-startconfiguratie bij naar de geteste commit en scripts.

## Aandachtspunten voor vervolgstappen

- requirements-dev.txt neemt requirements-security.txt op voor daadwerkelijke Fernet-tests; Linux-app blijft stdlib, encryptie optioneel.
- Docker kopieert events.js/manage.py; optionele dependency via WITH_BACKUP_ENCRYPTION=1. Laatste Dockerbuild was V5; V6 nog testen.
- security_v6.migrate is additief/idempotent; scankolommen krijgen alleen bij eerste toevoeging een tekststatus. Een quarantaine mag niet bij herstart worden vrijgegeven.
- Eindtijdresize wijzigt de opdracht en alle actieve teamdiensten atomair met versies; afgesloten opdrachten zijn vergrendeld.
- Oude volledige lijst-API blijft voor compatibiliteit; oorspronkelijke CRUD-schermen gebruiken limit/offset/q. Andere ondersteunende keuzelijsten niet allemaal begrensd.
- Oude lopende lokale ontwikkelserver is niet automatisch herstart naar V6. Stop uitsluitend eigen processen; start.py maakt vooraf backup. Tests gebruiken eigen tijdelijke databases.
- Geen echte credentials, productiegegevens of publieke appdeployment. GitHub-broncode/ZIP-publicatie is wel door gebruiker geautoriseerd.
