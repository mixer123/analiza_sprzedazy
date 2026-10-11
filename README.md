# transform.ipynb — flagi towarowe

Notebook dokłada do pełnego kalendarza (TowId × Data razem z ruchami magazynowymi) cztery flagi na poziomie towaru:

| Flaga | Znaczenie |
|---|---|
| `CzyWazony` | towar sprzedawany na wagę (w komórce 8 powstaje jako `JestWazony`, komórka 13 zmienia nazwę) |
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
- wyjście: `6023598440fc4b0d8f3deef28619ed5d35394a666e4a9e8affdaa45cb1d98672`

Hash wyjścia zmienił się względem poprzednich wersji (`9b255e47…`, `4c3f2689…`), bo zmieniły się typy kolumn (m.in. `Producent` jest `int16`, `CzyWazony` jest `int8`) i nazwa jednej kolumny. Hash zależy od typów i nazw kolumn, nie tylko od wartości.

W kalendarzu wiersz z `DokId = -1` to sztuczny "pusty dzień" (towar nie miał tego dnia żadnego dokumentu). Każdy wiersz z `DokId != -1` to realny dokument: sprzedaż (`TypDok == 21`) albo inny ruch magazynowy (PZ, BO, REM itd.).

## Parametry

| Parametr | Wartość | Komórka | Znaczenie |
|---|---|---|---|
| próg ułamkowych ilości | 50 % | 7 | od jakiego odsetka ułamkowych ilości towar uznajemy za ważony |
| `N_MINIMUM` | 550 dni | 9 | dolna granica progu "martwy" |
| `MARGINES` | 1,5 | 9 | ile razy dłuższa od typowej przerwy musi być obecna przerwa |
| `PROG_SEZONOWY` | 100 dni | 11 | od jakiej typowej przerwy towar uznajemy za sezonowy |

## Kolumny dodane przez notebook

| Kolumna | Typ | Opis |
|---|---|---|
| `CzyWazony` | int8 (0/1) | towar ważony (ta sama wartość we wszystkich wierszach danego TowId) |
| `DataOstatniejSprzedazy` | data | data ostatniej sprzedaży (`DokId != -1` i `TypDok == 21`) do tego dnia włącznie; przed pierwszą sprzedażą puste |
| `DniOdSprzedazy` | liczba | liczba dni od `DataOstatniejSprzedazy` do daty wiersza |
| `PrzerwaHistoryczna95pct` | liczba | 95. percentyl przerw (w dniach) między kolejnymi dniami sprzedaży, osobno dla każdego TowId; puste, gdy towar miał tylko jeden dzień sprzedaży |
| `PrognMartwy` | int32 | indywidualny próg martwoty: `max(550, 1,5 × PrzerwaHistoryczna95pct)`, obcięty do całkowitych dni; towar bez przerwy dostaje 550 |
| `CzyMartwyWTymDniu` | int8 (0/1) | 1, gdy `DniOdSprzedazy >= PrognMartwy`; wiersze przed pierwszą sprzedażą dostają 0 |
| `CzyMartwyNaKoniecDanych` | int8 (0/1) | 1, gdy dni od ostatniej sprzedaży do ostatniego dnia danych `>= PrognMartwy`; ta sama wartość w każdym wierszu TowId |
| `CzySezonowy` | int8 (0/1) | 1, gdy `PrzerwaHistoryczna95pct >= 100` |

**Zmiana nazwy:** kolumna powstaje w komórce 8 jako `JestWazony`, a dopiero komórka 13 zmienia ją na `CzyWazony`. W pliku wynikowym jest `CzyWazony`. Jeśli kod w innych notebookach używa starej nazwy, trzeba go poprawić. Duplikat komórki, który nadpisywał kolumnę typem `bool`, został usunięty, więc kolumna jest teraz `int8`.

## Opis komórek

Numeracja dotyczy **komórek kodu** (15 sztuk, tak jak liczysz w VS Code). Trzy komórki markdown (nagłówki sekcji) nie mają numeru: „Flagi towarowe” stoi przed komórką 3, „Towary wazone” przed komórką 5, „CzyMartwy — brak sprzedaży w ostatnich N dniach” przed komórką 9.

### Komórka 1 — importy i ścieżki
Importuje `sys`, `os`, `re`, `pandas`, `numpy`, `Path`. Przechodzi do katalogu głównego projektu (`os.chdir("../..")`), ale tylko jeśli nie jest już w katalogu `analiza_sprzedazy_w_sklepie`, więc komórkę można uruchamiać wielokrotnie. Dodaje katalog projektu do `sys.path` i importuje `utils.tools` jako `tools`.

