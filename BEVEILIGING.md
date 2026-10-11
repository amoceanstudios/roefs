# Beveiligingsbeoordeling en resterend werk

Deze beoordeling omvat broninspectie en de meegeleverde automatische regressietests. Dit is geen onafhankelijke penetratietest, AVG-audit of productiecertificering.

## Aantoonbare fouten die zijn hersteld

| Bevinding in de aangeleverde versie | Herstel en bewijs |
| --- | --- |
| Dossiertoegang werd bij elk verzoek afgeleid van een gelijke gebruikers- en medewerkersnaam | Permanente accountkoppeling; tests voor hernoemen, expliciete koppeling en een nieuw account met dezelfde naam |
| Medewerkersdashboard telde gegevens van andere medewerkers; logboek had geen objectafscherming | Eigen tellers en filters per toegewezen object; tests met afgeschermde records |
| Vrijwel alle modules accepteerden ongeldige getallen, datums, statussen en verwijzingen | Gemeenschappelijke servervalidatie voor 21 modules; negatieve regressies en CRUD per module |
| Verwijderen liet gekoppelde records achter | Verwijderbescherming en instructie om status/koppelingen te wijzigen |
| SOS en vervangingswerkstromen konden goedgekeurd verlof omzeilen | Dezelfde roosterregels voor alle toewijzingsroutes; regressie voor alle routes |
| Gewone planningscontrole en insert waren niet samen transactioneel | Schrijftransactie; gelijktijdige aanvragen geven precies één opgeslagen dienst en één conflict |
| Geen opslag van daadwerkelijke beschikbaarheidsblokken | Opgeslagen beschikbare/niet-beschikbare tijden; controles bij suggestie en opslaan |
| Dubbele of te hoge uren en inconsistente factuurkoppelingen mogelijk | Daggrens, dienstconsistentie, duplicaatcontrole en klant/contractvalidatie |
| Sessietokens stonden leesbaar in SQLite; geen loginbegrenzing | SHA-256-opslag van hoog-entropische tokens, verval/uitloggen/blokkeren en begrensde loginpogingen |
| Browserbeveiligingsheaders werden alleen op JSON gezet | Headers op HTML, scripts, afbeeldingen en API-antwoorden |
| CSV-cellen konden spreadsheetformules activeren | Voorloopbeveiliging voor formuletekens en regressietest |
| Widgets konden oude of niet-opgehaalde nulwaarden tonen | Actuele servergegevens bij navigatie/vernieuwen; werknemers krijgen geen fictieve bedrijfswidgets |
| Een lege klantenlijst kon bij herstart nieuwe voorbeeldgegevens injecteren | Alleen initiële seeding bij nieuwe installatie |
| Container luisterde alleen op loopback en bestanden konden onleesbaar zijn voor de niet-rootgebruiker | Containerbinding en expliciet bestandseigenaarschap; echte Docker-start en login getest |
| Startcontrole kon een andere server op dezelfde poort aanzien voor de eigen app | Per start een instantie-ID en negatieve bezette-poorttest; het bestaande proces blijft draaien |

## Huidige beveiligingsgrenzen

- Python-standaardbibliotheekserver, één proces en SQLite; geen productie-webserver, gedeelde sessie-infrastructuur of onafhankelijke rate-limitdienst.
- De loginbegrenzing leeft in het servergeheugen en is geen volledige bescherming tegen gedistribueerde aanvallen of dienstweigering. Reverse-proxyadressen worden niet blind als clientidentiteit vertrouwd.
- Sessies staan in `sessionStorage` aan de clientkant. De CSP staat bestaande inline eventhandlers/stijlen toe. HTML-escaping en een opgeslagen XSS-regressie zijn getest, maar een strikte nonce-CSP en volledige sessie/cookieherziening ontbreken.
- Accountblokkering, serverrechten, Same-Origincontrole bij mutaties en JSON-contenttypecontrole zijn aanwezig. Geen MFA, selfservicewachtwoordherstel, externe identityprovider of fijnmazige organisatie-/tenantrollen.
- De database is niet versleuteld. Sleutelregistratie, berichten en personeelsdossiers zijn alleen geschikt voor fictieve demo-inhoud in deze versie. Backups bevatten dezelfde gegevens als de database en moeten privé blijven.
- Auditregistratie is applicatief en lokaal; niet cryptografisch onveranderbaar en niet bij elke read aanwezig.
- Documenten zijn metadata/referenties, geen beveiligde upload- of ondertekenservice. De werkbonaftekening is opgeslagen tekst, geen juridische digitale handtekening.
- De tekstuele relatiekolommen zijn behouden. App-validatie en beschermde verwijdering vervangen geen databaseconstraints tegen directe SQL-bewerkingen. Onbekende bestaande databases kunnen reeds ongeldige gegevens bevatten; controleer de relatiecontrole en maak eerst een backup.
- CAO-bedragen, fiscale regels en juridische uitzonderingen zijn overgenomen rekenhulpen. Actuele rechtsgeldigheid en volledige salarisverwerking zijn niet extern gevalideerd. Factuurstatussen zijn lokale administratieve gegevens, geen bank-, btw- of boekhoudintegratie. Boekhoudregels vormen geen volledig sluitend dubbelboekhoudsysteem; definitieve factuurnummerreeksen, creditnota’s en fiscale onveranderbaarheid zijn niet wettelijk getoetst.

## Nodig vóór gebruik met echte bedrijfsgegevens

Een afzonderlijke productieopdracht moet ten minste onafhankelijke beveiligings- en autorisatietests, sessie-/CSP-hardening, privacygrondslagen en bewaartermijnen, backup-/hersteloefeningen, monitoring, robuuste deployment en echte integratietests afdekken. Voer realistische langdurige belastingtests uit met de beoogde gelijktijdigheid en schrijfbelasting. Controleer fysieke iPhone/Android-apparaten, Safari, toegankelijkheid en de uiteindelijke netwerkconfiguratie.

De korte proef met 250 fictieve medewerkers en 800 klanten bevestigt alleen de expliciet gemeten lokale scenario's. Er is geen uitspraak gedaan dat het systeem al geschikt is voor het volledige bedrijf in productie.
