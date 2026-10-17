# transform.ipynb — kolumny wyliczane i flagi datowe

Druga część `transform.ipynb`, po flagach towarowych (`docs/transform_flagi_towarowe_butek.md`). Dokłada ruchy magazynowe, oczyszczone nazwy, kolumny i flagi datowe, usuwa kolumny pomocnicze, zmienia `TowId` na `SKU` i sprawdza dane przed zapisem `fact_inka_final.parquet`.

Krótkie opisy są w markdownach nad komórkami notebooka. Ten plik zbiera ustalenia i decyzje, które się tam nie mieszczą.

## Kolumny dodane

| Kolumna | Typ | Opis |
|---|---|---|
| `RuchMagazynowy` | float64 | ilość ruchu ze znakiem: `IloscBazowa` (wg `MetodaLiczenia`) × `Mnoznik` |
| `NazwaTowCzysta`, `NazwaAsortCzysta` | tekst | nazwy małymi literami, bez polskich znaków i symboli |
| `Rok`, `RokISO` | int16 | rok kalendarzowy i rok tygodnia ISO |
| `Miesiac`, `TydzienRokuISO`, `DzienTygodnia`, `DzienMiesiaca` | int8 | `DzienTygodnia`: 1 = pn … 7 = nd |
| `RokMiesiac` | category (uporządkowana) | `'YYYY-MM'`, kategorie w kolejności chronologicznej (ok. 10 MB zamiast ~144 MB jako tekst) |
| `NazwaDnia` | category (uporządkowana) | Poniedziałek … Niedziela, ze słownika (niezależnie od locale systemu) |
| `CzySwieto` | int8 (0/1) | **tylko** święto ustawowe, także w długim weekendzie (uwaga: wcześniej pod tą nazwą było „święto lub niedziela niehandlowa”) |
| `CzyDlugiWeekend` | int8 (0/1) | dzień w oknie długiego weekendu (`dlugie_weekendy`) |
| `CzyNiedzielaHandlowa` | int8 (0/1) | niedziela handlowa wg ustawy |
| `CzyRoboczy` | int8 (0/1) | kalendarzowo dzień roboczy: pn–pt i nie święto (mostek w długim weekendzie = 1) |
| `CzyZamkniety` | int8 (0/1) | dzień bez żadnego paragonu (z danych) |
| `DniDoSwieta`, `DniPoSwiecie` | int16 | `0` w dzień święta, `1–7` dni przed / po najbliższym święcie, `8` dalej niż 7 dni (dni kalendarzowe) |
| `OknoSwiateczne` | category | nazwa okna świątecznego (np. `majowka_2023`) ze słownika `okna_swiateczne`: dni okna i do 7 dni przed / po; poza oknami `brak` |

**Usunięte:** `IloscBazowa`, `Mnoznik` (zawarte w `RuchMagazynowy`); po review: `KategoriaDnia` (zastąpiona flagami 0/1) i `CzyCzerwonyDzien` (wyliczalny z flag: `CzySwieto | (DzienTygodnia == 7 & CzyNiedzielaHandlowa == 0)`).
**Zmiana nazwy:** `TowId` → `SKU`, tuż przed zapisem. Hash wyjścia sortuje po `['SKU', 'Data', 'DokId', 'Kolejnosc']`, a kolejny krok (`stany`) powinien liczyć hash wejściowy z tymi samymi kolumnami.

## Zasady ogólne

- Rekordy zerowe z `calendar` mają `DokId = -1`. Transformacje liczone z historii SKU muszą je odfiltrować (`DokId != -1`).
- `AktywnyDok = 0` zostaje w `fact_inka_final`, pomijamy go dopiero przy liczeniu stanów.
- `fact_inka_final` to CSOT na poziomie transakcji (ziarno dzienne do rozważenia później).
- Kodowanie kategorii (one-hot itp.) dopiero na etapie ML, nie w ETL.

## Flagi kalendarzowe 0/1

