# transform.ipynb — flagi towarowe

Notebook dokłada do pełnego kalendarza (TowId × Data razem z ruchami magazynowymi) cztery flagi na poziomie towaru:

| Flaga | Znaczenie |
|---|---|
| `JestWazony` | towar sprzedawany na wagę |
| `CzyMartwyWTymDniu` | w danym dniu przerwa w sprzedaży przekroczyła indywidualny próg towaru (zmienia się w czasie) |
| `CzyMartwyNaKoniecDanych` | towar jest martwy na ostatni dzień danych (jedna wartość na TowId) |
| `CzySezonowy` | towar ma sezonowy rytm sprzedaży (regularnie milknie na długie okresy) |

Flagi nic nie usuwają z danych. Dopisują kolumny, a decyzję o filtrowaniu podejmujesz w analizie.

## Uruchamianie

1. Najpierw uruchom `calendar.ipynb`, który zapisuje `dane/interim/fact_inka_calendar.parquet`.
2. Uruchom `transform.ipynb` od góry do dołu (**Run All**). Potrzebuje modułu `utils/tools.py` (funkcja `hash_danych_bezpieczny`).

## Wejście i wyjście

| | Plik | Rozmiar | Skąd |
|---|---|---|---|
| Wejście | `dane/interim/fact_inka_calendar.parquet` | 9 485 872 wierszy × 30 kolumn | wynik `calendar.ipynb` |
| Wyjście | `dane/interim/fact_inka_final.parquet` | 9 485 872 wierszy × 38 kolumn | ten notebook |

Sumy kontrolne (`tools.hash_danych_bezpieczny`, sortowanie po `TowId`, `Data`):

- wejście: `dd831a813d662099be81de7050891487f7e95808cf0c2aad19404e7a4484ef6e`
- wyjście: `9b255e47616b01ade38ff34994625ddd177e811d38b9cf67603066667506da3a`

W kalendarzu wiersz z `DokId = -1` to sztuczny "pusty dzień" (towar nie miał tego dnia żadnego dokumentu). Każdy wiersz z `DokId != -1` to realny dokument: sprzedaż (`TypDok == 21`) albo inny ruch magazynowy (PZ, BO, REM itd.).

## Parametry

| Parametr | Wartość | Komórka | Znaczenie |
|---|---|---|---|
| próg ułamkowych ilości | 50 % | 6 | od jakiego odsetka ułamkowych ilości towar uznajemy za ważony |
| `N_MINIMUM` | 550 dni | 9 | dolna granica progu "martwy" |
| `MARGINES` | 1,5 | 9 | ile razy dłuższa od typowej przerwy musi być obecna przerwa |
| `PROG_SEZONOWY` | 100 dni | 11 | od jakiej typowej przerwy towar uznajemy za sezonowy |

## Kolumny dodane przez notebook

| Kolumna | Typ | Opis |
|---|---|---|
| `JestWazony` | bool | towar ważony (ta sama wartość we wszystkich wierszach danego TowId) |
| `DataOstatniejSprzedazy` | data | data ostatniej sprzedaży (`DokId != -1` i `TypDok == 21`) do tego dnia włącznie; przed pierwszą sprzedażą puste |
| `DniOdSprzedazy` | liczba | liczba dni od `DataOstatniejSprzedazy` do daty wiersza |
| `PrzerwaHistoryczna95pct` | liczba | 95. percentyl przerw (w dniach) między kolejnymi dniami sprzedaży, osobno dla każdego TowId; puste, gdy towar miał tylko jeden dzień sprzedaży |
| `PrognMartwy` | liczba | indywidualny próg martwoty: `max(550, 1,5 × PrzerwaHistoryczna95pct)`; towar bez przerwy dostaje 550 |
| `CzyMartwyWTymDniu` | int8 (0/1) | 1, gdy `DniOdSprzedazy >= PrognMartwy`; wiersze przed pierwszą sprzedażą dostają 0 |
| `CzyMartwyNaKoniecDanych` | int8 (0/1) | 1, gdy dni od ostatniej sprzedaży do ostatniego dnia danych `>= PrognMartwy`; ta sama wartość w każdym wierszu TowId |
| `CzySezonowy` | int8 (0/1) | 1, gdy `PrzerwaHistoryczna95pct >= 100` |

## Opis komórek

Numeracja dotyczy **komórek kodu** (15 sztuk, tak jak liczysz w VS Code). Trzy komórki markdown (nagłówki sekcji) nie mają numeru: „Flagi towarowe” stoi przed komórką 3, „Towary wazone” przed komórką 4, „CzyMartwy — brak sprzedaży w ostatnich N dniach” przed komórką 9.

