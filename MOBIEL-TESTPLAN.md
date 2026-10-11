# Mobiele acceptatie

## Geautomatiseerd uitgevoerd

De browser gebruikt de echte Python-server, tijdelijke SQLite-data en echte HTTP-verzoeken; er zijn geen API-mocks. Chromium is getest op breedtes 320, 375, 390, 412, 768, 1024 en 1440 px. De tests controleren de dagstart, planning, uren, berichten, accounts, HR, CAO en rondleiding op pagina-overloop. Alle beheerschermen openen afzonderlijk. Menu openen/sluiten, volledig door het menu scrollen, toetsenbordfocus, Escape, browser terug/vooruit, CRUD-formulieren, medewerkersuren/beschikbaarheid en het voorbereiden/opslaan van een plannersuggestie zijn getest.

Screenshots: `reports/mobile.png` en `reports/desktop.png`. Actuele aantallen en uitkomsten staan in `TESTRAPPORT.md` en `reports/all-tests.txt`.

## Nog uit te voeren op echte apparaten

1. Open de tunnel-HTTPS-link in Safari op een fysieke iPhone en in Chrome op een Android, ook via mobiel internet. Voer eerst de extra linktoegang in en log daarna in als beheerder.
2. Controleer het Amocean-logo en ‘Hoi Beheerder. Wat wil je doen?’. De startpagina mag niet worden vervangen door het cijferdashboard.
3. Open het menu, scrol helemaal naar beneden, kies een module, sluit met achtergrond/knop en test toetsenbord/schermlezer.
4. Navigeer Start → Uren → Planning en veeg vanaf de linkerrand terug. Test ook vooruit. De browser bepaalt native veeggedrag; de applicatie registreert schermen in de geschiedenis. Vanaf het eerste scherm mag de browser de website verlaten.
5. Schuif de dagen van het weekoverzicht horizontaal zonder dat het hele document meeschuift. Open een dienst en test het toetsenbord, datum- en tijdkiezer.
6. Test portrait/landscape, 200% tekstvergroting, notch/safe areas en een open schermtoetsenbord. Controleer dat Opslaan en Annuleren bereikbaar blijven.
7. Log in als medewerker: controleer eigen planning, dien uren in, wijzig eigen beschikbaarheid en werk een werkbon bij. Controleer als beheerder het opgeslagen resultaat.
8. Probeer een dienst tijdens geregistreerd verlof te plannen. De server moet deze weigeren; ook bij SOS of een werkstroom.
9. Stuur een fictief bericht. Controleer de startteller en leesstatus bij beheer.
10. Loop de interactieve rondleiding af, onderbreek en start opnieuw. De uitleg mag zonder opslaan geen bedrijfsrecords wijzigen.

**Niet afgedekt door Chromium-emulatie:** echte iOS Safari/WebKit, systeemgebaren, VoiceOver/TalkBack, variaties in Android-toetsenborden en mobiele netwerkuitval. Deze punten staan open; de browserdownload voor WebKit was in de bouwomgeving niet beschikbaar.
