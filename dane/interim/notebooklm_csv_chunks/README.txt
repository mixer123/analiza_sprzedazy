Eksport fact_inka_hard_flagged_wazone.parquet do formatu obslugiwanego przez NotebookLM (CSV)
================================================================================================

Zrodlo: dane/interim/fact_inka_hard_flagged_wazone.parquet
Wiersze: 8 802 515, kolumn: 34
Rozmiar oryginalu (parquet, skompresowany): ~82 MB

NotebookLM ma limit 500 000 slow i 200 MB NA JEDNO ZRODLO (oraz limit liczby zrodel na notebook,
zalezny od planu - np. 50 dla konta darmowego). Cala tabela w jednym pliku znaczaco przekracza
oba limity, dlatego podzielono ja na 353 pliki CSV po 25 000 wierszy kazdy (ostatni plik ma
2 515 wierszy). Kazdy plik ma wlasny naglowek kolumn, wiec jest samodzielnym zrodlem.

Maksymalna liczba slow w pojedynczym pliku (zmierzone): 463 924 (< limit 500 000, margines ~7%).
Kazdy plik: ~6-7 MB (znacznie ponizej limitu 200 MB).

Pliki: fact_inka_hard_flagged_wazone_part_001.csv ... fact_inka_hard_flagged_wazone_part_353.csv
Kolejnosc wierszy zachowana jak w oryginalnym pliku parquet (part_001 = pierwsze 25000 wierszy, itd.)

Uwaga: 353 plikow prawdopodobnie przekracza limit liczby zrodel w jednym notebooku NotebookLM
(zalezny od planu, dla darmowego to 50). Rozwaz zaimportowanie ich partiami do kilku osobnych
notebookow, albo sprawdz aktualny limit zrodel dla swojego konta.