### Komórka 1 — importy i ścieżki
Importuje `sys`, `os`, `re`, `pandas`, `numpy`, `Path`. Przechodzi do katalogu głównego projektu (`os.chdir("../..")`), ale tylko jeśli nie jest już w katalogu `analiza_sprzedazy_w_sklepie`, więc komórkę można uruchamiać wielokrotnie. Dodaje katalog projektu do `sys.path` i importuje `utils.tools` jako `tools`.

### Komórka 2 — suma kontrolna wejścia
Liczy hash pliku `fact_inka_calendar.parquet` i go wypisuje. Porównaj go z hashem u kolegi, żeby mieć pewność, że obaj pracujecie na identycznych danych. Ustawia też zmienną `nazwa_pliku`, której używa następna komórka.

### Komórka 3 — wczytanie danych
Wczytuje kalendarz do `df_flagi`. Na tej tabeli działają wszystkie kolejne komórki.

### Komórka 4 — odsetek ułamkowych ilości
Dla każdego TowId liczy:
- `LiczbaTransakcji` — liczba wszystkich wierszy towaru w tabeli (razem z pustymi dniami i ruchami innymi niż sprzedaż),
- `LiczbaUlamkowych` — liczba wierszy, w których `IloscPlus` jest ułamkiem (`IloscPlus % 1 != 0`),
- `PctUlamkowych` — odsetek ułamkowych w procentach.

Wypisuje statystyki (`describe`). Wynik: 12 481 TowId, mediana 0 %, maksimum 97,2 %. Czyli prawie żaden towar nie jest sprzedawany ułamkowo, a te, które są, mają bardzo wysoki odsetek.

### Komórka 5 — wykrywanie wagi po nazwie
Definiuje `czy_nazwa_sugeruje_wage(nazwa)`. Funkcja:
1. zamienia nazwę na wielkie litery,
2. usuwa wzorce "liczba + KG" (np. `0,5KG`, `1,65KG`), bo to stała gramatura opakowania,
3. zwraca `True`, jeśli w reszcie nazwy zostało samodzielne słowo `KG` (np. `SURÓWKA KG`).

Pod funkcją jest test kontrolny na 6 przykładach (3 gramatury → `False`, 3 towary na wagę → `True`).

### Komórka 6 — finalna flaga `JestWazony` per TowId
1. Bierze unikalne pary `TowId` – `NazwaTow` i liczy `NazwaSugerujeWage`.
2. Łączy je z wynikami z komórki 4.
3. Towar jest ważony, gdy `PctUlamkowych >= 50` **lub** nazwa sugeruje wagę.
4. Zapisuje zbiór `lista_wazonych_towid`.

Wynik: **193 ważone TowId**, z czego 118 złapała tylko nazwa (mają poniżej 50 % ułamkowych, bo waga zaokrągla ilości). Komórka wypisuje też listę tych 118.

### Komórka 7 — przypisanie `JestWazony` do wierszy i kontrola
Dodaje do `df_flagi` kolumnę `JestWazony` (czy `TowId` należy do `lista_wazonych_towid`). Wypisuje liczbę wierszy: 367 506 ważonych i 9 118 366 pozostałych. Potem pokazuje, z jakich asortymentów pochodzą ważone towary (cukierki na wagę, sery na wagę, warzywa, owoce, wędliny na wagę itd.). To kontrola sensowności, czy lista wygląda wiarygodnie.

### Komórka 8 — duplikat komórki 7
Identyczny kod i identyczny wynik jak w komórce 7. Można ją usunąć.

### Komórka 9 — flagi `CzyMartwyWTymDniu` i `CzyMartwyNaKoniecDanych`
Próg martwoty jest indywidualny dla każdego towaru, dzięki czemu towar sezonowy nie jest uznawany za martwy tylko dlatego, że jest poza sezonem. Wszystko jest liczone wyłącznie na sprzedaży (`DokId != -1` i `TypDok == 21`), więc ruchy PZ, BO czy REM nie "ożywiają" towaru.

