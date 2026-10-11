# Architectuur en beoordeling

## Uitgangspunt en bestandsanalyse

Alle elf bestanden uit de aangeleverde ZIP zijn beoordeeld: `server.py`, `index.html`, `assets/amocean-mark.png`, `README.md`, `MOBIEL-TESTPLAN.md`, `START-GRATIS-24U.command`, `Dockerfile`, `.dockerignore`, `test_api.py`, `test_planning.py` en `TEST-HERSTEL.py`. De ZIP bevatte geen databasebestand, dependency-lockfile, CI-configuratie of AGENTS.md. Documentatieclaims over vroegere tests zijn opnieuw gecontroleerd en gelden niet automatisch als bewijs voor deze versie.

De oorspronkelijke app is een compacte monoliet: Python `ThreadingHTTPServer`, routering in `Handler`, SQLite met WAL en generieke tabellen met tekstvelden. De frontend is JavaScript zonder framework, met HTML-rendering en `fetch`, oorspronkelijk volledig in één HTML-bestand. Er zijn geen externe bedrijfs-API's gekoppeld. “Slimme” analyses zijn vaste regels, geen generatief model. De standaardpagina blijft de oorspronkelijke Amocean-dagstart.

De bestaande implementatie is voortgezet. Geen module is opnieuw vanaf nul gebouwd. De schermcode en stijlen zijn uit de HTML gehaald; vervangen functieversies zijn verwijderd om dubbele definities te voorkomen.

| Bestand | Verantwoordelijkheid |
| --- | --- |
| `server.py` | HTTP, authenticatie, serverrechten, CRUD, planning, HR/CAO, berichten, werkstromen, database-initialisatie/migratie |
| `domain.py` | Gedeelde invoervalidatie, statussen, referenties, recordafscherming, roosterregels en verwijderbescherming |
| `index.html` | Nederlandse HTML-schil en oorspronkelijke Amocean-splash/logo |
| `app.js` | Behouden moduleschermen, dagstart, planning, HR/CAO, SOS en werkstromen |
| `ui.js` | Navigatie, formulieren, actuele widgets, accountbeheer, CSV-beveiliging en interactieve rondleiding |
| `styles.css`, `ui.css` | Oorspronkelijke Amocean-stijlen en responsive/toegankelijke aanvullingen |
| `start.py`, `START*` | Lokale start, backup, gereedheidscontrole en optionele Cloudflare Tunnel |
| `tests/`, `run_tests.py` | Backend-, browser-, installatie- en beperkte schaalcontroles |
| `reports/` | Werkelijke testuitvoer en screenshots van deze versie |

## Data en modules

De oorspronkelijke twintig modules blijven aanwezig; beschikbaarheid is nummer 21. Generieke CRUD is getest met aanmaken, uitlezen, wijzigen en verwijderen voor elke module.

| Groep | Tabellen/modules | Controles |
| --- | --- | --- |
| Relaties | customers, objects, contracts, quotes | Verplichte namen, geldige verwijzingen, klant/objectconsistentie, bedragen, datums |
| Financieel | invoices, ledger, payroll | Unieke factuurnummers bij CRUD, klant/contractconsistentie, getallen, periode, status |
| Personeel | employees, leave, availability | Contracturen, datumvolgorde, status, eigen-recordrechten en beschikbaarheidstijden |
| Uitvoering | shifts, hours, workorders | Overlap, verlof, beschikbaarheid, maximaal 24 geregistreerde uren per dag, dienst/medewerker/datum, goedkeuringsrechten |
| Kwaliteit | inspections, logbook | Scorebereik, datum, objectkoppeling, afscherming per toegewezen object |
| Middelen | orders, assets, keys, vehicles | Aantallen, objectverwijzingen, datums, verplichte identificatievelden |
| Overig | documents, alerts | Opgeslagen referentiemetadata en meldingen; verplichte velden en statussen |

Ondersteunende tabellen: `users`, `sessions`, `permissions`, `messages`, `audit`, `autopilot_jobs`, `employee_cao_profiles`, `employee_contract_terms`, `settings`.

Relaties in de oorspronkelijke generieke tabellen zijn tekstuele ID's zonder gedeclareerde SQL-foreign keys. Om bestaande databases intact te laten zijn ze niet destructief herbouwd. Alle generieke schrijfroutes valideren verwijzingen op de server. Verwijderen van een gekoppeld record wordt geweigerd. Deze applicatieregels beschermen niet tegen handmatig uitgevoerde SQL; toekomstige schemamigraties met echte constraints vragen aparte voorbereiding en datacontrole.