Wcześniej `KategoriaDnia` (jedna kolumna, jedna wartość wg priorytetu) gubiła część informacji — wskazał to Butek w review:
- święta w długim weekendzie były widoczne tylko jako `dlugi_weekend` (kategoria `swieto` miała 6 dni, a świąt jest 42),
- niedziela handlowa 30.04.2023 zniknęła w majówce (22 dni zamiast 23),
- mostek (dzień roboczy w długim weekendzie) tracił informację, że był roboczy.

Teraz cztery niezależne flagi, które mogą się nakładać: `CzySwieto`, `CzyDlugiWeekend`, `CzyNiedzielaHandlowa`, `CzyRoboczy`. Zwykłą sobotę i niedzielę rozróżnia `DzienTygodnia`.

Przykłady (majówka 2023, okno 29.04–03.05):
- 29.04 (sob) → `CzyDlugiWeekend = 1`, pozostałe 0,
- 30.04 (nd) → `CzyDlugiWeekend = 1`, `CzyNiedzielaHandlowa = 1`,
- 1.05 i 3.05 → `CzyDlugiWeekend = 1`, `CzySwieto = 1`,
- 2.05 (wt, mostek) → `CzyDlugiWeekend = 1`, `CzyRoboczy = 1`.

**Uwaga przy EDA:** przy łączeniu flag w warunki (`groupby`, filtry) wynik trzeba za każdym razem sprawdzić (asserty, liczności), żeby kolejne analizy nie definiowały typów dni na różne sposoby.

Kontrole w notebooku: niedziela handlowa zawsze wypada w niedzielę, święto nigdy nie ma `CzyRoboczy = 1`, brak `NaN` po `merge`.

## CzyZamkniety

Kalendarz (ustawa) i dane (sklep) to osobne informacje:
- „czerwony dzień” (święto ustawowe lub niedziela niehandlowa) — z kalendarza, wyliczalny z flag także dla przyszłych dat; w notebooku tylko pomocniczo (`czerwony_dzien`), bez kolumny w tabeli,
- `CzyZamkniety` — z danych: brak paragonów (`TypDok = 21`, `DokId != -1`) danego dnia. Zamknięty to nie to samo co brak ruchów: w dni zamknięte bywają PZ, ZAM, PRZEC, REM.
- Komórka `CzyZamkniety` wypisuje dni, w których `CzyZamkniety` różni się od „czerwonego dnia”, czyli sklep zachował się inaczej, niż wynika z kalendarza (np. otwarty w niedzielę niehandlową albo zamknięty w niedzielę handlową).

Przykład: 2023-04-30 i 2023-08-27 to niedziele handlowe (`CzyNiedzielaHandlowa = 1`), w które sklep był zamknięty (`CzyZamkniety = 1`) — to jedyne 2 rozbieżności w danych.

## DniDoSwieta / DniPoSwiecie

- Odległość w dniach kalendarzowych od **dnia święta** ustawowego: `DniDoSwieta` do najbliższego następnego, `DniPoSwiecie` od ostatniego. `0` tylko w dzień święta. Zielone Świątki się nie liczą (`swieta_bez_okna`).
- Wcześniej `0` miały wszystkie dni okna (np. sobota i niedziela przed Nowym Rokiem) — zmienione, bo dzień przed świętem to co innego niż samo święto. Przynależność do długiego weekendu niosą `CzyDlugiWeekend` i `OknoSwiateczne`.
- Święta kilkudniowe (Wielkanoc, Boże Narodzenie) mają `0` w każdym dniu święta; mostek między świętami (np. 2.05) ma `1` i `1`.
- Przykład (Nowy Rok 2024): 30.12 → 2 / 4 (do 1.01 / od 26.12), 31.12 → 1 / 5, 1.01 → 0 / 0, 2.01 → 4 / 1.
- Liczba zamiast 0/1, bo 0/1 łatwo wyliczyć później (np. `DniDoSwieta <= 2`), a odwrotnie się nie da.
- Dwie kolumny, bo dzień może być „po” jednym święcie i „przed” kolejnym.
- `8` zamiast `NaN` — celowo, żeby kolumna nie miała braków. Wcześniej było `999`, ale modele liniowe traktują liczbę jako odległość, więc 999 zaburzało wyniki; 8 jest tuż za zakresem 1–7, a modelom drzewiastym to obojętne.

