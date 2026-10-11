# ROEFS ONE — bijgewerkte demonstratie

Voortgebouwd op **ROEFS-ONE-NL-MOBIEL-FIX (2).zip**. De oorspronkelijke Python-backend, SQLite-database, twintig bedrijfsmodules en Amocean-dagstart zijn behouden. Beschikbaarheid is als extra module toegevoegd. Na inloggen blijft het eerste scherm **‘Hoi Beheerder. Wat wil je doen?’**.

## Starten

Python 3.10 of nieuwer is voldoende; de applicatie heeft geen externe Python-pakketten nodig.

```bash
python3 start.py
```

Op macOS kan ook `bash START.command`; op Windows `py -3 start.py` of `START.bat`. Het script toont het lokale adres en de nieuw gegenereerde demoaccountwachtwoorden in je eigen terminal. Gebruik uitsluitend fictieve gegevens.

Voor de bestaande gratis tijdelijke Cloudflare-link:

```bash
bash START-GRATIS-24U.command
```

Hiervoor moet `cloudflared` geïnstalleerd zijn. De link blijft afhankelijk van een draaiende computer, internet en Cloudflare; de historische bestandsnaam “24U” garandeert geen 24 uur beschikbaarheid.

## Wat is verbeterd

- Vaste account–medewerkerkoppeling, servercontrole van eigen dossiers en objecten, instelbare extra inzage en blokkeren/resetten van accounts.
- Validatie van alle 21 CRUD-modules, beschermde verwijdering van gekoppelde gegevens, unieke factuurnummers en controle op dubbele of onmogelijke urenregistraties.
- Transactionele roostercontrole: overlap, verlof/verzuim en opgeslagen beschikbaarheid gelden ook bij SOS en goedgekeurde werkstromen.
- Weekplanning met beschikbaarheidsmeldingen en medewerkerssuggesties; een suggestie kan een echt dienstformulier voorbereiden.
- Medewerkers kunnen eigen uren indienen, beschikbaarheid/verlof vastleggen, logboekmeldingen toevoegen en werkbonnen bijwerken. Beheer keurt uren en verlof goed.
- Nederlandse formulieren en keuzevelden, actuele widgets, beveiligde CSV-export, verbeterde mobiele navigatie, toetsenbordfocus en interactieve rondleiding in echte schermen.
- Startscript met gereedheidscontrole, automatische SQLite-reservekopie en verbeterde Docker-start als gebruiker zonder rootrechten.

## Documentatie en tests

- [INSTALLATIE.md](INSTALLATIE.md): starten, bijwerken, backups, tunnel en Docker.
- [ARCHITECTUUR.md](ARCHITECTUUR.md): bronanalyse, bestanden, modules, rechten en API's.
- [TESTRAPPORT.md](TESTRAPPORT.md): uitsluitend daadwerkelijk uitgevoerde controles, fouten en beperkingen.
- [MOBIEL-TESTPLAN.md](MOBIEL-TESTPLAN.md): aanvullende acceptatie op echte telefoons.
- [BEVEILIGING.md](BEVEILIGING.md): herstelde fouten en nog noodzakelijke productiecontroles.

```bash
python3 run_tests.py --backend-only
# Met Playwright en Chromium geïnstalleerd:
python3 run_tests.py --load
```

Dit pakket is een ontwikkel- en demonstratieversie. Het is **niet als productiegeschikt vastgesteld**. De externe tunnelverbinding kon in de bouwomgeving niet worden gevalideerd door een DNS/netwerkbeperking. De lokale applicatie en Docker-container zijn afzonderlijk getest. Een iPhone-emulatie in Chromium is geen test met een fysieke iPhone of Safari.
