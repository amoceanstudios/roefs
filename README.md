# ROEFS ONE — V6 migratiepakket

Voortzetting van de bestaande applicatie. Begin bij [ROEFS-MIGRATIEHANDLEIDING.md](ROEFS-MIGRATIEHANDLEIDING.md). De [migratierapportage](V6-MIGRATION-REPORT.md), [finale functiematrix](V6-FINAL-FUNCTIEMATRIX.md), [tests](V6-FINAL-TESTRAPPORT.md), [beveiligingscontrole](V6-FINAL-SECURITY.md) en [metingen](V6-FINAL-PERFORMANCE.md) beschrijven wat werkelijk is getest en wat nog klantacceptatie vereist. **Geen productiegeschiktheidsclaim.**

Nieuw: native CSV/XLSX-datamigratie, 26 categorieën/52 templates, 24.050 fictieve volumerecords, schoolafspraken, Roefs onboarding, afdeling/rayonhandhaving en providerneutrale boekhoudvoorbereiding. NoCore is een eenmalige migratiebron, geen permanente operationele afhankelijkheid.

## Behouden basis

Voortgebouwd op de aangeleverde ROEFS ONE-broncode. De Python-backend, SQLite, bestaande modules en het Amocean-logo blijven behouden. Na inloggen kies je **Oud Portaal** of **Nieuw Portaal**. Het vertrouwde scherm **‘Hoi Beheerder. Wat wil je doen?’** blijft beschikbaar via Oud Portaal. Dit pakket gebruikt demonstratiegegevens.

```bash
python3 start.py
```

Python 3.10+; getest met 3.12 op Linux. Het startscript maakt willekeurige demoaccountwachtwoorden en toont ze uitsluitend lokaal. `--quiet` onderdrukt deze uitvoer. Windows: installeer eerst `py -3 -m pip install -r requirements.txt`, daarna `py -3 start.py`.

De **Werkruimte** voegt een gekoppelde procesketen toe: klant met locaties → contract → werkopdracht → gekwalificeerde medewerker en materieel → checklist en bestand → uren → goedkeuring → decimale conceptfactuur en PDF/CSV. Planning heeft dag/week/maand, groepering, suggestieredenen, versiecontrole, batchkopieën en veilig terugdraaien. De bestaande eenvoudige schermen blijven beschikbaar.

**Integraties & synchronisatie** ondersteunt een geconfigureerde JSON-API automatisch op een interval, inclusief recordkoppelingen, import/export, systeemvoorrang per categorie, conflicten, foutgeschiedenis, herhaalpogingen en een duurzame verzendwachtrij. Er zijn geen echte ERP-accounts gekoppeld. AFAS, Exact en Dynamics staan zichtbaar als nog niet actieve providerprofielen; hun leverancierspecifieke adapters vereisen toegang en schema’s. Zie [INTEGRATIES.md](INTEGRATIES.md).

## Documentatie

- [CINEMATIC-WORLD-IMPLEMENTATION.md](CINEMATIC-WORLD-IMPLEMENTATION.md): het 3D-portaal, cameravluchten, bestaande modules in ruimtelijke panelen en terugnavigatie.
- [Rendering- en regressiecontroles](reports/world-render-budget-verification.md): 25 geselecteerde tests van de laatste vervolgstap; grenzen van apparaat- en prestatiedekking.
- [INSTALLATIE.md](INSTALLATIE.md): starten, upgrade, Docker, gratis Cloudflare en tests.
- [GEBRUIKERSHANDLEIDING.md](GEBRUIKERSHANDLEIDING.md): dagelijkse bediening en procesketen.
- [PLANNING.md](PLANNING.md): controles, suggesties en beperkingen.
- [ARCHITECTUUR.md](ARCHITECTUUR.md), [DATABASE.md](DATABASE.md), [API.md](API.md): technische werking.
- [BEVEILIGING.md](BEVEILIGING.md): beveiliging, rechten en herstel.
- [TESTRAPPORT.md](TESTRAPPORT.md): uitgevoerde tests en metingen.
- [FUNCTIEMATRIX.md](FUNCTIEMATRIX.md), [BEKENDE-PROBLEMEN.md](BEKENDE-PROBLEMEN.md): expliciete dekking en resterende scope.
- [PRODUCTIE-CHECKLIST.md](PRODUCTIE-CHECKLIST.md): voorwaarden vóór een eventuele productiebeoordeling.

```bash
python3 run_tests.py --backend-only
# Met Playwright en Chromium:
python3 run_tests.py --load
```

Er wordt niets automatisch gefactureerd, betaald, gemaild of publiek gepubliceerd. Externe synchronisatie staat standaard uit en vereist expliciete configuratie. Deze versie is niet als productiegeschikt vastgesteld. De masteropdracht is breder dan de geverifieerde dekking; zie de functiematrix voor PARTIAL/BLOCKED/NOT TESTED.

## 3D-portaal starten en bijwerken

Start de app zoals hierboven en log in. Kies **Oud Portaal** voor het vertrouwde Amocean-dashboard of **Nieuw Portaal** voor de 3D-wereld. Alle toegankelijke modules gebruiken hun bestaande schermen en server-API's. **Sluiten** in de 3D-wereld brengt je terug naar het oude portaal. Via **Portaal kiezen** op dat startscherm kun je opnieuw kiezen. Zonder WebGL2 blijft de modulelijst bruikbaar; **Beweging uit** schakelt de camera-animatie en de doorlopende renderlus uit.

Bij opnieuw inloggen verschijnt de keuze opnieuw. Herladen binnen dezelfde browsertab behoudt de gekozen omgeving; directe links naar een 3D-module openen die bestemming. De keuze wijzigt geen bedrijfsgegevens of rechten. Zie [de controles van het keuzescherm](reports/portal-choice-verification.md).

`spatial.js` is meegebouwd en opgenomen in de Docker-image. Voor normaal starten en Render via Docker is geen npm-installatie nodig. Na wijzigingen in `spatial/` bouw je met Node.js 24 en de gepinde lockfile opnieuw:

```bash
npm ci
node tools/frontend_notices.mjs
npm run build
npm run test:spatial
```

De geteste deploymentbranch is `roefs-one-enterprise-v6`. Controleer in Render of die branch is geselecteerd en vergelijk het commitnummer van de deployment met GitHub. Een GitHub-push bevestigt op zichzelf geen geslaagde Render-deployment. Op een gratis Render-instance is de SQLite-opslag niet blijvend bij herstart of redeploy; zie de installatiehandleiding voor opslag en backups.
