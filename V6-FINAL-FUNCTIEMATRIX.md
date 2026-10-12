# V6 finale functiematrix

Status verwijst naar technische fictieve tests; klantacceptatie is afzonderlijk.

| Onderdeel | Status en bewijs |
|---|---|
| Bestaande app, Python/SQLite, Amocean-startscherm, rollen en processen | Behouden; volledige regressiesuite |
| CSV/XLSX-wizard en echte database-import | Geïmplementeerd; API-, Chromium- en volumetests |
| Mapping, proefrun, conflicten, checkpoints en historie | Geïmplementeerd; herimport/updates/onderbreking/gelijktijdige bevestiging getest |
| Schooldienstafspraken en werkbonnen | Geïmplementeerd; 460 uur, uitzonderingen, expliciete glasdatums, idempotente generatie getest |
| Afdeling/rayonrechten | Aangesloten op server/API; beleidskern- en negatieve HTTP-tests; echte Roefs-indeling nog nodig |
| Onboarding | Opgeslagen eigenaar/bewijs/datum/dependencies; API/browser getest |
| Boekhoudinterface | Configuratie/outbox/status/retries getest met mock; live adapter en provideracceptatie geblokkeerd op leverancierinformatie |
| Planning/uitvoering/uren/factuurvoorbereiding | Bestaande kritieke keten opnieuw getest; geen live factuurboeking zonder adapter |
| Responsieve UI | Chromium op bestaande acht breedten; nieuwe wizard bij 390 px; fysieke Safari/Android nog niet geaccepteerd |
| Backup/herstel | Getest, inclusief importidentiteiten en pauzeren boekhoudcyclus |
| Cloudflare-startscript | Behouden; publieke netwerkregistratie eerder geblokkeerd, geen live URL bewezen |
| Productiegeschiktheid | Niet vastgesteld; zie PRODUCTIE-CHECKLIST.md |

## Importcategorieën

Onderstaande ketentest maakt elke XLSX-template werkelijk aan en verwerkt de CSV-template daarna als ongewijzigde herimport. Download/parse wordt ook voor beide formaten getest. Aanvullende tests maken CSV-records aan en controleren updates/rollback.

| Intern model | Module | XLSX | CSV |
|---|---|---|---|
| `customers` | Relaties | Aangemaakt en zichtbaar | Herimport verwerkt, geen duplicaat |
| `objects` | Objecten | Aangemaakt en zichtbaar | Herimport verwerkt, geen duplicaat |
| `contracts` | Contracten | Aangemaakt en zichtbaar | Herimport verwerkt, geen duplicaat |
| `quotes` | Offertes | Aangemaakt en zichtbaar | Herimport verwerkt, geen duplicaat |
| `employees` | HRM | Aangemaakt en zichtbaar | Herimport verwerkt, geen duplicaat |
| `shifts` | Planning | Aangemaakt en zichtbaar | Herimport verwerkt, geen duplicaat |
| `hours` | Urenregistratie | Aangemaakt en zichtbaar | Herimport verwerkt, geen duplicaat |
| `inspections` | Kwaliteit DKS/VSR | Aangemaakt en zichtbaar | Herimport verwerkt, geen duplicaat |
| `logbook` | Digitaal logboek | Aangemaakt en zichtbaar | Herimport verwerkt, geen duplicaat |
| `workorders` | Werkbonnen | Aangemaakt en zichtbaar | Herimport verwerkt, geen duplicaat |
| `orders` | Bestellingen | Aangemaakt en zichtbaar | Herimport verwerkt, geen duplicaat |
| `assets` | Materieel | Aangemaakt en zichtbaar | Herimport verwerkt, geen duplicaat |
| `keys` | Sleutelregistratie | Aangemaakt en zichtbaar | Herimport verwerkt, geen duplicaat |
| `vehicles` | Wagenpark | Aangemaakt en zichtbaar | Herimport verwerkt, geen duplicaat |
| `documents` | Documenten | Aangemaakt en zichtbaar | Herimport verwerkt, geen duplicaat |
| `leave` | Verlof & verzuim | Aangemaakt en zichtbaar | Herimport verwerkt, geen duplicaat |
| `availability` | Beschikbaarheid | Aangemaakt en zichtbaar | Herimport verwerkt, geen duplicaat |
| `alerts` | Meldingen | Aangemaakt en zichtbaar | Herimport verwerkt, geen duplicaat |
| `communications` | Contacthistorie | Aangemaakt en zichtbaar | Herimport verwerkt, geen duplicaat |
| `articles` | Artikelen en materialen | Aangemaakt en zichtbaar | Herimport verwerkt, geen duplicaat |
| `teams` | Teams | Aangemaakt en zichtbaar | Herimport verwerkt, geen duplicaat |
| `contacts` | Contactpersonen | Aangemaakt en zichtbaar | Herimport verwerkt, geen duplicaat |
| `rooms` | Ruimtes | Aangemaakt en zichtbaar | Herimport verwerkt, geen duplicaat |
| `service_types` | Diensttypes | Aangemaakt en zichtbaar | Herimport verwerkt, geen duplicaat |
| `work_programs` | Werkprogramma's | Aangemaakt en zichtbaar | Herimport verwerkt, geen duplicaat |
| `work_instructions` | Werkinstructies | Aangemaakt en zichtbaar | Herimport verwerkt, geen duplicaat |

Niet opgenomen in vrije import: facturen/boekingen/salaris en modelspecifieke hulpgegevens waarvoor een afzonderlijke proceshandeling nodig is. Documentimport betreft metadata, geen bijlagebestanden. Nieuwe werkopdrachten zijn Concept, geen gesimuleerde historische goedkeuringen.
