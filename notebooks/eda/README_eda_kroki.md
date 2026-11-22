# EDA w krokach: jeden notebook na jeden wynik

Każdy notebook odpowiada jednemu wierszowi tabeli „EDA: wyniki, które mają powstać”. Wspólny kod (wczytanie danych, kalendarz, typy popytu) jest w `eda_wspolne.py`, więc notebooki są krótkie i nie powtarzają się.

## Kolejność i zależności
| Krok | Notebook | Wynik | Zapisuje do `dane/eda/` | Wymaga wcześniej |
|---|---|---|---|---|
| 1 | `01_podobienstwo_lat.ipynb` | Podobieństwo lat | `wynik_01_podobienstwo_lat.csv` | nic |
| 2 | `02_srednia_czy_mediana.ipynb` | Średnia czy mediana | `wynik_02_srednia_mediana.csv` | nic |
| 3 | `03_okno_historii_N.ipynb` | Okno historii N | `wynik_03_okno_N.csv`, `wynik_03_N_wg_typu.csv` | nic |
| 4 | `04_mnoznik_dnia_tygodnia.ipynb` | Mnożnik dnia tygodnia | `wynik_04_mnoznik_dnia_tygodnia.csv` | nic |
| 5 | `05_mnoznik_tygodnia_roku.ipynb` | Mnożnik tygodnia roku (z Wielkanocą) | `wynik_05_mnoznik_tygodnia_roku.csv`, `wynik_05_wielkanoc_tygodnie.csv` | krok 4 |
| 6 | `06_wydarzenia.ipynb` | Wydarzenia z potwierdzonym efektem | `wynik_06_wydarzenia.csv`, `wynik_06_okna.csv` | nic |
| 7 | `07_promocje.ipynb` | Efekt promocji | `wynik_07_promocje_asid.csv`, `wynik_07_promocje_sku.csv` | krok 4, kolumna `CzyPromocja` |
| 8 | `08_typy_popytu.ipynb` | Typy popytu SKU | `wynik_08_typy_popytu.csv`, `wynik_08_reguly.csv` | nic |
| 9 | `09_czyszczenie_zimny_start.ipynb` | Czyszczenie i zimny start | `wynik_09_decyzje.csv`, `wynik_09_flagi_sku.csv`, `wynik_09_jednorazowe.csv` | nic |

Kroki 1-4, 6, 8 i 9 są niezależne. Krok 5 czyta wynik kroku 4, a krok 7 czyta wynik kroku 4 i wymaga kolumny `CzyPromocja` w `fact_inka_final.parquet` (bez niej zatrzymuje się z komunikatem).

## Jak uruchomić
1. Skopiuj katalog `notebooks/eda/` do projektu (obok `dane/`).
2. Otwórz notebook (kernel `analiza_sprzedazy_env`) i uruchom od góry do dołu. Pierwsza komórka sama znajduje katalog główny projektu.
3. Wyniki trafiają do `dane/eda/`.

## Zasady wspólne (zgodne ze specyfikacją)
- EDA używa wyłącznie lat **2023-2024**. Rok 2025 jest rokiem testowym i nie wchodzi do analizy (moduł obcina dane do 31.12.2024).
- Sprzedaż = `TypDok == 21` i `DokId != -1`; miara = `IloscPlus`.
- Asortyment `AsId 319` (towary przecenione) jest pominięty.
- **Dzień czysty**: otwarty Pn-So, poza okolicami świąt (±3 dni) i oknem wielkanocnym (od −9 do +1 dnia). Z dni czystych liczymy Bazę i mnożniki.
- Wiersze z `CzyPromocja == 1` są wyłączone z mnożników dnia tygodnia, tygodnia roku i wydarzeń.

## Przyjęte założenia (do przejrzenia)
- Typy popytu liczone na danych **tygodniowych**, z progami ADI 1,32 i CV² 0,49.
- Wydarzenie jest „potwierdzone”, gdy w obu latach efekt ma ten sam kierunek i przekracza 90. percentyl szumu dnia zwyczajnego.
- Wybór reguły prognozy dla typu: najmniejszy WAPE przy obciążeniu w granicach ±30 %. Samego WAPE nie używamy, bo przy rzadkim popycie nagradza prognozy zaniżone.
- `CzyPromocja` jest wyliczana z cen, więc jest przybliżona; promocja bez sprzedaży jest niewidoczna.
