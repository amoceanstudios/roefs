# V6 finale beveiligingscontrole — technische resultaten en grenzen

## Binnen deze implementatie gecontroleerd

Bestaande serverrollen, HttpOnly/SameSite-cookies, CSRF, PBKDF2, TOTP/herstelcodes, inactieve accounts, sessie-intrekking, versiecontrole, auditketen, documentquarantaine en private downloads blijven behouden. De strikte script-CSP blijft actief; nieuwe UI-acties gebruiken de bestaande expliciete eventdispatcher.

De voorheen inactieve scopekern is aangesloten op HTTP-authenticatie met requestgebonden ContextVar-reset. Beperking op afdeling en rayon is een intersectie boven op rolrechten. Geen indeling betekent geen toegang voor een beperkt account. Beheeraccounts zijn bewust globaal en kunnen via de API niet zelf worden beperkt. Beleidswijziging trekt de sessies van de gebruiker in. Indelingen en beleid hebben versiecontrole; verwijderde classificaties blijven niet aan hergebruikte record-ID's hangen.

Gecontroleerde paden: oude en nieuwe record-API's, paginering/tellingen, lookups, dashboard, planning/suggesties, directe mutaties en batches, werkopdrachten, documenten, uren, rapporten/CSV/PDF, contracten en nieuwe modellen. Gekoppelde payloads mogen niet over de ingestelde grenzen heen schrijven. Een werkopdrachttransitie mag geen verborgen gekoppelde diensten wijzigen. Planningconflicten blijven over grenzen heen voorkomen, maar geven geen verborgen dienstnummer prijs. Vrije organisatiebrede audit-/timeline-/sync-overzichten zijn voor beperkte accounts geweigerd. Meldingen worden alleen getoond als hun doel herleidbaar en toegankelijk is; vrije algemene meldingen worden bij actieve beperking verborgen.

Negatieve HTTP-tests bewijzen Noord/Zuid-isolatie, oningedeelde records in alle oorspronkelijke modules, verboden details/wijzigingen/verwijderingen, kruisverwijzingen, bulkrollback, exports, bestanden, imports, beheerfuncties en ingetrokken sessies. Positieve tests controleren toegestane lijsten, planning, rapportage, nieuwe records en daaropvolgende globale beheerrequests. Daarnaast blijven de 10 beleidskerntests bestaan. Dit is geen onafhankelijk, uitputtend bewijs van afwezigheid van alle beveiligingsfouten.

## Migratie en boekhouding

Alle migratie-, onboarding- en boekhoudroutes vereisen onbeperkt systeem-/bedrijfsbeheer, ook downloads. JSON-/bestandslimieten worden op de server afgedwongen. XLSX wordt zonder extractie verwerkt; padtraversal, dubbele ZIP-paden, uitpaklimieten, XML-entiteiten, formules, externe relaties, macro's en ingesloten actieve inhoud worden gecontroleerd. CSV-uitvoer neutraliseert formuleprefixen. Geen betaalde conversieservice of uitvoer van celinhoud.

Import gebruikt parameterbinding, een vaste modellencatalogus, bronidentiteiten, gevalideerde relaties, optionele expliciete binding met bestaande interne records, foutloze proefrun, beheerbevestiging, doelversies en transactiebatches. Gelijktijdig bevestigen levert één succes en één versieconflict op. Een onderbreking behoudt eerdere batches en rolt de mislukte batch terug.

Achtergrondtaken zijn expliciete organisatiebrede servicetaken, geen opdrachten van een beperkte gebruiker. Scopebeperkte gebruikers kunnen de externe organisatiebrede sync niet bedienen. De nieuwe boekhoudcyclus staat standaard uit en vereist een geïnstalleerde/geteste adapter én expliciete activering. Geen live adapter wordt meegeleverd. Providerfouten lekken geen tokens; uitwisseling bevat een begrensde selectie factuur-/debiteurvelden. Herstel pauzeert alle externe verwerking.

## Nog vereist vóór echt gebruik

- Onafhankelijke penetratietest en beoordeling van de daadwerkelijke Roefs-rechtenmatrix en recordindeling.
- Encryptie en toegangsbeheer van actieve database/documenten. Optionele versleutelde backups bestaan; dat is geen volledige encryptie-at-rest van de werkdatabase. TOTP-geheimen vereisen bescherming van de database.
- ClamAV of geaccepteerde malwarescanner. Zonder scanner blijven binaire uploads in quarantaine; tekstbijlagen zijn geen bewijs van een uitgevoerde virusscan.
- WebKit/Safari, fysieke toestellen, toegankelijkheid, doelomgeving, externe boekhoud-API en duurbelasting.
- Logbewaking, bewaartermijnen, offsite herstel, incidentprocedure, onafhankelijke auditopslag en accountbeheer. Afdeling/rayonbeleid is geen multi-tenant infrastructuurscheiding.

Historische V5/V6-tussenstandrapporten zijn geen actuele eindtestuitvoer. De actuele uitgevoerde tests en eventuele blokkades staan in V6-FINAL-TESTRAPPORT.md. Geen nul-bugs- of productiecertificering.
