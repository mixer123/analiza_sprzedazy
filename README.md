# Analiza Sprzedaży SPAR — Projekt INKA

Projekt edukacyjny: analiza sprzedaży sklepu SPAR (franczyza) na danych z PC-Market (2023–2026).  
Cel: optymalizacja zamówień — prognoza sprzedaży i rekomendacja ilości do zamówienia.  

**Autorzy:**
- Mirosław Butajło ([@mixer123](https://github.com/mixer123))  
- Hubert Drozda ([@Hiu1975](https://github.com/Hiu1975))

<details>
<summary><h2>Projekt — struktura, konwencje, środowisko</h2></summary>

### Struktura Projektu

```
analiza_sprzedazy_w_sklepie/
├── 📁 dane/
│   ├── 📁 raw/        ← surowe pliki źródłowe
│   └── 📁 interim/    ← przetworzone pliki parquet
├── 📁 notebooks/
│   ├── 📁 etl/
│   ├── 📁 eda/
│   └── 📁 ml/
├── 📁 scripts/
│   ├── 📁 etl/
│   ├── 📁 eda/
│   └── 📁 ml/
├── 📁 utils/
├── 📁 tests/
├── 📁 docs/
├── 📄 README.md
├── 📄 .gitignore
└── 📄 .gitattributes   ← obsługa plików .parquet przez Git LFS
```

### Konwencje Nazw

#### Kod
- Kolumny DataFrame → `CamelCase`
- Pliki/foldery → `snake_case`
- Zmienne → `snake_case`
- Funkcje → `snake_case`

#### Pliki
- Notebooki ETL: `select_cols.ipynb`, `calendar.ipynb`
- Notebooki testy: `testy_<nazwa>.ipynb`
- Notebooki EDA: `eda_<temat>.ipynb`
- Skrypty pipeline: `<nazwa>.py`
- Pliki parquet: `<nazwa>.parquet`

### Sumy Kontrolne

```python
from utils.tools import hash_danych_bezpieczny
hash = hash_danych_bezpieczny("dane/interim/nazwa.parquet")          # domyślnie sortuje po TowId, Data

# fact_inka_final (po zmianie TowId → SKU):
hash = hash_danych_bezpieczny("dane/interim/fact_inka_final.parquet",
                              kolumny_sortowania=['SKU', 'Data', 'DokId', 'Kolejnosc'])
```

Hash zależy od wersji bibliotek — porównujemy wyniki tylko przy wspólnym środowisku (niżej).

### Środowisko

Wspólne wersje (konieczne do zgodnych hashy):

| Pakiet | Wersja |
|---|---|
| Python | 3.11 |
| pandas | 3.0.3 |
| numpy | 1.26.4 |
| pyarrow | 14.0.2 |

```
conda create -n inka python=3.11 -y
conda activate inka
pip install "pandas==3.0.3" "numpy==1.26.4" "pyarrow==14.0.2" "matplotlib==3.10.9" "scipy==1.17.1" jupyter ipykernel
python -m ipykernel install --user --name inka --display-name "inka (Python 3.11, pandas 3)"
```

W notebookach wybieramy kernel `inka`. Sprawdzenie w notebooku:
`import sys, pandas, numpy, pyarrow; print(sys.executable, pandas.__version__, numpy.__version__, pyarrow.__version__)`

</details>

<details>
<summary><h2>ETL — pipeline</h2></summary>

### Pipeline ETL

```
📁 dane/raw/
├── 📦 asort.parquet
├── 📦 dok.parquet
├── 📦 pozdok.parquet
└── 📦 towar.parquet
        │
        ▼
⚙️ notebooks/etl/select_cols.ipynb  ← wybór kolumn z 4 tabel źródłowych
        │
        ▼
📁 dane/interim/
├── 📦 asort_selected.parquet
├── 📦 dok_selected.parquet
├── 📦 pozdok_selected.parquet
└── 📦 towar_selected.parquet
        │
        ▼
⚙️ notebooks/etl/merge.ipynb  ← scalenie 4 tabel + doc_type_map
        │
        ▼
📁 dane/interim/
└── 📦 fact_inka.parquet
        │
        ▼
⚙️ notebooks/etl/select_asid.ipynb  ← HARD wykluczenia AsId
        │
        ▼
📁 dane/interim/
└── 📦 fact_inka_hard.parquet
        │
        ▼
⚙️ notebooks/etl/select_soft.ipynb  ← SOFT wykluczenia (SKU bez sprzedaży)
        │
        ▼
📁 dane/interim/
└── 📦 fact_inka_soft.parquet
        │
        ▼
⚙️ notebooks/etl/calendar.ipynb  ← uzupełnienie dni zerowych
        │
        ▼
📁 dane/interim/
└── 📦 fact_inka_calendar.parquet
        │
        ▼
⚙️ notebooks/etl/transform.ipynb  ← transformacje, flagi towarowe i kalendarzowe (CzyPromocja — w przygotowaniu)
        │
        ▼
📁 dane/interim/
└── 📦 fact_inka_final.parquet
```

</details>

<details>
<summary><h2>Plan prac</h2></summary>

### 1. Stany magazynowe + hurtownia danych

**Odpowiedzialny:** Hubert  **Szacunek:** 3–5 dni

#### Metoda liczenia stanów (propozycja)
- **REM i BO resetują stan** do policzonej ilości (`IloscPlus`) — spis z natury zastępuje stan; pozycje tego samego towaru w jednym remanencie **sumujemy**
- pozostałe ruchy według `MetodaLiczenia` (`IP`, `IP_IM_DELTA`) — jak `RuchMagazynowy`
- **kolejność ruchów:** `Data` → `KolejnyWDniu` (nie `DokId`)
- **filtry:** `AktywnyDok = 1`, `WplywNaStan = 1`, bez wierszy zerowych (`DokId = -1`), bez pustych REM/BO (`IP = 0` i `IM = 0`)
- **kontrola jakości:** stan wyliczony tuż przed REM vs `IloscMinus` (stan systemowy przed spisem), dla każdego dokumentu REM osobno
- baza: notebook Huberta (ma już reset, sumowanie, `KolejnyWDniu`) + struktura funkcji z wersji Butka

#### Stany w `fact_inka_final` (MVP)
Stany liczymy **raz w ETL** — EDA, algorytmy i Streamlit czytają gotowy wynik, bez przeliczania historii ruchów. Na MVP jako dwie kolumny w `fact_inka_final`:
- **`StanPoRuchu`** — stan po każdym ruchu (wierszu), narastająco w kolejności `Data` → `KolejnyWDniu` → `Kolejnosc`; szczegółowo, do analiz i weryfikacji
- **`StanKoniecDnia`** — stan na koniec dnia, powtórzony we wszystkich wierszach SKU × dzień (= ostatni `StanPoRuchu` dnia); w analizach **nie sumować**, brać `first()` / `max()`

#### Hurtownia danych (po MVP)
Model gwiazdy (Kimball): tabele faktów (`fact_inka_final`, `fact_stany` — SKU × dzień) + wymiary (`dim_towar`, `dim_kalendarz`). Na MVP zostaje jeden plik `fact_inka_final` (CSOT).

#### Zadania
| Zadanie | Czas |
|---|---|
| porządki w notebooku (funkcje, stare komórki) | 0,5–1 dnia |
| stany: `StanPoRuchu` + `StanKoniecDnia` w `fact_inka_final` | 1 dzień |
| testy, weryfikacja, analiza wyników | 1–2 dni |
| poprawki, PR, review | 0,5–1 dnia |

**Do ustalenia:** miejsce w pipeline (osobny notebook `notebooks/etl/stany.ipynb` czy część `transform`); wejście — `fact_inka_final` po merge `transform`.

---

### 2. EDA

**Szacunek:** 8–12 dni  **Uwaga:** punkty 1, 2 i 4 nie wymagają stanów — można zacząć równolegle; punkty 3 i 5 dopiero po stanach.

| # | Analiza | Co zrobić | Po co | Czas | Wymaga stanów |
|---|---|---|---|---|---|
| 1 | **Szeregi czasowe sprzedaży** | trend, sezonowość (tydzień, rok, święta), średnie i zmienność | wejście do algorytmu na średnich i cech do XGBoost | 2–3 dni | nie |
| 2 | **Proces zamówień** | dni zamówień, co i jak często, lead time ZAM → PZ, % zamówień niezrealizowanych | harmonogram i lead time do reguły zamówienia (brak danych od SPAR) | 2–3 dni | nie |
| 3 | **Braki towaru (stockouts)** | jak często i jak długo stan ≈ 0 (≤ 3 szt.) | oczyszczenie danych treningowych — pusta półka ≠ brak popytu | 1 dzień | tak |
| 4 | **Charakter popytu SKU** | regularny vs sporadyczny (odstęp między sprzedażami, zmienność ilości) | wybór metody prognozy dla typu SKU (średnia nie działa na sporadycznych) | 1 dzień | nie |
| 5 | **Obecna polityka zamawiania** | dni zapasu, częstość braków, zamrożony zapas | punkt odniesienia — porównanie naszych rekomendacji z obecnym sposobem zamawiania | 1–2 dni | tak |
| — | **Podsumowanie** | wnioski dla algorytmów | — | 1 dzień | — |

**Mniej pilne:** weryfikacja flag kalendarzowych (czy różnicują sprzedaż); ceny i promocje — przy `CzyPromocja`.

**Hipoteza do sprawdzenia przy pkt 2:** w okresach promocji sklep mógł kupować więcej towaru niż wynikało z bieżącej sprzedaży i sprzedawać go po promocji (wyższa marża). Jeśli w ogóle widoczne — raczej w kategoriach najbardziej dochodowych (alkohole). Skala prawdopodobnie niewielka.

</details>