## OknoSwiateczne

- Nazwa okna (`category`) wprost ze słownika `okna_swiateczne`: dni okna + do 7 dni przed i po; poza oknami `brak`.
- 27 okien: 22 długie weekendy + 5 pojedynczych świąt (Nowy Rok 2023 — nd, Wszystkich Świętych 2023 — śr, Niepodległości 2023 — sob, Trzech Króli 2024 — sob, Wszystkich Świętych 2025 — sob). Zielone Świątki nie mają okna (`swieta_bez_okna`).
- Zakresy wygenerowano raz regułą „najbliższe okno, remis → następne” i wpisano do słownika jako statyczne. Dni newralgiczne zmienia się w słowniku jedną datą, bez zmiany logiki. Remisy (dzień dokładnie w połowie między oknami) przypisane do następnego okna: 06.11.2023, 28.12.2023, 06.11.2024, 26.04.2025, 05.11.2025, 30.12.2025 — do przejrzenia.
- Wartości w snake_case z rokiem — filtrowanie po rodzaju (`str.startswith('majowka')`) i po roku (`str.endswith('_2024')`).
- Celowo jedna kolumna, bez osobnych nazw „poprzedniego” i „następnego” okna — więcej wzorców rozdrobniłoby grupy w EDA i dało szum modelom. Odległość do obu okien niosą `DniDoSwieta` / `DniPoSwiecie`.

## Słowniki statyczne

Cztery słowniki w kolejnych komórkach notebooka:
- `swieta_pl` — święta ustawowe 2023–2026, z nazwą w komentarzu przy każdej dacie; zgodne w 100% z biblioteką `holidays` (od 2025 Wigilia jest dniem wolnym). Do tego `swieta_bez_okna` — Zielone Świątki: zawsze w niedzielę, bez dnia wolnego w zamian i bez efektu zakupowego, więc mają `CzySwieto = 1`, ale nie tworzą okna świątecznego.
- `niedziele_handlowe` — wg ustawy, 2023 – styczeń 2026; 2023-12-10 zamiast 2023-12-24 (Wigilia w niedzielę, termin przeniesiony nowelizacją).
- `dlugie_weekendy` — 22 okna, tylko ciągi **≥ 3 dni** wolnych: święta + soboty/niedziele + mostki (pojedynczy dzień roboczy = 1 dzień urlopu). Święto w sobotę/niedzielę bez sąsiednich świąt daje najwyżej 2 dni, więc nie jest długim weekendem. Dni wolnego oddawanego przez pracodawcę za święto w sobotę nie uwzględniamy — to decyzja firmy, nie kalendarza. `nowy_rok_2025` i `nowy_rok_2026` obejmują 1–6.01 (mostki, razem z Trzema Królami).
- `okna_swiateczne` — pełne zakresy okien dla `OknoSwiateczne` (patrz wyżej).

Przy nowych danych wszystkie słowniki trzeba uzupełnić — pilnuje tego assert w walidacji (dane muszą mieścić się w 01.01.2023–31.01.2026).

## Walidacja kalendarza

Kalendarz opiera się na ręcznych słownikach i wielu decyzjach, a błąd w dacie nie wywoła wyjątku — po cichu zepsuje flagi. Dlatego wszystkie kontrole są w jednej komórce „Walidacja kalendarza”:
- **asserty**: zakres danych w zakresie słowników; brak duplikatów; niedziele handlowe tylko w niedziele i nie w święto; długie weekendy ≥ 3 dni, ze świętem, bez nakładania; okna świąteczne bez nakładania, każde z rdzeniem, każdy długi weekend w swoim oknie, każde święto (poza Zielonymi Świątkami) w jakimś oknie; flagi spójne (`CzyRoboczy` tylko pn–pt i nie w święto, `CzySwieto` = `swieta_pl`); `DniDoSwieta = 0` dokładnie w dniach okien; każdy dzień okna i długiego weekendu ma nazwę w `OknoSwiateczne`; brak `NaN` i poprawne typy,
- **wydruki do przeglądu ręcznego**: tabela okien (zakres, rdzeń, dni przed/po, święta, mostki), okna z zakresem innym niż ±7 dni oraz przełomy roku dzień po dniu (20.12–10.01).

