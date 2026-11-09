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
3. **Reset:** REM i BO (`MetodaLiczenia = 'RESET_IP'`) ustawiają stan na ilość ze spisu (`IloscPlus`). Pozycje tego samego towaru w jednym dokumencie się sumują. Puste pozycje spisu (`IloscPlus = 0` i `IloscMinus = 0`) nie resetują.
4. Stan = suma narastająca ruchów od ostatniego resetu. Przed pierwszym resetem towaru — od 0.

## Kontrola jakości — zgodność z REM

Stan wyliczony tuż przed remanentem porównujemy ze stanem systemowym (`IloscMinus` pozycji REM), tolerancja 0,001.

| | REM (SKU × dokument) | zgodnych |
|---|---|---|
| razem | 18 756 | 95,1% |
| nieważone | 18 066 | 96,4% |
| ważone | 690 | 61,0% |

Niezgodności to głównie **artefakty danych**, a nie błąd metody: dokumenty wpisane do systemu po REM, ale z wcześniejszą datą (przykład: SKU 65, PZ i ROZB z 18.02.2023 wpisane po REM z tego dnia — stan systemowy w REM jeszcze ich nie uwzględniał). Kolejność wg `DokId` zamiast daty daje gorszy wynik (67,5%), więc zostaje kolejność wg daty.

## Ujemne stany

1,58% SKU-dni ma ujemny `StanKoniecDnia`.
- **Przed pierwszym REM** (stan od 0): 6,4% SKU-dni ujemnych — oczekiwane.
- **Po REM:** 1,46% SKU-dni; 42% serii ujemnych trwa 1–2 dni (dokumenty wpisane później).
- **Długie serie** dotyczą głównie: pieczywa (PZ wpisywany zbiorczo z datą faktury, sprzedaż codziennie), towarów ważonych, wielopaków, pozycji „PRZECENA” i opakowań/usług.

*Artefakt danych* — wynik wyglądający jak realne zjawisko, a powstały przez sposób zapisu lub liczenia danych.

## Ograniczenia i po MVP

- **Pieczywo świeże:** stan z ruchów nie ma sensu (niesprzedane wraca do piekarni lub idzie w straty). Założenie: stan na koniec dnia = 0, zamówienie = prognoza sprzedaży. Do rozdzielenia świeże / paczkowane (`AsId` 120 CHLEBY jest mieszane).
- **Towary ważone:** zgodność 61% — do zbadania.
- Flaga „stan niewiarygodny” dla grup z długimi ujemnymi seriami.
- Flagowanie dokumentów wpisanych po REM z wcześniejszą datą.
