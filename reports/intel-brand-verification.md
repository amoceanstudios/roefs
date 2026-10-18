# AMOCEAN INTEL — Midnight Flash

Datum: 19 oktober 2026.

## Vormgeving en naam

- De zichtbare productnaam is **AMOCEAN INTEL**: login, laadscherm, portaalkeuze, oude navigatie, planningkop, browser­titels, rondleiding, synchronisatielabels en PDF-koppen. Nieuwe authenticatorconfiguraties gebruiken ook deze productnaam. Bestaande authenticatorgeheimen en accounts zijn niet aangepast.
- Een lokaal meegeleverde **Alfa Slab One** geeft titels het karakter van stevige jaren-90-filmtitels: warm geel, gebroken wit en een donkere rode schaduw. Bedieningslabels, tabellen en formulieren houden een leesbaar sans-seriflettertype.
- Het nachtelijke oceaanbeeld is specifiek voor deze interface gegenereerd in fotografische stijl, met hard flitslicht op water en natte rotsen, diepe nachtblauwe schaduwen en filmkorrel. Het is geen echte locatieopname. Het WebP-bestand is circa 247 KiB; het ongewijzigde font circa 95 KiB. Credits en de volledige fontlicentie staan in `assets/`.
- De 3D-wereld gebruikt het beeld ook als textuurvlak achter de moduleobjecten. Koudere frontale flitsbelichting en een donkerblauwe vloer sluiten aan op de foto. De bestaande subtiele camerabeweging, uitschakelbare flits en reduced-motionbediening blijven beschikbaar. Audioknoppen staan op mobiel boven de introductie, zodat ze de grotere filmtitels onderaan niet overlappen.
- **Oud Portaal** en **Nieuw Portaal** blijven na inloggen beschikbaar zoals eerder gebouwd. De productnaam verandert geen bestaande gegevens, accountnamen, routes, versies, factuurnummering of configuratiesleutels. Interne namen zoals `ROEFS_DB` en bestaande API-beleidswaarden blijven compatibel.

Python/SQLite en de bedrijfslogica blijven behouden. De serverwijzigingen bestaan uit productteksten en expliciete statische routes voor achtergrond en font. Alleen logo, achtergrond en font zijn via die routes bereikbaar; er is geen algemene bestandstoegang toegevoegd. De CSP is niet verruimd en er zijn geen externe font- of beeldverzoeken nodig tijdens gebruik.

## Daadwerkelijk uitgevoerde controles

| Controle | Definitieve uitkomst |
| --- | --- |
| Bestaande portaalkeuze, echte bestemmingen, mobiel, accountwissel en vertraagde widgets | 7 geslaagd |
| Nieuwe merk-, asset-, font-, browser-, PDF- en authenticatorcontroles | 4 geslaagd |
| JavaScript-adapters en wereldmodellen | 8 geslaagd |
| Start, herstart, backup, poortcontrole en lokale tunnelgereedheid | 4 geslaagd |
| MFA, sessies, backup/herstel en beveiligde bestanden | 4 geslaagd |
| Synchronisatie, conflicten, dubbele records, uitval en herstel | 13 geslaagd |
| Bestaand mobiel werkpaneel en hoge kwaliteit met shaders/transmissie | 1 geslaagd |

**41 verschillende geselecteerde tests geslaagd, 0 definitief mislukt en 0 overgeslagen.** De vier nieuwe merktests zijn uitgevoerd als drie browsertests plus de afzonderlijk toegevoegde PDF/authenticatorcontrole. De wereldtest is na aanvullende mobiele controles opnieuw uitgevoerd; deze herhalingen worden niet extra geteld. Logs: `intel-brand-*-tests.txt`.

De browser controleert dat het echte font laadt, de WebP decodeert, de nieuwe naam zichtbaar is, beide portalen openen en de bediening op 320/390 pixels bereikbaar blijft. Bij onbekende assets en padtraversal blijft met een geldig testaccount de respons 404. De eerste versie van die test verwachtte ook zonder account 404; de bestaande authenticatie geeft daar eerst 401. De test gebruikt nu een geldig fictief account om de daadwerkelijke routering te controleren. De serverbeveiliging is daarvoor niet aangepast.

De frontendbuild slaagt. De bijgewerkte Docker-controle vergelijkt niet alleen JS/CSS, maar ook de daadwerkelijk geserveerde foto en het font met de SHA-256-hashes van de werkmap en controleert de nieuwe productnaam in de HTML. Zie `intel-brand-container-test.txt` en `cinematic-docker-smoke.json`.

Visueel bekeken: `intel-login.png`, `intel-choice-desktop.png`, `intel-choice-mobile.png`, `intel-world.png` en `intel-world-mobile.png`.

## Grenzen

Chromium met software-WebGL is gebruikt; fysieke iPhone/Android-apparaten en Safari zijn niet gevalideerd. De volledige historische testsuite en representatieve GPU-/belastingmetingen zijn niet opnieuw uitgevoerd. Dit bewijst geen 60/30-fps-doel en geen productiegeschiktheid. Video, GLB, KTX2/Basis en Draco blijven buiten deze wijziging. Externe ERP-koppelingen worden door deze vormgeving niet actief gemaakt.

Deze controles betreffen de lokale broncode en container. GitHub-publicatie wordt bij oplevering met het commitnummer bevestigd; een actieve Render-deployment is hiermee niet bewezen.