### Komórka 2 — suma kontrolna wejścia
Liczy hash pliku `fact_inka_calendar.parquet` i go wypisuje. Porównaj go z hashem u kolegi, żeby mieć pewność, że obaj pracujecie na identycznych danych. Ustawia też zmienną `nazwa_pliku`, której używa następna komórka. Wynik: `dd831a81…ef6e`.

### Komórka 3 — wczytanie danych
Wczytuje kalendarz do `df_flagi`. Na tej tabeli działają wszystkie kolejne komórki.

### Komórka 4 — zamiana typów kolumn
Zmniejsza zużycie pamięci przez zmianę typów:
- `Producent`: puste wartości zamienia na `-1` i rzutuje na `int16`.
- `TypDok`, `TypPoz`, `DokId`, `AsId`, `Kolejnosc`, `NrPozycji` → `int32`.
- `KolejnyWDniu`, `AktywnyDok`, `AktywnyTow`, `Mnoznik`, `WplywNaStan`, `CzyNiechciane` → `int8`.
- `EAN`: rzut na `int64`, potem na tekst, potem na `category`.

Na co uważać:
- `KolejnyWDniu` jest w słowniku dwa razy: raz z `int16`, raz z `int8`. W słowniku Pythona wygrywa ostatni wpis, więc kolumna kończy jako `int8`, a `int16` jest ignorowane. `int8` mieści tylko -128…127 i przy przekroczeniu zawija wartość po cichu. Jeśli chcesz `int16`, usuń drugi wpis (to samo dotyczy zdublowanego `Mnoznik`).
- `Producent` jako `int16` mieści do 32 767. Sprawdź `df_flagi['Producent'].max()`, żeby mieć pewność.
- `EAN` przez `int64` gubi zera wiodące, a przy pustej wartości rzut się wywróci. Bezpieczniej: `df_flagi['EAN'].astype('string').astype('category')`.

### Komórka 5 — odsetek ułamkowych ilości
Dla każdego TowId liczy:
- `LiczbaTransakcji` — liczba wszystkich wierszy towaru w tabeli (razem z pustymi dniami i ruchami innymi niż sprzedaż),
- `LiczbaUlamkowych` — liczba wierszy, w których `IloscPlus` jest ułamkiem (`IloscPlus % 1 != 0`),
- `PctUlamkowych` — odsetek ułamkowych w procentach.

Wypisuje statystyki (`describe`). Wynik: 12 481 TowId, średnia 0,68 %, mediana 0 %, maksimum 97,2 %. Prawie żaden towar nie jest sprzedawany ułamkowo, a te, które są, mają wysoki odsetek. Mianownik zawiera puste dni i ruchy, więc odsetek jest zaniżony (to dlatego część ważonych towarów ma tylko kilka do kilkunastu procent).

### Komórka 6 — wykrywanie wagi po nazwie
Definiuje `czy_nazwa_sugeruje_wage(nazwa)`. Funkcja:
1. zamienia nazwę na wielkie litery,
2. usuwa wzorce "liczba + KG" (np. `0,5KG`, `1,65KG`), bo to stała gramatura opakowania,
3. zwraca `True`, jeśli w reszcie nazwy zostało samodzielne słowo `KG` (np. `SURÓWKA KG`).

Pod funkcją jest test kontrolny na 6 przykładach (3 gramatury → `False`, 3 towary na wagę → `True`). Wynik zgodny z oczekiwaniem.

### Komórka 7 — finalna flaga `JestWazony` per TowId
1. Bierze unikalne pary `TowId` – `NazwaTow` i liczy `NazwaSugerujeWage`.
2. Łączy je z wynikami z komórki 5.
3. Towar jest ważony, gdy `PctUlamkowych >= 50` **lub** nazwa sugeruje wagę.
4. Zapisuje zbiór `lista_wazonych_towid`.

Wynik: **193 ważone TowId**, z czego 118 złapała tylko nazwa (mają poniżej 50 % ułamkowych). Komórka wypisuje też listę tych 118.

### Komórka 8 — przypisanie `JestWazony` do wierszy i kontrola
Dodaje do `df_flagi` kolumnę `JestWazony` jako `int8` (1, gdy `TowId` należy do `lista_wazonych_towid`). Wypisuje liczbę wierszy: 9 118 366 z 0 i 367 506 z 1. Potem pokazuje, z jakich asortymentów pochodzą ważone towary (CUKIERKI WAGA 42, SERY WAGA 33, WARZYWA 31, OWOCE 19 itd.). To kontrola sensowności listy.

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
9. Rzutuje obie flagi na `int8`, a `PrognMartwy` na `int32` (ułamek jest obcinany, np. 1 420,5 → 1 420).