## Usunięte z wcześniejszych wersji

- `KategoriaDnia` — zastąpiona flagami 0/1 (review PR #9),
- `CzyCzerwonyDzien` — wyliczalny z flag (review PR #9),
- `ProductLifetimeDays` — artefakt,
- angielskie duplikaty cech kalendarzowych (`day_of_week`, `year`…),
- agregacje `daily_sales`, `df_tx_sku`, `df_feat_tx`, `eda_weekly` — to etap EDA/ML.

## Do decyzji

- Okna 1–2-dniowe (np. 1.11.2023, środa) — w słowniku okien dla `DniDoSwieta` / `DniPoSwiecie`, ale nie w `dlugie_weekendy`?
- Wielka Sobota, 23.12 — w oknie czy poza nim (to mocne dni zakupowe)?
- Boże Narodzenie + Nowy Rok (+ Trzech Króli) — jedno okno czy osobne? (rozstrzygnie EDA; prawdopodobnie jedno okno świąteczno-noworoczne)
- `DniDoSwieta` / `DniPoSwiecie`: zasięg (1–3 dni czy więcej?) — do wyboru w EDA (dni otwarcia: patrz Propozycje po MVP).

## Propozycje po MVP

- `DniDoSwieta` / `DniPoSwiecie`: rozważyć liczenie w dniach otwarcia sklepu zamiast kalendarzowych (dni zamknięte — niedziele niehandlowe, święta — nie wnoszą sprzedaży, więc „2 dni przed świętem” może znaczyć różną liczbę dni zakupowych).
- Flaga stanu magazynu (brak towaru ≠ brak popytu), dni skróconego otwarcia, kanibalizacja.
- `CenaRealna` — faktyczna cena z kasy dla sprzedaży (`TypDok = 21`). Pominięta w MVP. `Zaplacono` jest per paragon, więc wymaga rozdzielenia na pozycje; ceny ujemne do zbadania; dla pozostałych ruchów `CenaPoRab`.
- `CenaPoRab` i `CenaRealna` są **netto**; cena brutto = netto × (1 + VAT).
- `select_cols`: można dodać `Stawka` (VAT z `towar` — uwaga, tylko obecna stawka, a VAT na żywność się zmieniał).
- `TowId_Master` — scalanie duplikatów SKU (przeceny: `przec` / `przecena` / `pyec`…, literówki, nowy EAN dla tego samego produktu). Baza: `NazwaTowCzysta` + fuzzy matching. Dokładnie ta sama nazwa: 93 SKU w 46 grupach, ale część to różne warianty, więc nie scalać w ciemno.

## Skąd zero sprzedaży (poza zamkniętym sklepem)

- **Brak towaru na stanie** — najczęstsza i najgroźniejsza przyczyna, bo model uczy się „nie ma popytu, zamawiaj mniej”. Do wykrycia po wyliczeniu stanów (np. stan ≤ 3 sztuk).
- **Cykl życia towaru** — dni przed pierwszą dostawą i po wycofaniu z oferty (ważne przy wierszach zerowych z `calendar`).
- **Towar w systemie, ale nie na półce** — leży na zapleczu albo nie został wyłożony.
- **Sprzedaż na innym TowId** — duplikaty, przeceny (AsId 319), zmiana EAN (dotyczy `TowId_Master`).
- **Remanent albo awaria kas** — sklep nieczynny cały dzień lub część dnia.
- **Krótsze godziny otwarcia** (Wigilia, Wielka Sobota) — nie dają zera, ale zaniżają sprzedaż.
- **Kanibalizacja** — promocja zamiennika zabiera popyt.
- **Sezonowość** (znicze, choinki) — brak popytu prawdziwy, ale przewidywalny.