1. Sortuje tabelę po `TowId`, `Data` i tworzy maskę `jest_sprzedaz`.
2. `DataOstatniejSprzedazy` — data wiersza tam, gdzie jest sprzedaż, a następnie przeniesienie ostatniej znanej daty w dół (`ffill`) w obrębie TowId.
3. `DniOdSprzedazy` — różnica w dniach między datą wiersza a `DataOstatniejSprzedazy`.
4. Przerwy historyczne — unikalne dni sprzedaży dla każdego TowId, różnica między kolejnymi dniami = `Przerwa`.
5. `PrzerwaHistoryczna95pct` — 95. percentyl przerw dla TowId (odporny na pojedyncze wyjątki, w przeciwieństwie do maksimum). Zapamiętuje też datę ostatniej sprzedaży każdego TowId.
6. `PrognMartwy = max(N_MINIMUM, MARGINES × PrzerwaHistoryczna95pct)` — towar z długimi, regularnymi przerwami dostaje wyższy próg, a podłoga 550 dni chroni towary z krótką historią. Towar z jednym dniem sprzedaży nie ma przerwy, więc dostaje samą podłogę.
7. `CzyMartwyWTymDniu = DniOdSprzedazy >= PrognMartwy`. Wiersze przed pierwszą sprzedażą towaru dostają 0.
8. `CzyMartwyNaKoniecDanych` — czy liczba dni od ostatniej sprzedaży do ostatniego dnia danych jest `>= PrognMartwy`. Ta sama wartość w każdym wierszu danego TowId.

Dlaczego dwie flagi: kalendarz jest przycięty do "ostatnia sprzedaż + 14 dni", więc po "śmierci" towaru nie ma już wierszy, w których licznik dni mógłby urosnąć do progu. `CzyMartwyWTymDniu` zapala się więc tylko przy bardzo długiej przerwie w środku życia towaru albo na ruchu (PZ, ST itd.) zapisanym długo po ostatniej sprzedaży. Towary, które przestały się sprzedawać, wskazuje `CzyMartwyNaKoniecDanych`.

Komórka wypisuje liczbę wierszy dla każdej wartości `CzyMartwyWTymDniu`, liczbę TowId dla `CzyMartwyNaKoniecDanych` oraz statystyki `PrognMartwy`.

Wynik na pełnych danych z `fact_inka_calendar.parquet`:
- `CzyMartwyWTymDniu`: 16 704 wiersze z 1 (w 801 TowId), 9 469 168 z 0. Spośród wierszy z 1: 15 519 to puste dni (długa przerwa w środku życia towaru), 1 185 to ruchy inne niż sprzedaż, a 0 to dni ze sprzedażą.
- `CzyMartwyNaKoniecDanych`: 3 098 TowId z 1, 9 383 z 0. To bardzo blisko 3 097 martwych towarów z wcześniejszej analizy rotacji.
- `PrognMartwy`: od 550 do 1 420,5 dnia, średnia ok. 553,1.
- Wiersze przed pierwszą sprzedażą towaru (puste `DataOstatniejSprzedazy`): 39 469.

### Komórka 10 — rozkład `PrzerwaHistoryczna95pct`
Wypisuje statystyki i percentyle (50, 75, 90, 95, 99 %) tej kolumny dla unikalnych TowId. Służy do świadomego wyboru progu sezonowości zamiast zgadywania. Kolumna jest liczona na samej sprzedaży. Towary z jednym dniem sprzedaży nie mają przerwy i nie wchodzą do statystyk.

| Percentyl | 50 % | 75 % | 90 % | 95 % | 99 % |
|---|---|---|---|---|---|
| dni | 16 | 39,9 | 109,8 | 199 | 400,6 |

Przerwę da się policzyć dla 11 846 TowId. Pozostałe 635 ma tylko jeden dzień sprzedaży.

### Komórka 11 — flaga `CzySezonowy`
Ustawia `PROG_SEZONOWY = 100` dni (taka sama wartość jak dawny próg "zagrożony" w kategorii rotacji, tuż przy 90. percentylu). Towary, których `PrzerwaHistoryczna95pct >= 100`, trafiają do `towid_sezonowe`. Do `df_flagi` trafia kolumna `CzySezonowy`. Wypisuje liczbę unikalnych TowId z flagą i bez niej.

Wynik: **1 297 sezonowych TowId** (10,4 %), 11 184 pozostałych. Dla porównania, przy progu 150 dni byłoby ich 837, przy 200 dniach 590, a przy 250 dniach 404.

### Komórka 12 — zmiana typów i podgląd
Zamienia `CzySezonowy`, `CzyMartwyWTymDniu` i `CzyMartwyNaKoniecDanych` na `int8` (0/1), żeby zajmowały mało miejsca i bezproblemowo zapisywały się do parquet. 






