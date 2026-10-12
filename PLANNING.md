# Planning gebruiken en begrijpen

De oorspronkelijke weekplanner blijft werken. **Werkruimte → Slimme planning** biedt dag/week/maand en groepering op datum, medewerker, team, klant, locatie of gereserveerd materieel. Filter op afdeling, medewerker en klant. Open een dienst voor exacte tijden, medewerker, locatie, status en planningsnotitie.

Sleep naar een dag of medewerker om te verplaatsen. Het formulier is het volwaardige toetsenbord- en touchalternatief. **Einde +15 minuten** verandert het formulier; pas Opslaan schrijft. Losse diensten kunnen 1–52 weken worden gekopieerd. De server ondersteunt batches tot 100 diensten en slaat een batch uitsluitend in zijn geheel op.

Een gekoppelde teamopdracht heeft één tijdvak. Alle teamdiensten moeten daarop aansluiten. Annuleer eerst de gekoppelde diensten en wijzig dan de opdracht wanneer het tijdvak moet veranderen; een losse sleepactie mag geen uiteenlopende tijdvakken in één opdracht veroorzaken. Dit is bewust strikter dan een onbeperkte teamplanner.

## Verplichte servercontroles

- Geldige datum en tijden; diensten op dezelfde dag, eindtijd na begintijd.
- Actieve medewerker, geen overlappende actieve dienst.
- Geen goedgekeurd verlof/verzuim of geregistreerde onbeschikbaarheid.
- Dekking door beschikbaarheidsblokken, als deze zijn opgegeven.
- Juiste team, vereiste vaardigheden en geldige certificaten bij gekoppelde opdrachten.
- Beschikbaar materieel, geldige keuring, geen onderhoud op de geplande datum en geen botsende reservering.
- Voldoende medewerkers vóór Toegewezen/In uitvoering.
- Voldoende tussenruimte voor expliciet geregistreerde reistijden met bron.
- Actuele recordversie; een gelijktijdige wijziging geeft 409 en wordt niet overschreven.

Niet-geregistreerde beschikbaarheid blijft **onbevestigd**. Contracturen, arbeidstijdenwet, cao/rusttijd, vaardigheden die niet geregistreerd zijn en ontbrekende reistijden vragen menselijke beoordeling. Er worden geen reistijden verzonnen.

## Suggesties

Bij een opdracht: **Medewerkers voorstellen**. De lijst vermeldt score en redenen; uitgesloten medewerkers krijgen concrete redenen. Instellingen bevatten gewichten voor geregistreerde beschikbaarheid, werkbelasting, locatiekennis, regio en overlappende vaardigheden. Werkbelasting trekt punten af; positieve criteria tellen erbij op. Gelijke scores worden stabiel op medewerkers-ID gesorteerd. Verplichte kwalificaties worden nooit met een gewicht omzeild. De planner kiest zelf een geschikte medewerker.

## Geschiedenis en terugdraaien

Iedere nieuwe planningsmutatie krijgt een historie-item met vorige recordinhoud en resulterende versie. Terugdraaien kan alleen als geen volgende mutatie heeft plaatsgevonden en de vorige situatie opnieuw alle controles doorstaat. Een nieuwe dienst wordt geannuleerd, niet stilzwijgend weggehaald. Oude routes hebben audit, maar niet dezelfde volledige undo-historie.
