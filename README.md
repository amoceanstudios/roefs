# ROEFS ONE — V6 migratiepakket

Voortzetting van de bestaande applicatie. Begin bij [ROEFS-MIGRATIEHANDLEIDING.md](ROEFS-MIGRATIEHANDLEIDING.md). De [migratierapportage](V6-MIGRATION-REPORT.md), [finale functiematrix](V6-FINAL-FUNCTIEMATRIX.md), [tests](V6-FINAL-TESTRAPPORT.md), [beveiligingscontrole](V6-FINAL-SECURITY.md) en [metingen](V6-FINAL-PERFORMANCE.md) beschrijven wat werkelijk is getest en wat nog klantacceptatie vereist. **Geen productiegeschiktheidsclaim.**

Nieuw: native CSV/XLSX-datamigratie, 26 categorieën/52 templates, 24.050 fictieve volumerecords, schoolafspraken, Roefs onboarding, afdeling/rayonhandhaving en providerneutrale boekhoudvoorbereiding. NoCore is een eenmalige migratiebron, geen permanente operationele afhankelijkheid.

## Behouden basis

Voortgebouwd op de aangeleverde ROEFS ONE-broncode. De Python-backend, SQLite, bestaande modules, Amocean-logo en eerste scherm **‘Hoi Beheerder. Wat wil je doen?’** blijven behouden. Dit pakket gebruikt uitsluitend fictieve demonstratiegegevens.

```bash
python3 start.py
```

Python 3.10+; getest met 3.12 op Linux. Het startscript maakt willekeurige demoaccountwachtwoorden en toont ze uitsluitend lokaal. `--quiet` onderdrukt deze uitvoer. Windows: installeer eerst `py -3 -m pip install -r requirements.txt`, daarna `py -3 start.py`.

De **Werkruimte** voegt een gekoppelde procesketen toe: klant met locaties → contract → werkopdracht → gekwalificeerde medewerker en materieel → checklist en bestand → uren → goedkeuring → decimale conceptfactuur en PDF/CSV. Planning heeft dag/week/maand, groepering, suggestieredenen, versiecontrole, batchkopieën en veilig terugdraaien. De bestaande eenvoudige schermen blijven beschikbaar.

**Integraties & synchronisatie** ondersteunt een geconfigureerde JSON-API automatisch op een interval, inclusief recordkoppelingen, import/export, systeemvoorrang per categorie, conflicten, foutgeschiedenis, herhaalpogingen en een duurzame verzendwachtrij. Er zijn geen echte ERP-accounts gekoppeld. AFAS, Exact en Dynamics staan zichtbaar als nog niet actieve providerprofielen; hun leverancierspecifieke adapters vereisen toegang en schema’s. Zie [INTEGRATIES.md](INTEGRATIES.md).

## Documentatie

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
