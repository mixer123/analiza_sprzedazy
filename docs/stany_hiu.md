# stany.ipynb — stany magazynowe

Krok ETL po `transform.ipynb`. Wejście `dane/interim/fact_inka_final.parquet`, wyjście `dane/interim/fact_inka_final_stany.parquet` (te same wiersze + 2 kolumny).

## Kolumny wynikowe

| Kolumna | Typ | Opis |
|---|---|---|
| `StanPoRuchu` | float64 | stan towaru po danym wierszu |
| `StanKoniecDnia` | float64 | stan na koniec dnia, powtórzony we wszystkich wierszach SKU × dzień — **nie sumować**, brać `first()` / `max()` |

## Metoda

1. Kolejność ruchów: `SKU` → `Data` → `KolejnyWDniu` → `Kolejnosc` (wiersz zerowy dnia ma `KolejnyWDniu = -1`, więc stoi na początku dnia).
2. Ruch = `RuchMagazynowy` z `transform` (ze znakiem). Dokumenty nieaktywne (`AktywnyDok = 0`) nie zmieniają stanu.
3. **Reset:** REM i BO (`MetodaLiczenia = 'RESET_IP'`) ustawiają stan na ilość ze spisu (`IloscPlus`). Pozycje tego samego towaru w jednym dokumencie się sumują. Pusta pozycja REM (`IloscPlus = 0` i `IloscMinus = 0`) też resetuje — spis 0 oznacza stan 0. Puste pozycje BO pomijamy: `BO/23/2` to pusty bilans otwarcia magazynu 2 (`MagId = 2`, sklep miał kiedyś dwa magazyny), który wyzerowałby stan startowy z `BO/23/1` (magazyn 1).
4. Stan = suma narastająca ruchów od ostatniego resetu. Przed pierwszym resetem towaru — od 0.

## Kontrola jakości — zgodność z REM

Stan wyliczony tuż przed remanentem porównujemy ze stanem systemowym (`IloscMinus` pozycji REM), tolerancja 0,001.

| | REM (SKU × dokument) | zgodnych |
|---|---|---|
| razem | 27 708 | 96,2% |
| nieważone | 26 918 | 97,1% |
| ważone | 790 | 65,9% |

Liczba REM obejmuje puste pozycje spisu (8 952) — w 98,8% z nich stan wyliczony przed spisem też wynosi 0. Niezależna wersja algorytmu (Butek) daje ten sam wynik: 96,2%.

Niezgodności to głównie **artefakty danych**, a nie błąd metody: dokumenty wpisane do systemu po REM, ale z wcześniejszą datą (przykład: SKU 65, PZ i ROZB z 18.02.2023 wpisane po REM z tego dnia — stan systemowy w REM jeszcze ich nie uwzględniał). Kolejność wg `DokId` zamiast daty daje gorszy wynik (67,5%), więc zostaje kolejność wg daty.

## Ujemne stany

1,64% SKU-dni ma ujemny `StanKoniecDnia` (2 850 z 12 481 SKU choć raz).
- **Przed pierwszym REM** (stan od 0): ujemne SKU-dni oczekiwane.
- **Po REM:** większość serii ujemnych trwa 1–2 dni (dokumenty wpisane później).
- **Długie serie** dotyczą głównie: pieczywa (PZ wpisywany zbiorczo z datą faktury, sprzedaż codziennie), towarów ważonych, wielopaków, pozycji „PRZECENA” i opakowań/usług.

*Artefakt danych* — wynik wyglądający jak realne zjawisko, a powstały przez sposób zapisu lub liczenia danych.

## Ograniczenia i po MVP

- **Pieczywo świeże:** stan z ruchów nie ma sensu (niesprzedane wraca do piekarni lub idzie w straty). Założenie: stan na koniec dnia = 0, zamówienie = prognoza sprzedaży. Do rozdzielenia świeże / paczkowane (`AsId` 120 CHLEBY jest mieszane).
- **Towary ważone:** zgodność 66% — do zbadania.
- Flaga „stan niewiarygodny” dla grup z długimi ujemnymi seriami.
- Flagowanie dokumentów wpisanych po REM z wcześniejszą datą.
