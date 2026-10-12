# Checklist vóór productiebeoordeling

**Geen productiegeschiktheid vastgesteld.** Technische tests en klantacceptatie zijn afzonderlijke stappen.

- [x] Additieve migratie, CSV/XLSX-proefrun, bevestiging, controlepunten en herimport technisch geïmplementeerd en met fictieve data getest.
- [x] Afdeling/rayonbeleid aangesloten; negatieve serverautorisatietests uitgevoerd.
- [x] Backup/herstel en pauzeren van externe verwerking technisch getest.
- [ ] Echte bronexports, identiteit/relaties, mapping, tellingen en inhoudelijke aansluiting door Roefs goedgekeurd.
- [ ] Definitieve rechtenmatrix en alle relevante records ingedeeld; personeelsaccounts en MFA/herstel gecontroleerd.
- [ ] Dataminimalisatie, privacygrondslagen, verwerkersafspraken, bewaartermijnen en cao-/arbeidstijdregels vastgesteld.
- [ ] Beveiligde doelomgeving met HTTPS, persistente opslag, voldoende geheugen, procesherstart, monitoring en incidentbeheer. Geen Render Free voor blijvende bedrijfsdata.
- [ ] Actieve opslag en offsite backups beschermd; herstel op doelinfrastructuur met afgesproken RPO/RTO geoefend.
- [ ] Onafhankelijke penetratietest, dependency-/container-scan en beveiligingsreview van echte inrichting.
- [ ] Malwarescanner beschikbaar en getest; documentretentie en handtekeningen passend bij het proces.
- [ ] Langdurige gemengde belasting met beoogde gelijktijdigheid op doelhardware; SQLite-locking/geheugen/p95/p99 en foutbudget beoordeeld.
- [ ] Fysieke iPhone/Safari/Android, tablet, toetsenbord/screenreader en bedrijfsnetwerkacceptatie.
- [ ] Boekhoudprovider, API/toegang, administratie, debiteur- en factuurbeleid bevestigd; echte adapter en end-to-endtest met idempotentie, storingen, retries en herstel geaccepteerd.
- [ ] Definitieve migratieplanning, freeze/delta, rollback, operationele acceptatie en expliciete go-livegoedkeuring vastgelegd in Roefs onboarding.

Een groene technische importtest zet bovenstaande klantbesluiten niet automatisch op voltooid.
