# Analiza Sprzedaży SPAR — Projekt INKA

## Struktura Projektu

```
analiza_sprzedazy/
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
└── 📄 .gitignore
```

## Pipeline ETL

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
⚙️ notebooks/etl/transform.ipynb  ← transformacje i kolumny flagowe
        │
        ▼
📁 dane/interim/
└── 📦 fact_inka_final.parquet
```

## Konwencje Nazw

### Kod
- Kolumny DataFrame → `CamelCase`
- Pliki/foldery → `snake_case`
- Zmienne → `snake_case`
- Funkcje → `snake_case`

### Pliki
- Notebooki ETL: `select_cols.ipynb`, `calendar.ipynb`
- Notebooki testy: `testy_<nazwa>.ipynb`
- Notebooki EDA: `eda_<temat>.ipynb`
- Skrypty pipeline: `<nazwa>.py`
- Pliki parquet: `<nazwa>.parquet`

## Sumy Kontrolne

```python
from utils.tools import hash_danych_bezpieczny
hash = hash_danych_bezpieczny("dane/interim/nazwa.parquet")
```

## Autorzy

- Mirosław Butajło ([@mixer123](https://github.com/mixer123))
- Hubert Drozda ([@Hiu1975](https://github.com/Hiu1975))