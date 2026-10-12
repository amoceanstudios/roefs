# API-contract

JSON over HTTP onder `/api`. Fouten hebben `{"error":"Nederlandse toelichting"}`. 400 invoer, 401 authenticatie/MFA, 403 rechten/CSRF, 404 afgeschermd of onbekend, 409 conflict, 413 te groot, 415 contenttype, 428 ontbrekende versie, 429 begrenzing, 503 database tijdelijk niet beschikbaar. Mutaties zijn transactioneel; geen succesantwoord vóór commit.

## Authenticatie

- `POST /login`: username, password, optioneel code. Retourneert sessiecookie, token voor bestaande API-clients, csrf, username en role.
- `GET /me`: actuele rol/dossierkoppeling/extra rechten en csrf.
- `POST /logout`: trekt de huidige sessie in.
- Cookieclients sturen `X-CSRF-Token` bij POST/PUT/DELETE. API-clients kunnen `Authorization: Bearer ...` gebruiken.
- `GET /v5/security/mfa/status`, `POST /v5/security/mfa/setup|enable|disable`. Configuratie vereist huidig wachtwoord; enable/disable ook code.
- `GET /v5/sessions`, `POST /v5/sessions/revoke` met id uit eigen sessielijst.

## Bestaande interfaces

`/records/{module}[/{id}]` behoudt GET/POST/PUT/DELETE voor de oorspronkelijke 21 modules. De UI stuurt If-Match bij bewerken. Gekoppelde V5-procesrecords vereisen specifieke endpoints. `/users`, `/users/update`, `/users/link`, `/users/permissions` blijven beheerdersroutes. Planning/SOS, berichten, HR/CAO, autopilot en oude dashboards blijven aanwezig; autorisatie wordt opnieuw op de server toegepast.

## Nieuwe interfaces

| Route | Methode | Werking |
|---|---|---|
| `/v5/home` | GET | Actuele dagelijkse tellers en dezelfde record-ID-selecties voor doorklik |
| `/v5/metadata` | GET | Rolafhankelijke modules, extra velden en schrijfrechten |
| `/v5/entities/{module}` | GET | `{items,total,limit,offset}`; q, status, sort, direction, limit≤100, offset en relevante relationele filters |
| `/v5/entities/{module}/{id}` | GET/PUT/DELETE | Individueel record; versie verplicht bij mutatie |
| `/v5/entities/{module}` | POST | Nieuwe stamgegevens met basis- en extra validatie |
| `/v5/resources/{table}[/{id}]` | GET/POST/PUT/DELETE | Teams, contacten, certificaten, reistijden en artikelen |
| `/v5/customers/{id}/timeline` | GET | Klant, locaties, contacten, contracten, opdrachten, eigen audithistorie |
| `/v5/customers/import` | POST | rows: 1–200 klantobjecten; atomaire batch |
| `/v5/planning/calendar` | GET | from/to maximaal 63 dagen; filters employee_id/team_id/customer_id/object_id/department/asset_id |
| `/v5/planning/suggest` | POST | object_id, date, start_time, end_time, optioneel workorder_id/exclude_shift_id; candidates/excluded met redenen |
| `/v5/shifts[/{id}]` | POST/PUT | Dienst opslaan; update vereist version |
| `/v5/planning/bulk` | POST | shifts: 1–100 dienstmutaties; geen gedeeltelijke opslag |
| `/v5/planning/undo` | POST | history_id; controleert laatst bekende versie en huidige conflicten |
| `/v5/workorders[/{id}]` | GET/POST/PUT | Nieuwe opdracht of detail met checklist, historie en diensten |
| `/v5/workorders/{id}/transition` | POST | version, state, reden waar verplicht; afrondingsnotitie bij Voltooid |
| `/v5/workorders/{id}/checklist` | POST | Nieuwe title of bestaande id/version/done |
| `/v5/workorders/{id}/pdf` | GET | Geautoriseerde werkbon-PDF |
| `/v5/hours[/{id}]` | GET/POST/PUT | employee_id, workorder_id, starts_at/ends_at mét offset, break_minutes, reason |
| `/v5/hours/{id}/review` | POST | version, status Goedgekeurd/Afgewezen, reason bij afwijzen |
| `/v5/invoices/prepare` | POST | workorder_id, version, hourly_rate, vat_rate, optioneel lines |
| `/v5/invoices/{id}/review` | POST | version, status, reden bij afwijzing |
| `/v5/invoices/{id}/credit` | POST | version en verplichte reden; volledige creditcorrectie, geen betaling |
| `/v5/invoices/{id}/lines|pdf|csv` | GET | Werkelijke regels, PDF of administratieve CSV |
| `/v5/files` | GET/POST | Metadata of upload name/category/content(base64), klant/medewerker/opdracht en retentie |
| `/v5/files/{id}` | GET | Geautoriseerde download, geen statisch publiek pad |
| `/v5/reports[/{csv|pdf}]` | GET | from/to, department, customer_id; berekeningen en opgeslagen details |
| `/v5/notifications` | GET | Eigen meldingen |
| `/v5/notifications/read` | POST | Eigen meldings-id |
| `/v5/preferences` | GET/PUT | tour_step, tour_completed, notifications |
| `/v5/reminders/run` | POST | Beheer: deduplicerende deadlinecontrole |
| `/v5/settings` | GET/PUT | Organisatie, categorieën, afdelingen, gewichten, retentie |
| `/v5/audit` | GET | actor/module-filter, maximaal 200 resultaten |
| `/v5/sync` | GET | Configuratie, echte runs, conflicten en gebeurtenissen |
| `/v5/sync/connections[/{id}]` | POST/PUT | Configuratie, version bij update; tokens alleen als variabelenaam |
| `/v5/sync/connections/{id}/schedule` | POST | In wachtrij zetten, geen valse voltooiingsmelding |
| `/v5/sync/conflicts/{id}` | POST | action, reason, local_version en eventueel local_id |

Nieuwe stamgegevens gebruiken POST/PUT/DELETE niet voor directe status-/bedragsmutaties van V5-procesrecords. Gebruik de specifieke werkopdracht-, uren-, planning- en factuurhandelingen.

Bedragen zijn decimale strings; berekening per factuurregel rondt half-up op twee decimalen. Verrekeningen van afrondingen, fiscale uitzonderingen of complexe creditreeksen vereisen externe boekhoudcontrole. Tijden voor uren moeten geldig zijn in Europe/Amsterdam; dubbelzinnige kloktijden vragen de expliciete offset.

Voor het externe connectorprotocol, versievoorbeelden, limieten en verwijderbeleid: [INTEGRATIES.md](INTEGRATIES.md).
