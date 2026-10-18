# Keuze na inloggen: Oud Portaal / Nieuw Portaal

Datum: 19 oktober 2026.

Na een succesvolle login verschijnt **Kies je portaal**. **Oud Portaal** opent het bestaande Amocean-dashboard. **Nieuw Portaal** opent de bestaande 3D-wereld, met dezelfde modules, gegevens en serverrechten. Het dashboard is tijdens de keuze verborgen en inert. Het keuzescherm wacht niet op optionele dashboardwidgets.

Op het oude startscherm staat **Portaal kiezen**. De knop **Sluiten** in de 3D-wereld gaat terug naar het oude portaal. Herladen in dezelfde tab behoudt de keuze; uitloggen, sessieverlies en een nieuwe login wissen die keuze. De tijdelijke keuze in `sessionStorage` bevat alleen de omgeving en een accountaanduiding, geen wachtwoord of authenticatietoken. Directe links naar toegankelijke 3D-modules behouden hun bestemming.

De wijziging zit in de presentatie-uitbreiding, scoped CSS en gebouwde `spatial.js`. De bestaande loginfunctie wordt aangeroepen zonder wijziging van haar authenticatieverzoeken. Python, SQLite, serverrechten en bedrijfsfuncties zijn niet gewijzigd. Bestaande browserfixtures kiezen nu expliciet Oud Portaal voordat hun werkfuncties worden getest.

## Controles

- Zeven nieuwe browsertests controleren beide echte bestemmingen, toetsenbordfocus, mobiel op 320/390/768 pixels, opslaan van de tijdelijke keuze, herladen, uitloggen en wisselen van account, mislukte login, vertraagd laden van de bundel, vertraagde dashboardwidgets, directe links en de WebGL-fallback met medewerkerrechten.
- De negen bestaande cinematische integratietests zijn uitgevoerd: alle 45 beheermodules, bestaande klantopslag, browsergeschiedenis, serverweigering voor medewerkers, planning verslepen, werkbonchecklists en opruimen bij uitloggen.
- De tien bestaande portaaltests controleren onder meer alle modules, zeven schermformaten, CRUD en XSS, medewerkersuren, rechten, planningconflicten, suggesties, CSV-export en rondleiding.
- De acht JavaScript-tests en de frontendbuild zijn uitgevoerd. De Docker-controle vergelijkt de werkelijk geserveerde JS/CSS met de werkmap. De afzonderlijke logs heten `portal-choice-*.txt`.

**Definitief: 34 verschillende geselecteerde tests geslaagd, 0 definitief mislukt, 0 overgeslagen.** Dit zijn 7 nieuwe browsertests (6 in `portal-choice-tests.txt` en de afzonderlijk toegevoegde widget-racetest), 9 cinematische integratietests, 10 bestaande portaaltests en 8 JavaScript-tests. Gerichte herhalingen worden niet extra geteld. Build en Docker-controle slagen aanvullend. De definitief geserveerde JS heeft SHA-256 `b9bedc9aec8aa32e22c195985b220334359d264391070b424ada01d0d3801281`; CSS heeft SHA-256 `4073b1ea65c7b2be2c64000e996a2c5e05790f7ae597bbabd380194662ddef00`.

Een tussencontrole vond horizontale kaartoverflow op 320 pixels; grid-minimumbreedtes en de mobiele indeling zijn hersteld. Een bestaande algemene modulecontrole verwachtte voor de eerder toegevoegde zelfstandige gegevensruimte ten onrechte `#content`. Die controle test nu ook de werkelijke zoekinterface van die module; de gerichte herhaling slaagt. De eerste run staat in `portal-choice-legacy-initial.txt`. De nieuwe navigatie wordt daarbij niet overgeslagen.

In een tussenrun werd het keuzescherm na vertraagd laden niet binnen de wachttermijn gevonden. De keuze wordt inmiddels vóór het laden van optionele widgets aangemaakt; zowel de afzonderlijke herhaling als de definitieve cookie-/bundelcontrole slagen. De extra test met een bewust vastgehouden echt dashboardverzoek bevestigt dat de gebruiker al een portaal kan openen voordat de widgets antwoorden.

Desktop en mobiel zijn visueel bekeken. Afbeeldingen: `portal-choice-desktop.png` en `portal-choice-mobile.png`.

De browsercontroles gebruiken Chromium en waar nodig software-WebGL; fysieke iPhone/Android-apparaten en Safari zijn niet getest. De volledige historische suite, een onafhankelijke beveiligingscontrole en belastingtests zijn niet opnieuw uitgevoerd. Er wordt geen productiegeschiktheid of actieve Render-deployment vastgesteld. GitHub-publicatie wordt bij oplevering met het commitnummer bevestigd.
