# Checklist vóór productiebeoordeling

Status: **geen productiegeschiktheid vastgesteld**. Deze checklist is geen certificering.

- [ ] Accepteer en sluit ontbrekende scope uit FUNCTIEMATRIX/BEKENDE-PROBLEMEN expliciet af.
- [ ] Onafhankelijke penetratietest, OWASP-autorisatie-/sessie-/uploadonderzoek en dependency/container-scan.
- [ ] Definitieve rechtenmatrix per afdeling/rayon, privacygrondslagen, minimale HR-velden en bewaartermijnen.
- [ ] Geharde HTTPS-deployment, strikte CSP, rate limiting, logbewaking, procesherstart en incidentprocedure.
- [ ] Geen default/testaccounts of testtokens; correcte secretbeheerder, MFA-herstelprocedure en accountlevenscyclus.
- [ ] Encryptie/toegangsbeheer van database, documenten, backups en TOTP-geheimen; offsite herstelproef.
- [ ] Langdurige gemengde belasting op doelhardware, beoogde gelijktijdigheid, SQLite-locking, p95/p99, geheugen en foutbudget.
- [ ] Fysieke iOS/Safari/Android, tablet, toetsenbord/screenreader en bedrijfsnetwerkacceptatie.
- [ ] Echte leverancierconnectorcontracten, OAuth-refresh indien nodig, veldmapping, richting en leidend systeem vastgesteld.
- [ ] Externe idempotentie/If-Match, delete-/archiefbeleid, outage-/retry-/dubbele worker-/hersteltests met leverancier.
- [ ] Egressallowlist, DNS-rebindingmaatregelen, monitoring bij verlopen tokens en vastgelopen synchronisatie.
- [ ] Fiscale factuurnummers, btw, creditprocessen en boekhoudexport afgestemd met accountant/bestaand systeem.
- [ ] Cao-/rusttijd-/arbeidstijdenregels inhoudelijk en technisch gevalideerd.
- [ ] Documentmalwarescanning, retentie-uitvoering en ondertekening passend bij juridische eisen.
- [ ] Expliciete toestemming vóór publieke deployment of verwerking van echte bedrijfsgegevens.
