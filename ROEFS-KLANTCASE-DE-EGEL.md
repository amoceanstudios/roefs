# Basisschool De Egel — klantpresentatie

Toegevoegd op 13 oktober 2026, na expliciete toestemming om de opgegeven
klantnaam en het adres te gebruiken. Het eerdere fictieve schoolvoorbeeld
blijft beschikbaar; deze klantcase is een afzonderlijk dossier.

## Openen op Render

Deploy de nieuwste commit van `roefs-one-enterprise-v6`. Wacht op **Live**,
vernieuw de app en log in als beheerder. Op het oorspronkelijke Amocean-startscherm
staat **Klantcase Basisschool De Egel**. Kies de maandag van de presentatieweek,
bevestig de beschreven presentatieplanning en klik **Klantcase opslaan en openen**.
Een deployment alleen vult een bestaande database niet: dit opslaan moet eenmaal
op de gebruikte installatie gebeuren. Opnieuw openen of opslaan maakt geen dubbelen.
Een al aanwezige klant met dezelfde naam blokkeert de aanmaak ter controle;
bestaande klantgegevens worden niet overschreven of automatisch samengevoegd.

## Wat wordt opgeslagen?

- Klant/debiteur: Basisschool De Egel, Europalaan 44, 1111 AA Eindhoven,
  letterlijk volgens het aangeleverde bericht.
- Een gekoppelde schoonmaaklocatie en een presentatiecontract met twee diensten.
- Interieurverzorging: ma 2, di 2, wo 3, do 2, vr 2,5 arbeidsuren;
  11,5 per week en 460 per 40 afgesproken lesweken.
- Vijf schoonmaakwerkbonnen voor één gekozen presentatieweek, vanaf 16:00.
- Vier glaswerkbonnen, inclusief buitenzijde gevelglas, binnenzijde gevelglas
  en separatieglas. Presentatiedatums: woensdag in week 0, 13, 26 en 39;
  het tijdvak 09:00–10:00 is uitsluitend een demonstratieaanname.
- Negen gekoppelde open diensten in de gewone planning, nog zonder medewerker.
- Checklists, bronkoppelingen en auditgeschiedenis in dezelfde SQLite-database.

De negen werkbonnen beginnen als **Concept**. Het presentatiecontract is actief
om de bestaande werkbonketen te gebruiken. De contractperiode van 365 dagen is
een presentatieperiode. Het contractbedrag 0 is een technische lege beginwaarde,
geen overeengekomen tarief. De opgegeven adresgegevens zijn niet geverifieerd.

## Presentatieroute

1. Open het klantdossier en toon klant, locatie, contract en gekoppelde opdrachten.
2. Kies **Presentatieweek in planning**: vijf schoonmaakdiensten en het eerste
   glasbezoek verschijnen in die week. De drie andere glasbezoeken staan later.
3. Open een werkbon en kies **Medewerkers voorstellen**. Inplannen vult de
   bestaande open dienst in, zonder er een tweede dienst naast te maken.
4. Doorloop de gewone werkbonstatussen, checklist en urenregistratie. Uren worden
   daadwerkelijk opgeslagen en moeten afzonderlijk worden goedgekeurd.
5. Factuurvoorbereiding volgt pas na de bestaande uitvoerings- en goedkeuringsstappen
   en het invoeren van een tarief. Het dossier toont werkelijk opgeslagen uren
   en facturen; er worden bij het voorbereiden geen fictieve financiële feiten geboekt.

Het volledige schoonmaakbestek, de echte lesweekkalender, glasdatums en -duur,
personeelsinzet, contractperiode en tarieven zijn nog niet aangeleverd.
De overige 39 schoonmaakweken worden dus niet als bevestigde uitvoering ingepland.
De term lesweken komt uit de klantopdracht: dit is de schoonmaakfrequentie.
Gebruik de presentatieplanning niet als bevestigde productieplanning.

## Tests en grenzen

Gerichte HTTP/SQLite-tests controleren opslag, koppelingen, kalender,
geen automatische uren/facturen, rechten, dubbele aanmaak, herstart en de
volledige uitvoering-tot-conceptfactuurketen in een tijdelijke testdatabase.
De browsertest controleert de startknop, aanmaken, mobiele weergave, planning,
medewerkertoewijzing zonder dubbele dienst en herladen.
Zie het bijbehorende testverslag voor de uitgevoerde resultaten.

De eerder geleverde MIGRATION-READY ZIP en verificatie horen bij de vorige
release. Deze uitbreiding wordt via de nieuwe GitHub-commit geleverd.
Een lokale test bewijst niet dat de Render-installatie al bijgewerkt of gevuld is.
Op Render Free kan deze lokale SQLite-opslag bij deployment/herstart verloren gaan.
