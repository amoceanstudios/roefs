# Beveiliging en grenzen

Broninspectie en automatische regressies zijn uitgevoerd. Dit is geen onafhankelijke penetratietest, AVG-audit of productiecertificering.

## Aanwezige maatregelen

- Willekeurige initiële demoaccountwachtwoorden via `start.py`; direct starten met een nieuwe database zonder expliciete wachtwoorden wordt geweigerd. Nieuwe accountwachtwoorden zijn 12–200 tekens.
- PBKDF2-SHA256 met unieke salt; bestaande hashes hebben hun historische 250.000 iteraties en worden na succesvolle login opgewaardeerd naar 600.000. Bestaande wachtwoorden blijven geldig; forceer vóór echt gebruik een passend wachtwoordbeleid.
- Hoog-entropische sessies, uitsluitend gehasht in SQLite; acht uur verval, logout en intrekken na blokkeren, rol-/wachtwoordwijziging of MFA-wijziging.
- Browser gebruikt HttpOnly/SameSite=Strict-cookie, geen bedrijfsdata of sessiegeheim in localStorage/sessionStorage. CSRF-token op cookie-authenticatie bij mutaties. Bearer-authenticatie blijft beschikbaar voor bestaande API-clients.
- Secure-cookie standaard op directe server en bij tunnelstart. `start.py` zet voor uitsluitend lokale HTTP-demo standaard Secure uit. Achter HTTPS/reverse proxy expliciet `ROEFS_COOKIE_SECURE=1` instellen.
- Optionele TOTP: wachtwoordhercontrole bij configuratie, actuele code vóór activeren, beperkte klokmarge en blokkering van hergebruikte codes. Geen zelfbedachte externe MFA-service.
- Loginbegrenzing per waargenomen IP/gebruikersnaam; generieke fouten. JSON-contenttype, beperkte body, geen chunked input, geen NaN/Infinity.
- Expliciete rollen en objectafscherming op de server. Medewerkers krijgen uitsluitend gekoppeld werk, eigen uren en eigen/private gekoppelde documenten. Geen vertrouwen in browserrol of opgegeven eigenaarschap.
- Parameterbinding voor SQL; dynamische tabel/veldnamen uit vaste interne allowlists. HTML-escaping en formulebeveiliging bij CSV.
- Headers tegen MIME-sniffing, framing en refererlekken. Same-Origincontrole bij wijzigingen.
- Additieve migraties, transactiegebonden validatie, versies voor V5-processen, beschermde workflowhandelingen en traceerbare audit.
- Private bestandspaden met willekeurige sleutels; bestandsnaam-/type-/groottecontrole, SHA-256, geautoriseerde downloads; geen openbare upload-URL’s of uitvoerbare HTML-uploads.
- Externe connectorhost-allowlist, HTTPS, geen redirects, geen credentials in URLs, timeouts, begrensde antwoorden, geen tokens in database of logboek.
- Volledige backup/herstel met controlesommen, integriteitscontrole, weigering van onveilige archiefpaden en bestaande doelmap. Herstel pauzeert connectors en trekt sessies in.

## Rollenmatrix

De uitvoerbare matrix staat in `services/access.py`; niet in de frontend.

| Rol | Hoofdbevoegdheid |
|---|---|
| Systeembeheerder | Alle modules, accounts, configuratie, integraties |
| Bedrijfsbeheerder | Organisatiebreed beheer binnen deze enkele bedrijfsomgeving |
| Directeur | Lezen en rapportage; geen bedrijfswijzigingen, gebruikers of loonadministratie |
| Operationeel manager | Operationele modules en uren; geen facturatie of accountbeheer |
| Planner | Planning, opdrachten, beschikbaarheid, verlof en middelen; geen financiële of gebruikersmutaties |
| Leidinggevende | Operationele uitvoering, werkbon-/urenbeoordeling, verlof, kwaliteit, logboek |
| Medewerker | Alleen eigen/toegewezen operationele gegevens; geen goedkeuringsrechten |
| Financieel beheerder | Financiële modules en voorbereiding; zakelijke inzage voor de factuurketen |
| Auditor | Lezen/audit, geen bedrijfswijzigingen; geen gebruikers of loonadministratie |

De toepassing ondersteunt één bedrijf, geen cryptografisch gescheiden multi-tenantomgeving. Leidinggevenden hebben organisatiebrede operationele bevoegdheden, geen uitgewerkte rayon/afdelingsscope. Directeur/auditor kunnen operationele persoonsgegevens lezen; een definitief privacybeleid en veldmatrix voor echt gebruik moeten worden vastgesteld.

## Resterende beveiligingsrisico’s

- De stdlib HTTP-server is geen geharde publieke productie-webserver. Geen onafhankelijke rate-limitdienst, requestworkerpool, WAF of centrale monitoring.
- Bestaande inline eventhandlers/stijlen vereisen CSP `unsafe-inline`. Stored-XSS-scenario’s zijn getest, maar een strikte nonce/hash-CSP en onafhankelijke aanvalstest ontbreken.
- Rate limiting is in het procesgeheugen en geen bescherming tegen alle gedistribueerde aanvallen. MFA heeft geen herstelcodes of volledig selfservice-herstel; geen e-mailreset/SSO.
- SQLite, audit, backups en TOTP-geheimen zijn niet versleuteld. Beveilig filesystem, toegang, opslagmedia en backups. Audit is niet cryptografisch onveranderbaar.
- Historische tekst-ID’s hebben geen volledige SQL-foreign keys; directe SQL kan applicatieregels omzeilen. Oude clients zonder If-Match hebben niet dezelfde versiegarantie als V5.
- Uploadvalidatie is geen antivirus/content-disarm. Afbeeldingen worden niet opnieuw gecodeerd. Geen formele digitale ondertekening, OCR of automatische privacyclassificatie.
- SSRF-controles reduceren risico maar vereisen aanvullende egressregels; er is geen volledig gepinde DNS/TLS-netwerkstack. Leverancierstoegang en OAuth-refresh zijn niet gevalideerd.
- Geen formele fiscale toets: conceptfacturen, credits en CSV zijn administratieve voorbereiding, geen vervanging van gecertificeerde boekhouding. Geen definitieve fiscale nummerreeks of e-invoice-standaard.
- Documentretentie wordt vastgelegd; automatische vernietiging en herstelbewaarbeleid zijn niet geactiveerd.

Gebruik uitsluitend fictieve gegevens tot afzonderlijke beveiligings-, integratie-, privacy- en duurbelastingbeoordelingen zijn afgerond.
