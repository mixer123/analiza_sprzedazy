# transform.ipynb — CzyPromocja

Sekcja `transform.ipynb` wykrywająca promocje z cen na pozycjach sprzedaży (`TypDok == 21`, `DokId != -1`).

## Kolumny wynikowe

| Kolumna | Typ | Opis |
|---|---|---|
| `CzyPromocja` | int8 (0/1) | dzień towaru w promocji |
| `TypPromocji` | category | `obnizka` / `multibuy` / `obnizka_multibuy` / `brak` |
| `ObnizkaPct` | float32 | głębokość obniżki (0–1); bez promocji 0 |

Flaga opisuje **dzień towaru** (SKU × Data), nie pozycję paragonu — wiersze zerowe (`DokId = -1`) w oknie promocji też mają `CzyPromocja = 1`.

## Algorytm — dwa sygnały

**Obniżka A → B** — „dolina” ceny półkowej `CenaDet`:
1. cena dnia = najczęstsza `CenaDet` w dniu (ważona ilością),
2. kolejne dni z tą samą ceną → odcinki,
3. początek doliny: odcinek z ceną niższą o ≥ 5% od poprzedniego (albo pierwszy odcinek nowego SKU),
4. koniec doliny: pierwszy odcinek, w którym cena wraca w górę o ≥ 5% względem najwyższej ceny w dolinie (dolina może obejmować kilka odcinków — promocja schodkowa),
5. odrzucane: dolina > 31 dni (zmiana ceny) i powrót do ceny sprzed spadku bez wyraźnego skoku,
6. flaga na wszystkich dniach doliny, także bez sprzedaży.

Przykład (masło Mlekovita 6255): 6,49 → 5,79 (22.03–08.04.2023) → 6,49: dolina 22.03–08.04, `ObnizkaPct` = 1 − 5,79 / 6,49 = 0,108.

**Multibuy** — rabat kasowy: pozycja z `CenaPoRab < CenaDet` („2 za…”, „1+1 za grosz”, „miksuj dowolnie”). Rabat widać tylko w dniach, gdy ktoś kupił wymaganą liczbę sztuk, więc przerwy ≤ 7 dni między dniami z rabatem też są promocją.

**`ObnizkaPct`:**
- obniżka: `1 − cena dnia ÷ cena sprzed doliny` (nowy SKU: cena po powrocie); w dniach bez sprzedaży wartość z ostatniego dnia ze sprzedażą,
- multibuy: średni rabat pozycji z rabatem `1 − CenaPoRab ÷ CenaDet`; w dniach wypełnionych średnia z dni na końcach przerwy,
- oba sygnały: większa z wartości.

## Parametry

| Parametr | Wartość | Znaczenie |
|---|---|---|
| `PROMO_PROG` | 0,05 | minimalny spadek i powrót ceny (5%) |
| `PROMO_MAX_DNI` | 31 | maksymalna długość doliny |
| `PROMO_LUKA_MULTIBUY` | 7 | przerwa między dniami z rabatem wypełniana jako promocja |

## CenaDet — „boczne wejście”

`CenaDet` (cena detaliczna z kartoteki w chwili sprzedaży) czytana bezpośrednio z `dane/raw/pozdok.parquet` po `DokId` + `Kolejnosc`. Potrzebna wyłącznie do wyliczenia flagi — **nie trafia** do `fact_inka_final`. Bez zmian w `select_cols` i `calendar`. Na paragonach `CenaDet == CenaPrzedRab` w 100%, więc `CenaPrzedRab` jest zbędna.

## Walidacja na gazetkach

**Dane:** 6 gazetek SPAR (03.2023 – 01.2026), przepisane ręcznie do `gazetki_promocje.parquet`.

**Pozycja** = jeden towar (SKU) w jednej gazetce, z okresem `DataOd`–`DataDo` — np. masło 6255 w gazetce 15–21.03.2023. Pozycji z przypisanym SKU: 344.

**`PromocjaWSklepie`** = czy cena w sklepie faktycznie spadła w okresie gazetki (sklep franczyzowy nie zawsze bierze udział w promocji):
- 1 → 298 pozycji
- 0 → 46 pozycji

Porównanie z algorytmem Butka (mediana `CenaPoRab` z 60 dni wstecz):

| Pytanie | Jak liczone | Nasz | Butek |
|---|---|---|---|
| Czy flaga znajduje promocje z gazetek? (↑) | pozycje z `PromocjaWSklepie = 1` z flagą choć w 1 dniu okresu ÷ 298 | 93,0% | 87,2% |
| Czy flaga pojawia się, gdy w sklepie promocji nie było? (↓) | pozycje z `PromocjaWSklepie = 0` z flagą choć w 1 dniu okresu ÷ 46 | 6,5% | 10,9% |
| Czy flaga obejmuje całą promocję, a nie tylko część dni? (↑) | dni sprzedaży z flagą ÷ wszystkie dni sprzedaży w okresach 344 pozycji | 83,9% | 72,9% |
| Ile flag dotyczy towarów spoza gazetki? (↓) | dni sprzedaży z flagą na SKU spoza gazetki ÷ wszystkie dni z flagą, w okresie 3 gazetek przepisanych w całości | 60,9% | 68,0% |

Ostatni wiersz to **górna granica błędu** — sklep ma też własne promocje spoza gazetek (krótka data, akcje producentów), więc część tych flag to prawdziwe promocje.

Flaga obejmuje 4,8% dni sprzedaży (Butek: 5,8%).

## Ograniczenia

- **SKU sprzedawane tylko w promocji** (wielopaki piw, produkty świąteczne) — brak ceny „przed”/„po”, nie zostaną wykryte. Dla modelu bez znaczenia: flaga byłaby w nich stała.
- **Algorytm patrzy w przyszłość** (potrzebuje powrotu ceny) — do oznaczania historii OK; przy prognozie przyszłe promocje i tak znamy z gazetek.
- **Promocje bez zmiany ceny w sklepie** (cena z gazetki = cena regularna sklepu) — z cen niewykrywalne.

## Po MVP

- Warstwa z gazetek: `CzyPromocja` = algorytm **lub** potwierdzenie z gazetki + kolumna `ZrodloPromocji`; gazetki dokładane stopniowo (ok. 26 gazetek głównych rocznie, start w środy co 2 tygodnie).
- Wielopaki: cena regularna z ceny pojedynczej sztuki × N.
- Cena odniesienia „tylko wstecz” (pomysł Butka) — jeśli flaga ma być liczona na bieżąco.
