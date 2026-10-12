# Gebruikershandleiding

## Beginnen

Log in met het door `start.py` gegenereerde fictieve account. De Amocean-dagstart blijft het eerste scherm. Gebruik het zijmenu of de dagelijkse acties. Op een telefoon opent ☰ het menu; sluit met de sluitknop, de achtergrond of Escape. Terug en vooruit gebruiken browsergeschiedenis; de app blokkeert de gebaren van je besturingssysteem niet.

De eerste dagstart biedt een rondleiding. Starten, volgende/vorige stap, sluiten en later opnieuw starten zijn mogelijk. De stappen gebruiken echte schermen en markeren hun bediening. Voortgang en afgerond/overgeslagen-status worden per account op de server bewaard.

## Een gekoppelde opdracht uitvoeren

1. Werkruimte → Relaties: klant toevoegen, factuuradres en klantnummer vastleggen. Klantdossier toont locaties, contacten, contracten, opdrachten en wijzigingen.
2. Objecten: meerdere werklocaties aan dezelfde klant koppelen. Contactpersonen kunnen apart worden toegevoegd.
3. Contracten: klant, locatie, bedrag, looptijd, verlengdatum en dienstverlening vastleggen.
4. Medewerkers/Teams/Certificeringen: vaardigheden, team, afdeling, regio en certificaatvervaldatums bijhouden. Gebruik uitsluitend operationeel noodzakelijke informatie; geen medische details.
5. Materieel: machine en keuring vastleggen. Werkopdrachten → Nieuw: locatie, dienst, datum/tijden, capaciteit, vereiste vaardigheden/certificaten en materieel selecteren.
6. Opdracht openen: checklisttaken toevoegen, naar Gepland zetten en Medewerkers voorstellen kiezen. Na voldoende toewijzingen naar Toegewezen.
7. Medewerker opent de eigen opdracht, start deze, vinkt uitgevoerde taken af, voegt een foto/bestand toe en registreert uren. Uren vragen begin/einde mét UTC-offset voor Europe/Amsterdam en pauzeminuten.
8. Gereedmelden naar Voltooid vereist afgeronde checklist en afrondingsnotitie. Een ingevulde aftekennaam is een tekstuele bevestiging, geen gekwalificeerde elektronische handtekening.
9. Leidinggevende beoordeelt werkbon en uren. Afgewezen uren en correctie/heropenen vragen een reden. Factureerbaar kan pas nadat de ingediende uren zijn goedgekeurd.
10. Financieel beheer kiest Factuur voorbereiden, controleert tarief en btw, bekijkt regels en keurt het concept goed. Download PDF of boekhoud-CSV. De voorbereidingsdialoog ondersteunt naast het uurtarief optionele materiaal- en materieelregels; de API ondersteunt tot 100 extra regels.
11. Rapportages tonen opgeslagen planning, goedgekeurde uren, opdrachten en conflicten met datum-, afdeling- en klantfilters.

## Meldingen, bestanden en rechten

Mijn meldingen bevat alleen aan jouw account gerichte interne meldingen. Je kunt gelezen/ongelezen bijhouden en ontvangst instellen. De dagelijkse achtergrondcontrole maakt deduplicerende deadlineherinneringen zolang de server draait; Instellingen kan de controle ook direct uitvoeren. Er wordt geen e-mail of push verzonden.

Bestanden worden buiten de openbare webbestanden bewaard en geautoriseerd gedownload. Koppel ze aan klant, medewerker of opdracht. Toegestaan: PNG/JPG/PDF/UTF-8-tekst, maximaal 600 kB per bestand. PDF’s worden gedownload; er is geen ongecontroleerde actieve inline preview of antivirusgarantie.

Beheer maakt accounts, koppelt medewerkers en kiest een rol. Rollen worden op iedere serverhandeling gecontroleerd. Een verouderd formulier kan worden geweigerd: vernieuw, vergelijk en sla opnieuw op; herhaal niet blind dezelfde wijziging.

Via **Beveiliging** kun je een authenticator koppelen voor verificatie in twee stappen. Bewaar de sleutel veilig. Na activeren/deactiveren vervallen eigen sessies. Er is geen automatische e-mailreset of uitgewerkt MFA-herstel met herstelcodes; verlies van de sleutel vereist een gecontroleerde herstelprocedure door beheer.

## Automatische synchronisatie

Zie [INTEGRATIES.md](INTEGRATIES.md). Configureer eerst de API en geheimen op de server, kies per categorie welk systeem leidend is en activeer daarna de koppeling. De geschiedenis laat echte resultaten zien. Conflicten worden niet automatisch weggewerkt; vergelijk beide versies en motiveer een besluit. Na herstel uit backup staan koppelingen uit totdat je ze opnieuw beoordeelt.
