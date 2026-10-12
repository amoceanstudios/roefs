# Automatische synchronisatie

## Uitgangspunt en actuele status

Eenmalig configureren, daarna automatisch bijwerken zolang de server draait, de toegang geldig blijft en het externe API-contract wordt nageleefd. Standaard zijn er **geen actieve koppelingen** en gaat geen bedrijfsrecord naar buiten. De automatische worker start met de applicatie, bewaart zijn toestand in SQLite en hervat na herstart.

De generieke JSON-connector is functioneel geïmplementeerd en getest tegen een lokale HTTP-testserver. Dat bewijst het connectorcontract, niet een koppeling met een echte ERP-leverancier. AFAS, Exact Online en Microsoft Dynamics 365 zijn inactieve providerprofielen met expliciete ontbrekende voorwaarden. Er zijn geen verzonnen leveranciers-API’s, OAuth-tokens of succesvolle externe synchronisaties.

## Configureren

1. Zorg dat het doelsysteem of een eigen adapter het hieronder beschreven protocol ondersteunt.
2. Stel op de server `ROEFS_SYNC_ALLOWED_HOSTS` in op uitsluitend de benodigde API-hostnamen, komma-gescheiden. Externe adressen moeten HTTPS gebruiken; lokale/private/metadata-IP’s en redirects worden geweigerd.
3. Stel het API-token als geheime omgevingsvariabele in, bijvoorbeeld `ROEFS_SYNC_TOKEN_ADMINISTRATIE`. Vul in de interface alleen deze **variabelenaam** in, nooit het token zelf. Tokens staan niet in SQLite, exports of logs.
4. Open Integraties & synchronisatie → Koppeling toevoegen. Vul naam, generieke provider, basis-URL, geheime variabelenaam en interval in (30–86400 seconden).
5. Kies per categorie: Niet synchroniseren, ROEFS ONE leidend (export), Extern leidend (import), of Beide systemen (tweerichtingsverkeer met conflictbeoordeling).
6. Activeer. De worker controleert capabilities en verwerkt de categorieën. Alleen een werkelijk voltooide run krijgt Geslaagd; configuratie alleen krijgt geen succesclaim. Nu in wachtrij zetten is een verzoek om verwerking, geen bevestiging van synchronisatie.
7. Controleer de eerste run en enkele records aan beide zijden. Laat externe profielen zonder toegang inactief.

De expliciete testvariabele `ROEFS_SYNC_ALLOW_LOOPBACK_TEST=1` maakt uitsluitend lokale HTTP-testservers mogelijk. Gebruik die niet buiten geïsoleerde tests. Productie vereist tevens egressbeperking op netwerkniveau; de applicatiecontrole alleen is geen volledige bescherming tegen DNS-rebinding of een kwaadwillende toegestane API.

## Categorieën en voorrang

Verwerkingsvolgorde: klanten, medewerkers, artikelen/materialen, locaties, contracten, opdrachten, diensten, uren, facturen. Zo kunnen externe referenties naar lokale IDs worden vertaald. Ontbreekt een voorafgaande koppeling, dan wordt de wijziging niet met een onbewezen lokaal nummer opgeslagen.

| Categorie | Tabel | Typische velden |
|---|---|---|
| customers | customers | name, contact, email, phone, city, status |
| employees | employees | name, role, email, phone, contract_hours, status |
| articles | articles | code, name, unit, rate, vat_rate, status |
| objects | objects | name, customer_id, address, city, type, frequency, status |
| contracts | contracts | name, customer_id, object_id, monthly_value, start_date, end_date, status |
| workorders | workorders | object_id, employee_id, description, date, hours, status, signed_by |
| shifts | shifts | object_id, employee_id, date, start_time, end_time, status |
| hours | hours | employee_id, shift_id, date, hours, status |
| invoices | invoices | number, customer_id, contract_id, amount, due_date, status |

Het contract synchroniseert de expliciete basisvelden. Uitgebreide V5-workflowvelden, goedkeuringsidentiteiten, documenten en factuurregels worden niet via willekeurige externe velden overschreven. Bestaande gekoppelde V5-procesrecords worden bij inkomende wijzigingen ter beoordeling vastgehouden. De volledige rijke ERP-mapping is dus PARTIAL en vereist een leverancierspecifiek schema.

