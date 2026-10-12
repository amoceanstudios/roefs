> Historisch meetpunt. Actuele migratieversie: zie V6-FINAL-FUNCTIEMATRIX.md, V6-FINAL-TESTRAPPORT.md en V6-MIGRATION-REPORT.md.

# Functiematrix V5 en synchronisatie

PASS: genoemd scenario uitgevoerd en geslaagd. PARTIAL: werkende deelimplementatie, bredere mastereis nog niet compleet. BLOCKED: externe voorwaarde ontbreekt. NOT TESTED: geen uitgevoerde validatie. Geen voltooiingspercentages.

| Eis/onderdeel | Status | Bewijs / grens |
|---|---|---|
| Oorspronkelijke 21 CRUD-modules en behoud data | PASS | Oude API/regressies, migratie en herstart |
| Amocean-eerste scherm, logo, navigatie | PASS | Echte Chromium-tests en screenshots |
| Actuele dagelijkse tellers en doorklikselecties | PASS | Home/scope-test, geen fictieve productiegetallen |
| CRM, locaties, contacten, audit, duplicaten, import | PASS | CRUD, atomaire import, twee locaties in keten en browserformulier |
| Volledige CRM-/contractfunctionaliteit | PARTIAL | Handmatige contacthistorie; geen e-mailconnector of complexe contractmodellen |
| Opdrachtstatusmachine en verplichte checklist | PASS | Concept tot Factureerbaar, bevoegdheden en gesloten-recordbescherming |
| Planning overlap/verlof/beschikbaarheid | PASS | Negatieve tests, gelijktijdige mutaties |
| Teams, certificaten, materieel, suggestieredenen | PASS | Gekoppelde keten, uitsluitingen en reserveringscontrole |
| Dag/week/maand, groepering, kopie, batch, versie/undo | PARTIAL | Werkend; niet elke drag/dropcombinatie getest; complexe terugkeerpatronen/rand-resize ontbreken |
| Uren, pauze, DST, middernacht, beoordeling | PASS | Echte HTTP-tests, expliciete offsets, overlap/duplicaten |
| Mobiele uitvoering, bestand, aftekennaam, PDF | PASS | Rolketen plus browserchecklist/upload; geen gekwalificeerde handtekening |
| Voertuigen/materieel volledig beheer | PARTIAL | CRUD, keuring/onderhoud/reservering; geen onderhoudswerkplaatsadministratie |
| Decimal factuurregels, btw, concept, review, export | PASS | Exacte totaalcontrole in E2E, echte PDF/CSV, dubbele voorbereiding beschermd |
| Volledige boekhouding/fiscale facturatie | PARTIAL | Credit en handmatige kostenregels; geen fiscale certificering, bank of definitieve nummerreeks |
| Private documenten en downloadrechten | PASS | Pad/type/scope/checksum/backup-tests |
| Volledig documentmanagement | PARTIAL | Geen antivirus, gekwalificeerde ondertekening of retentievernietiging |
| Rapportage en lokale schaaldata | PARTIAL | Berekeningen, filters, PDF/CSV; niet alle managementrapporten |
| Interne meldingen, voorkeur, gelezen, deduplicatie | PASS | Scope/opslag/deduplicatie; dagelijkse deadlineworker |
| Externe e-mail/push | BLOCKED | Geen providerconfiguratie; uitgeschakeld |
| Negen rollen, serverrechten en objectscope | PASS | Role-chain en negatieve legacy/V5-tests |
| Afdelings-/rayonrechten en privacyacceptatie | PARTIAL | Organisatiebrede rollen; definitieve veld-/rayonscope ontbreekt |
| Cookie/CSRF, sessies, PBKDF2, TOTP | PASS | Sessies, CSRF-negatief, TOTP-hergebruik en intrekking |
| Strikte CSP, onafhankelijke pentest/SSO/MFA-herstel | NOT TESTED | Geen aanwezigheid of validatie geclaimd |
| Nederlands en acht schermbreedten | PASS | Chromium 320/375/390/430/768/1024/1440/1920; geen fysieke toestelclaim |
| Rondleiding en opgeslagen voortgang | PASS | Echte schermen, bediening en voorkeurbehoud |
| Instellingen en workflow-editor | PARTIAL | Organisatie/gewichten/retentie/rollen; geen vrije workflowbouwer |
| Consistente backup en herstel met bestanden | PASS | Werkelijk hersteld, checksums en sessie-intrekking |
| Volledige geteste procesketen en herstart | PASS | Klant/2 locaties/contract/team/certificaat/materieel/checklist/uren/beoordeling/factuur/directeur/geweigerde gebruiker |
| Automatische generieke synchronisatie | PASS | Lokale HTTP-testserver, worker en herstart zonder handmatige run |
| Tweerichtingsverkeer en systeemvoorrang | PASS | Eén kant gewijzigd, beide kanten, niet-leidende wijziging |
| Synckoppelingen, retries, duurzame outbox | PASS | Verloren antwoord na externe commit geeft één extern record |
| Syncfouten, leases, conflicten, verwijderbeleid | PASS | Storing/backoff, versieconflict, één worker, behoud brondata |
| Leverancierspecifieke ERP/CRM-adapters | BLOCKED | Toegang/OAuth/schema/mapping ontbreken; profielen zichtbaar inactief |
| Uitgebreide V5-data extern mappen | PARTIAL | Basisvelden; rijke workflow/factuurregel/documentmapping vereist apart contract |
| Docker zonder root en assets | PASS | Build, startup/login, UID 10001 en statische antwoorden |
| Gratis Cloudflare publieke end-to-end | BLOCKED | Eerder gemeten DNS/netwerkbeperking; V5 niet publiek blootgesteld |
| Fysieke iPhone/Android, Safari, Windows/macOS | NOT TESTED | Chromium is geen toestel-/platformtest |
| Productiegeschiktheid | NOT TESTED | Geen onafhankelijke beveiligings-, leveranciers- en duurbelastingacceptatie |