Mutaties van generieke records gebruiken `BEGIN IMMEDIATE`: de validatie en schrijfoperatie vallen binnen één SQLite-schrijftransactie. SOS en werkstroomgoedkeuring doen hetzelfde. Open transacties worden bij fouten teruggedraaid en verbindingen per verzoek gesloten. Indexen versnellen medewerkers- en datumselecties. De stille limieten van 1.000/2.000 bedrijfsrecords zijn verwijderd; voor grotere datasets blijft serverpaginering een vervolgstap.

## Rollen en rechten

**Beheerder:** alle bestaande modules en administratieve routes. Kan accounts koppelen, rol/wachtwoord wijzigen, blokkeren en extra inzage geven. Het laatste actieve beheerdersaccount kan niet worden geblokkeerd of gedegradeerd. Sessies vervallen na wachtwoord- of rolwijziging en blokkering. Accounts blokkeren behoudt de wijzigingshistorie.

**Medewerker:** vaste koppeling via `users.employee_id`, nooit tijdens elk verzoek via een naammatch. Ziet uitsluitend eigen diensten, uren, werkbonnen, verlof en beschikbaarheid. Logboekgegevens zijn beperkt tot toegewezen objecten. Een medewerker kan eigen uren indienen, eigen aanvragen en beschikbaarheid beheren, eigen werkbonvoortgang invullen en logboekmeldingen voor eigen objecten maken. Een medewerker kan geen uren/verlof goedkeuren, diensten wijzigen of rechten verhogen. Extra inzage in objecten, bestellingen, materieel en inspecties blijft beperkt tot toegewezen objecten. Expliciet vrijgegeven actieve documenten zijn gedeelde instructies; er is geen vertrouwelijke documentkluis.

Het “Klantportaal” blijft een interne beheerdersweergave. Externe klantaccounts of een derde klantrol waren niet aanwezig en worden niet voorgesteld als geïmplementeerd.

## API-groepen

- `POST /api/login`, `GET /api/me`, `POST /api/logout`: acht uur geldige, gehashte sessietokens; generieke loginfout en begrenzing van pogingen.
- `GET /api/modules`, `/api/lookups`: rolafhankelijke formuliermetadata en beperkte keuzelijsten.
- `/api/records/{module}[/{id}]`: GET, POST, PUT, DELETE met module- en recordcontrole. De server bepaalt eigenaarschap en statussen voor medewerkers.
- `/api/users`, `/api/users/permissions`, `/api/users/link`, `/api/users/update`: uitsluitend beheer.
- `/api/planning/overview`, `/api/planning/suggest`, `/api/sos/candidates`, `/api/sos/assign`: weekoverzicht en menselijke toewijzing na gedeelde controles.
- `/api/messages`, `/api/messages/read`: berichtopslag, eigenaarschap en leesstatus.
- `/api/hr/*`, `/api/cao/*`: personeelsdossiers en behouden indicatieve rekenhulpen; uitsluitend beheer.
- `/api/autopilot/*`: voorstel, goedkeuren/afwijzen, uitvoering en audit. Herhaalde goedkeuring van hetzelfde voorstel wordt geweigerd.
- `/api/dashboard`, `/api/smart/overview`, `/api/ai/analyze`, `/api/demo/chain`, `/api/audit`: opgeslagen aantallen, regels en wijzigingshistorie. Medewerkers krijgen persoonlijke dashboardtellers.

## Planning en interactie

De week wordt maandag–zondag opgebouwd. Overlap, actieve medewerker, verlof/verzuim en geregistreerde beschikbaarheid worden opnieuw gecontroleerd bij opslaan. Goedgekeurd verlof of beschikbaarheidswijzigingen kunnen bestaande diensten conflicterend maken: het overzicht toont die signalen; bestaande diensten worden niet stilzwijgend verwijderd. Beschikbare blokken worden gecontroleerd op dekking, niet-beschikbare blokken blokkeren overlappende inzet. Ontbrekende beschikbaarheid wordt als **onbevestigd** getoond.

Suggesties sorteren eerst op overschrijding van contracturen en daarna op geplande uren. Contracturen zijn een waarschuwing, geen volledige cao/rusttijdtoets. Reistijd, certificaten, meerdere locaties, nachtdiensten over middernacht en externe kalenderintegraties zijn niet volledig geïmplementeerd. Diensten over middernacht worden expliciet geweigerd.

Browsergeschiedenis ondersteunt terug en vooruit tussen schermen. Op het eerste scherm mag de browser de pagina verlaten; er is geen oneindige geschiedenisval. Het zijmenu sluit met knop, achtergrond en Escape, houdt toetsenbordfocus vast en laat scrollen binnen het menu toe. Formulieren gebruiken servermetadata, foutmeldingen en echte opslag. De rondleiding wijzigt zelf geen bedrijfsgegevens.