Leidend zijn is geen toestemming om gelijktijdige wijzigingen kwijt te raken. Wijzigingen aan de niet-leidende kant en veranderingen aan beide kanten worden vastgehouden. Bij tweerichtingsverkeer wordt een wijziging aan slechts één kant toegepast wanneer de bekende andere versie ongewijzigd is.

## API-contract roefs-sync-v1

Iedere aanvraag bevat `Authorization: Bearer <token>`. Antwoorden zijn JSON-objecten, maximaal 2 MB. Geen redirects. Verzoek-timeout 10 seconden.

`GET {base}/capabilities`:

```json
{"protocol":"roefs-sync-v1","categories":["customers","employees","articles","objects","contracts","workorders","shifts","hours","invoices"],"write":true,"idempotency":true,"conditional_updates":true}
```

`GET {base}/records/{category}` en vervolgens `?cursor=<next_cursor>`:

```json
{"items":[{"id":"klant-123","revision":"4","fields":{"name":"Fictieve klant BV","contact":"Demo contact","email":"demo@fictief.invalid","phone":"000","city":"Teststad","status":"Actief"}}],"next_cursor":null}
```

Maximaal 500 records per pagina en 100 pagina’s per categorie/run. Iedere run leest de gepagineerde verzameling opnieuw; dit is geen webhook- of incrementele changefeed. Een externe verwijdering moet als expliciet record met `deleted:true`, stabiele id en nieuwe revision worden aangeleverd. Afwezigheid uit een lijst wordt nooit als verwijdering geïnterpreteerd.

Uitgaand nieuw record: `POST {base}/records/{category}`, `Idempotency-Key: <vaste sleutel>`, `If-None-Match: *`. Bestaand record: `PUT .../{external_id}`, dezelfde idempotentieregel en `If-Match: <bekende revision>`. Body:

```json
{"roefs_id":"42","fields":{"name":"Fictieve klant BV","contact":"Demo","email":"demo@fictief.invalid","phone":"000","city":"Teststad","status":"Actief"}}
```

Het antwoord bevat `id`, nieuwe `revision` en exact de bevestigde `fields`. De externe API moet een herhaalde idempotentiesleutel ook na een storing dezelfde uitkomst geven en een onjuiste revisie weigeren met 409 of 412. De adapter controleert capabilities maar kan de eerlijkheid van een onbekende externe API niet bewijzen. Voor echte leveranciers is een afzonderlijke contracttest verplicht.

Referentievelden bevatten aan de externe kant externe IDs. Bedragen worden als decimale tekenreeksen verstuurd. Datums zijn ISO `YYYY-MM-DD`. Er is geen automatische BTW-/boekhoudkundige interpretatie buiten het vastgelegde contract.

## Conflicten, retry en herstel

Unieke SQL-koppelingen verbinden externe én lokale identiteit. Mogelijke semantische duplicaten (klantnaam, medewerker-e-mail, artikelcode, factuurnummer) worden niet automatisch samengevoegd. Een expliciete koppeling vereist overeenkomende velden. Conflicten tonen beide snapshots; beheer motiveert extern overnemen, lokaal verzenden met externe versiecontrole, expliciet koppelen of de categorie pauzeren.

Bij gelijktijdige lokale wijzigingen weigert de conflictoplossing een verouderde lokale versie. Laat een nieuwe synchronisatie de snapshots verversen. Externe wijzigingen na de gelezen versie veroorzaken bij push opnieuw een conflict. Verwijderen wordt nooit stilzwijgend doorgezet; beoordeel archivering handmatig.

Retries gebruiken exponentiële vertraging tot maximaal één uur. De outbox bewaart payload en idempotentiesleutel vóór verzending. Na een mogelijk verloren antwoord wordt eerst de oude poging afgemaakt, ook als lokaal inmiddels opnieuw is gewijzigd. Daarna kan de nieuwere versie volgen. Er is een werklease, periodiek vernieuwd tijdens verwerking; een verlopen lease kan na een procesuitval worden overgenomen.

Na backupherstel staan koppelingen uit en zijn gebruikerssessies ingetrokken. Bekijk extern verwerkte opdrachten, open outbox en conflicten voordat je weer activeert. Er zijn geen automatische fysieke verwijderingen, verborgen betaalacties of externe factuurverzendingen buiten de expliciet geconfigureerde gegevenssynchronisatie.
