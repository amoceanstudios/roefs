# Klantcase Basisschool De Egel — testresultaat

Datum: 13 oktober 2026. Uitgevoerd in de lokale cloudontwikkelomgeving.

- `python run_tests.py`: exitcode 0; 157 tests geslaagd in 210,586 seconden.
- Oorspronkelijke API-controles: 65 geslaagd.
- Oorspronkelijke planning-/rechtencontroles: 18 geslaagd.
- Logo, Nederlandse labels, navigatie en widgetvernieuwing: geslaagd.
- Gerichte klantcase-HTTP-tests op de definitieve servicecode: 3 geslaagd
  in 2,544 seconden, waaronder de uitvoering-tot-conceptfactuurketen.
- Chromium-browsertest (390×844): startknop, daadwerkelijke opslag,
  zes diensten in de presentatieweek, herladen en medewerker toewijzen
  zonder extra dienst: geslaagd, ook binnen de volledige testset.
- JavaScript-syntaxis (`node --check enterprise.js`): geslaagd.

De volledige unittest-uitvoer staat in `reports/all-tests.txt`.
Geen mislukte of overgeslagen tests in deze run. Geen nieuwe belastingtest,
publieke Render-controle, Safari-test of productieacceptatie uitgevoerd.

De case maakt negen gekoppelde werkbonnen en negen open diensten, maar geen
gewerkte uren of facturen. Alleen de geautomatiseerde test doorloopt uitvoering,
urenbeoordeling en factuurvoorbereiding, in een tijdelijke database met een
expliciet testtarief. Die testgegevens worden niet naar Render overgebracht.

Het eenmalig opslaan op Render moet na deployment via de nieuwe startknop
gebeuren. De bestaande MIGRATION-READY ZIP blijft de vorige release.
