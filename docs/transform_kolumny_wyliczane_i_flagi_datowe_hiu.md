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
| `RokMiesiac` | tekst | `'YYYY-MM'` (tekst zamiast `Period`, wygodniejszy np. w Power BI) |
| `NazwaDnia` | category (uporządkowana) | Poniedziałek … Niedziela, ze słownika (niezależnie od locale systemu) |
| `KategoriaDnia` | category | `dlugi_weekend` / `swieto` / `niedziela_handlowa` / `niedziela` / `sobota` / `roboczy` |
| `CzyCzerwonyDzien` | int8 (0/1) | święto ustawowe lub niedziela niehandlowa (z kalendarza); dawniej `CzySwieto` |
| `CzyZamkniety` | int8 (0/1) | dzień bez żadnego paragonu (z danych) |
| `DniDoSwieta`, `DniPoSwiecie` | int16 | `0` w oknie świątecznym, `1–7` dni przed / po, `8` dalej niż 7 dni |

**Usunięte:** `IloscBazowa`, `Mnoznik` (zawarte w `RuchMagazynowy`).
**Zmiana nazwy:** `TowId` → `SKU`, tuż przed zapisem. Hash wyjścia sortuje po `['SKU', 'Data', 'DokId', 'Kolejnosc']`, a kolejny krok (`stany`) powinien liczyć hash wejściowy z tymi samymi kolumnami.

## Zasady ogólne

- Rekordy zerowe z `calendar` mają `DokId = -1`. Transformacje liczone z historii SKU muszą je odfiltrować (`DokId != -1`).
- `AktywnyDok = 0` zostaje w `fact_inka_final`, pomijamy go dopiero przy liczeniu stanów.
- `fact_inka_final` to CSOT na poziomie transakcji (ziarno dzienne do rozważenia później).
- Kodowanie kategorii (one-hot itp.) dopiero na etapie ML, nie w ETL.

## KategoriaDnia

Priorytet, pierwsza pasująca wartość:
1. `dlugi_weekend` — cały ciąg dni z okna ze słownika `dlugie_weekendy` (łącznie ze świętami w oknie),
2. `swieto` — święto ustawowe poza długim weekendem (np. środa 1.11.2023); wcześniej trafiało do `roboczy` / `sobota` / `niedziela`,
3. `niedziela_handlowa` — data w `niedziele_handlowe` (wg ustawy),
4. `niedziela` — `DzienTygodnia == 7`,
5. `sobota` — `DzienTygodnia == 6`,
6. `roboczy` — pozostałe pn–pt.

Algorytm: kalendarz dzienny `df_kalendarz` z `pd.date_range(min, max)` (działa też dla przyszłych dat) → `np.select` w kolejności priorytetu → `pd.Categorical` ze stałą listą 6 kategorii → `merge` do danych po `Data`. Kontrole: daty w `niedziele_handlowe` wypadają w niedzielę, brak `NaN` po `merge`.

## CzyCzerwonyDzien i CzyZamkniety

Kalendarz (ustawa) i dane (sklep) to osobne flagi:
- `CzyCzerwonyDzien` — z kalendarza, więc wyliczalna też dla przyszłych dat.
- `CzyZamkniety` — z danych: brak paragonów (`TypDok = 21`, `DokId != -1`) danego dnia. Zamknięty to nie to samo co brak ruchów: w dni zamknięte bywają PZ, ZAM, PRZEC, REM.
- Komórka `CzyZamkniety` wypisuje dni, w których `CzyZamkniety` różni się od `CzyCzerwonyDzien`, czyli sklep zachował się inaczej, niż wynika z kalendarza (np. otwarty w niedzielę niehandlową albo zamknięty w niedzielę handlową).

Przykłady:
- 2023-04-30, 2023-08-27 → `niedziela_handlowa` + `CzyZamkniety = 1`,
- 1.05 → `dlugi_weekend` + `CzyCzerwonyDzien = 1`; 2.05 → `dlugi_weekend` + `CzyCzerwonyDzien = 0`,
- 1.11.2023 (śr) → `swieto` + `CzyCzerwonyDzien = 1`; sob. 11.11.2023 → `dlugi_weekend` + `CzyCzerwonyDzien = 1` (okno 11–12.11).

## DniDoSwieta / DniPoSwiecie

- Okna = długie weekendy + ciągi czerwonych dni (`CzyCzerwonyDzien = 1`) zawierające święto ustawowe. Zwykła niedziela sama nie tworzy okna.
- Liczba zamiast 0/1, bo 0/1 łatwo wyliczyć później (np. `DniDoSwieta <= 2`), a odwrotnie się nie da.
- Dwie kolumny, bo dzień może być „po” jednym oknie i „przed” kolejnym.
- `8` zamiast `NaN` — celowo, żeby kolumna nie miała braków. Wcześniej było `999`, ale modele liniowe traktują liczbę jako odległość, więc 999 zaburzało wyniki; 8 jest tuż za zakresem 1–7, a modelom drzewiastym to obojętne.

## Słowniki statyczne

- `swieta_pl` — święta ustawowe 2023–2026 (zgodne z biblioteką `holidays` i danymi; od 2025 Wigilia jest dniem wolnym).
- `niedziele_handlowe` — wg ustawy, 2023 – styczeń 2026; 2023-12-10 zamiast 2023-12-24 (Wigilia w niedzielę, termin przeniesiony nowelizacją).
- `dlugie_weekendy` — 25 okien, 2023 – styczeń 2026, ustalone ręcznie: święta + soboty/niedziele + mostki (pojedynczy dzień roboczy = 1 dzień urlopu); tylko okna ≥ 3 dni i święta w sobotę.

Przy nowych danych wszystkie trzy słowniki trzeba uzupełnić. Pilnuje tego `assert` w komórce długich weekendów: gdy dane sięgają dalej niż słowniki (obecnie 31.01.2026), notebook zatrzymuje się z komunikatem.

## Usunięte z wcześniejszych wersji

- `DlugiWeekend` i `NiedzielaHandlowa` (0/1) — są w `KategoriaDnia`,
- `CzyDzienRoboczy` — pokrywa się z `KategoriaDnia`,
- `ProductLifetimeDays` — artefakt,
- angielskie duplikaty cech kalendarzowych (`day_of_week`, `year`…),
- agregacje `daily_sales`, `df_tx_sku`, `df_feat_tx`, `eda_weekly` — to etap EDA/ML.

## Do decyzji

- Okna 1–2-dniowe (np. 1.11.2023, środa) — w słowniku okien dla `DniDoSwieta` / `DniPoSwiecie`, ale nie w `dlugie_weekendy`?
- Wielka Sobota, 23.12 — w oknie czy poza nim (to mocne dni zakupowe)?
- Boże Narodzenie + Nowy Rok (+ Trzech Króli) — jedno okno czy osobne?
- `DniDoSwieta` / `DniPoSwiecie`: zasięg (1–3 dni czy więcej?), dni kalendarzowe czy tylko otwarte.

## Propozycje po MVP

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
