# V6 huidig overdrachtspunt — migratiepakket

De oorspronkelijke tussenstand `42362d9fa716b433ab539169ae7d3f9f1b1bcdff` is behouden en uitgebreid op `roefs-one-enterprise-v6`. Lees nu de **V6-FINAL-*.md**-rapporten en V6-MIGRATION-REPORT.md. Oudere V6- en V5-rapporten blijven historische meetpunten; hun open-puntenlijst is niet de actuele status.

Gereed in bron: native CSV/XLSX-migratie met echte databasewrites, 26 categorieën, templates, fictieve volumeproef, expliciete schooldiensten, onboarding, actieve scopehandhaving en boekhoudinterface. De scopekern is niet meer inactief. Nieuwe modellen/migraties zijn additief. De bestaande Python/SQLite-app en oorspronkelijke Amocean-startscherm blijven staan.

Actuele code: services/data_migration.py, migration_registry.py, spreadsheets.py, migration_models.py, service_plans.py, onboarding.py, accounting.py en scopes.py; integratie in server/routes/common en bestaande processen. UI en expliciete CSP-eventhandlers staan in enterprise.js/events.js.

Reproduceer tests met `python run_tests.py --load` en `python tests/migration_volume.py`. De bron-ZIP kan schoon worden gecontroleerd met `python tools/verify_package.py <zip> --report <extern-pad>/controle.json`.

Vervolg dat Roefs/externe validatie vereist: representatieve goedgekeurde exports en veldbetekenis, definitieve recordindeling/rechten, inhoudelijke aansluiting en procesacceptatie, providerkeuze/API-contract en echte boekhoudadapter, beveiligde persistente doelomgeving, onafhankelijke pentest, fysieke mobiele acceptatie en duurbelasting. Zie ROEFS-NODIG.md. Geen automatische klantgoedkeuring of go-live.
