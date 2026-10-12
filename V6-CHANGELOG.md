# V6 wijzigingen — lopende sprint

Voortgebouwd op V5; Python, SQLite, oorspronkelijke modules en Amocean-dagstart behouden. Geen definitieve V6-release of productieverklaring zolang de acceptatiechecklist openstaat.

- Beveiliging: MFA-herstelcodes en verloren-authenticatorflow, persistente inlogbegrenzing, sessie-inactiviteit, accountcontrole vóór sessieafgifte, scripts zonder inline uitvoering, HSTS in Secure-configuratie, controleerbare auditketen.
- Gegevens: optionele geauthenticeerde backupencryptie, ClamAV-interface/quarantaine, scanstatus en hercontrole, versiegebonden documentverwijdering, opt-in retentieworker.
- Planning: configureerbare demonstratieregels, pauzes, dag-/weekmaxima, rustcontrole, meerdaagse/herhaalde dagsegmenten, uitzonderingen, atomaire annulering/herstel, visuele eindtijdschuif met gekoppelde teamdiensten, vergrendeling van gesloten opdrachten.
- Operatie: persistente inklok-/uitklokregistratie via de bestaande urenvalidatie; meerdere contractlocaties/frequenties, geversioneerde contractbesluiten en contractgekoppelde opdrachten; interne conceptfactuurnummering.
- Rapporten: medewerkers-/materieelbenutting, klantactiviteit, contractprestaties, financiële voorbereiding met expliciete berekeningen en CSV/PDF.
- Sync: duurzame incrementele controlepunten, zichtbare uitval, veilig opnieuw aanbieden met dezelfde idempotentiesleutel, pauzeren bij ongeldige API-toegang.
- Interface/schaal: centrale toegestane UI-acties, serverpaginering/zoeken voor oude CRUD-schermen, Nederlandse formulieren voor nieuwe processen, trapsgewijze lokale belasting.

Details en bewijs: V6-VOORTGANG.md, V6-ISSUEREGISTER.md, V6-TESTRAPPORT.md. Open intern werk wordt niet als klantafhankelijkheid gepresenteerd.
