# V6 migratiecentrum — geverifieerde vertrekpunten

Basis: commit 42362d9fa716b433ab539169ae7d3f9f1b1bcdff. De begonnen schoolcontractuitbreiding is als lokale wijziging behouden. Geen herbouw.

- Bestaand: JSON-klantimport via v5/customers/import, maximaal 200 rijen per transactie. De browser hanteert 600.000 bytes; de algemene JSON-serverlimiet is 1.000.000 bytes. Er is geen bestaande centrale CSV/XLSX-wizard.
- Bestaand: werkende rollen, expliciete proceshandelingen, versiecontrole, auditketen, migraties, backup/herstel, sync-outbox en generieke connector. Deze onderdelen blijven behouden.
- Open: uploads/kolommapping/bronidentiteiten/proefrun/batchcontrolepunten/verslagen/templates/onboarding ontbreken als centrale migratievoorziening.
- Open: rooms, service_types, work_programs en work_instructions ontbreken als zelfstandige doelmodellen; noodzakelijke additieve modellen en zichtbare modules moeten worden toegevoegd.
- Open SEC-05: scopes.py bevat een geteste beleidskern, maar is bewust niet aangesloten op alle routes. Geen bestaande afdelings-/rayonisolatieclaim.
- Extern: echte NoCore-exportstructuur, bronbestanden en migratiegoedkeuring ontbreken; synthetische fixtures zijn geen bevestigde leveranciersspecificatie. NoCore wordt geen operationele runtimeafhankelijkheid.
- Extern: boekhoudprovider en bevoegde API-toegang ontbreken. Bestaande sync wordt behouden; er worden geen vier speculatieve live adapters gebouwd.
- Omgeving/onafhankelijk: WebKit eerder HTTP 403; geen fysieke apparaten, onafhankelijke pentest of productieacceptatie.

Baseline: 123 tests, één mislukte browserassertie door te vroeg lezen na asynchrone verversing; gecorrigeerd en de vijf betrokken browsertests opnieuw geslaagd. Dit bestand beschrijft de vertrekpunten; zie V6-MIGRATION-REPORT.md voor de uiteindelijke afhandeling.

## Implementatiekeuzes

- Importidentiteiten worden apart bewaard per bronsysteem + categorie + externe sleutel. Een voorloopnul wordt niet weggeconverteerd. Relaties verwijzen naar deze sleutels en worden nooit op namen gegokt.
- Proefrun gebruikt de bestaande bedrijfsvalidatie en gebruikt een tijdelijke databasekopie met teruggedraaide savepoint; preview/logmetadata blijft bewaard, bedrijfsgegevens niet.
- Definitieve import vereist expliciete beheerbevestiging en werkt in begrensde, atomair gecommitteerde batches. Iedere batch slaat een controlepunt op. Na onderbreking hervat dezelfde import vanaf het laatste controlepunt; reeds gecommitteerde batches worden niet stilzwijgend teruggedraaid.
- Updaten vereist gekozen conflictbeleid en versiecontrole ten opzichte van de proefrun. Onbekende/ontbrekende ouders en veranderde doelrecords blokkeren de betreffende batch.
- CSV/XLSX wordt lokaal op de server verwerkt; formules, externe spreadsheetkoppelingen, zipbommen en macro-inhoud worden geweigerd. Geen betaalde conversie- of AI-dienst.
- Nieuwe objectmodellen worden zichtbaar via de bestaande werkruimte en dezelfde serverrollen. Templates worden uit het importregister gegenereerd, niet los van de validatie onderhouden.