Dlaczego dwie flagi: kalendarz jest przycięty do "ostatnia sprzedaż + 14 dni", więc po "śmierci" towaru nie ma już wierszy, w których licznik dni mógłby urosnąć do progu. `CzyMartwyWTymDniu` zapala się więc tylko przy bardzo długiej przerwie w środku życia towaru albo na ruchu (PZ, ST itd.) zapisanym długo po ostatniej sprzedaży. Towary, które przestały się sprzedawać, wskazuje `CzyMartwyNaKoniecDanych`.

Wynik na pełnych danych:
- `CzyMartwyWTymDniu`: 16 704 wiersze z 1, 9 469 168 z 0.
- `CzyMartwyNaKoniecDanych`: 3 098 TowId z 1, 9 383 z 0.
- `PrognMartwy`: od 550 do 1 420 dni, średnia ok. 553,13.

### Komórka 10 — rozkład `PrzerwaHistoryczna95pct`
Wypisuje statystyki i percentyle (50, 75, 90, 95, 99 %) tej kolumny dla unikalnych TowId. Służy do świadomego wyboru progu sezonowości zamiast zgadywania. Towary z jednym dniem sprzedaży nie mają przerwy i nie wchodzą do statystyk.

| Percentyl | 50 % | 75 % | 90 % | 95 % | 99 % |
|---|---|---|---|---|---|
| dni | 16 | 39,9 | 109,8 | 199 | 400,6 |

Przerwę da się policzyć dla 11 846 TowId (maksimum 947 dni). Pozostałe 635 ma tylko jeden dzień sprzedaży.

### Komórka 11 — flaga `CzySezonowy`
Ustawia `PROG_SEZONOWY = 100` dni (tuż przy 90. percentylu). Towary, których `PrzerwaHistoryczna95pct >= 100`, trafiają do `towid_sezonowe`. Do `df_flagi` trafia kolumna `CzySezonowy` (na razie jako `bool`). Wypisuje liczbę unikalnych TowId z flagą i bez niej.

Wynik: **1 297 sezonowych TowId** (10,4 %), 11 184 pozostałych.

### Komórka 12 — zmiana typów flag
Zamienia `CzySezonowy`, `CzyMartwyWTymDniu` i `CzyMartwyNaKoniecDanych` na `int8` (0/1), żeby zajmowały mało miejsca i bezproblemowo zapisywały się do parquet. Dla dwóch ostatnich to powtórzenie komórki 9, a rzutowanie `CzySezonowy` jest tu potrzebne. Komentarz mówi o „podglądzie jednego wiersza”, ale komórka już go nie wyświetla (`sample()` został usunięty).

### Komórka 13 — zmiana nazwy `JestWazony` na `CzyWazony`
`df_flagi.rename(columns={'JestWazony': 'CzyWazony'}, inplace=True)`. Od tej komórki w tabeli jest kolumna `CzyWazony`, a `JestWazony` już nie istnieje. Zmiana nazwy nie zmienia liczby kolumn (nadal 38).

### Komórka 14 — zapis wyniku
Zapisuje `df_flagi` do `dane/interim/fact_inka_final.parquet` (kompresja zstd, bez indeksu) i wypisuje rozmiar: `(9 485 872, 38)`. Zmienia też `nazwa_pliku` na plik wynikowy.

### Komórka 15 — suma kontrolna wyniku
Liczy hash pliku `fact_inka_final.parquet`. Po każdej zmianie kodu policz go ponownie i uzgodnij z kolegą. Wynik: `60235984…8672`. Zapisany w komentarzu hash jest już aktualny, ale komentarz „hash poniżej pochodzi ze starej wersji (37 kolumn)” jest nieaktualny i można go usunąć.

## Kontrola braków (poza notebookiem)

W notebooku nie ma komórki z `df_flagi.isna().sum()`. Jeśli ją uruchomisz, spodziewaj się:
- `Producent` — po komórce 4 braków nie ma, bo są zamienione na `-1`. Przed zamianą było ich 2 220 956 (dziura w danych źródłowych, nie błąd mapowania).
- `PrzerwaHistoryczna95pct` — puste dla towarów z jednym dniem sprzedaży (635 TowId). `PrognMartwy` ma wtedy wartość podłogi, więc braków nie ma.
- `DataOstatniejSprzedazy` i `DniOdSprzedazy` — po 39 469 pustych wierszy: wiersze sprzed pierwszej sprzedaży towaru (np. BO albo PZ zapisane wcześniej).
- Pozostałe kolumny — brak pustych wartości.
