> Historisch meetpunt. Actuele migratieversie: zie V6-FINAL-FUNCTIEMATRIX.md, V6-FINAL-TESTRAPPORT.md en V6-MIGRATION-REPORT.md.

# V6 prestatiemetingen — ontwikkelstand

12 oktober 2026. Geen productie-SLA of bewijs voor 250 gelijktijdige gebruikers.

Dataset: 250 fictieve medewerkers, aanvankelijk 800 klanten, 1600 locaties, 5001 opdrachten/diensten/urenregels per tabel. Per proef 100 HTTP-verzoeken, 80% lezen/20% schrijven. Na de mutaties: 820 klanten. Mix: gepagineerde lijsten, weekkalender, rapportage en klantaanmaak. Loopback HTTP op de cloudontwikkelmachine; geen externe ERP/tunnel. Ruwe machine-/CPU-/SQLitegegevens in de JSON-bestanden.

| Gelijktijdige verzoeken | Mediaan | p95 | p99 | Fouten | Zichtbare HTTP 503 | Bemonsterde RSS |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 5,17 ms | 151,96 ms | 173,40 ms | 0 | 0 | 35,12 MB |
| 8 (hervatting) | 26.43 ms | 1731.89 ms | 2076.24 ms | 0 | 0 | 60.57 MB |
| 16 | 57,67 ms | 2003,88 ms | 2261,88 ms | 0 | 0 | 77,45 MB |
| 32 | 212,29 ms | 3764,51 ms | 3862,63 ms | 0 | 0 | 98,70 MB |

Bronnen: reports/load-enterprise-1.json, -8.json, -16.json en -32.json. De proeven met 1/16/32 horen bij het eerdere tweede ontwikkelblok. Alleen de rij met 8 is bijgewerkt naar de volledige hervattingsrun met 123 tests en HTTP-workerbegrenzing. Dit zijn verschillende bronstanden, geen gezamenlijke finale benchmark. De ruwe JSON-bestanden corresponderen met de getoonde waarden.

SQLite integrity_check was ok; geen foreign-keyovertredingen. CPU betreft het serverleven inclusief fixtures/startup. RSS is bemonsterd, geen gegarandeerde piek. Lockcontention is alleen via zichtbare HTTP 503 gemeten; interne wachttijd niet afzonderlijk geïnstrumenteerd. Geen duurtest, crashherstel onder maximale belasting of fysieke productiehardware.

De bestaande Python/SQLite-architectuur is behouden. Paginering/SQL-scope beperken de oorspronkelijke CRUD-lijsten. Niet iedere ondersteunende keuzelijst, export of rapport is al begrensd. De stijgende p95 onder 32 gelijktijdige verzoeken moet met Roefs’ acceptatiedoel en doelhardware worden vergeleken voordat een eventuele gecontroleerde architectuurwijziging wordt besloten.
