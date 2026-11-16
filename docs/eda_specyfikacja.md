# EDA - specyfikacja techniczna i metodyka (Projekt INKA)

> **Zakres:** EDA pod algorytm deterministyczny (baseline prognozy sprzedaży). Modele ML poza zakresem na tym etapie.
> **Charakter:** projekt edukacyjny - priorytetem jest poprawna metodyka i jawne założenia, nie maksymalna dokładność.

---

# Część A - Specyfikacja techniczna

## A1. Cel

EDA dostarcza **parametry i reguły** dla baseline'u deterministycznego. Algorytm baseline'owy (w 3 podstawowych wariantach) jest zadany, EDA go nie wybiera.
Cel końcowy projektu to optymalizacja zamówień, więc prognoza dotyczy popytu w **oknie zamówienia**, a nie pojedynczego dnia.

**Warianty baseline'u** (porównywane ze sobą; kolejne algorytmy porównujemy z najlepszym):

| Wariant | Jak liczy |
|---|---|
| baseline_0 | SKU: tydzień N = średnia tygodnia N z lat poprzednich |
| baseline_1 | baseline_0 + wyrównanie Wielkanocy (C2) |
| baseline_2 | poziom bazowy SKU × mnożniki AsId (dzień tygodnia, tydzień roku, wydarzenia, promocja) |

**Wyniki EDA:**

| # | Wynik | Analiza | Co powstaje | Poziom | Dla wariantu |
|---|---|---|---|---|---|
| 1 | Podobieństwo lat | E1 | miara różnicy 2023 vs 2024 + wykres tygodniowy; czy sezonowa średnia z lat ma sens (2025 = rok testowy, nie wchodzi do EDA) | sklep, AsId | wszystkie |
| 2 | Średnia czy mediana | E1, E4 | wybór z uzasadnieniem (udział zer, skośność) | typ SKU | wszystkie |
| 3 | Okno historii N | E1 | długość okna dla średniej kroczącej (zimny start, wariant porównawczy) | SKU | 2 |
| 4 | Mnożnik dnia tygodnia | E1 | o ile dany dzień tygodnia sprzedaje więcej/mniej niż przeciętny dzień w grupie (np. Pt ×1,3, Wt ×0,8); grupy poniżej progu → profil sklepu | AsId | 2 |
| 5 | Mnożnik tygodnia roku | E1 | o ile dany tydzień roku sprzedaje więcej/mniej niż przeciętny tydzień w grupie (np. grudzień ×2,0, lipiec ×0,5); wygładzony (N−1, N, N+1), Wielkanoc wyrównana | AsId | 2 |
| 6 | Wydarzenia z potwierdzonym efektem | E2 | mnożnik każdego wydarzenia (święta, długie weekendy, okazje) per grupa + długość okna (ile dni przed / po); kryterium - efekt w obu latach 2023–2024 (do ustalenia) | AsId × wydarzenie | 1 (Wielkanoc), 2 |
| 7 | Efekt promocji | E3 | o ile więcej sprzedaje się w dniu promocji niż w zwykłym dniu (np. ×1,8); na MVP z `CzyPromocja`. Dni promocyjne nie wchodzą do wyliczania Bazy | AsId (duże SKU osobno) | 2 |
| 8 | Typy popytu SKU | E4 | każde SKU dostaje jeden z 4 typów popytu (np. kajzerka = regularny, bombonierka = nieregularny), a dla każdego typu ustalamy, jak liczyć jego prognozę (np. regularny: zwykła średnia; sporadyczny: średnia z dłuższego okresu, bo mediana dałaby 0) | SKU | wszystkie |
| 9 | Czyszczenie i zimny start | E6 | lista sytuacji psujących prognozę (nowe SKU, wycofane SKU, jednorazowe duże zakupy, korekty) i dla każdej decyzja, co z nią robimy | SKU | wszystkie |
| 10 | Ograniczenia danych | - | patrz A7 | - | - |

Harmonogram zamawiania (E5) nie jest potrzebny do baseline'u - osobne, późniejsze zadanie „proces zamówień”.

Zasady liczenia mnożników (próg wielkości grupy, wygładzanie, dni „czyste” bez okien wydarzeń i promocji): A6.

### Objaśnienia do tabeli „Wyniki EDA”

| Pkt | Termin | Co znaczy | Dziedzina / odpowiednik branżowy | Przykład |
|---|---|---|---|---|
| 2–9 | **Baza** (poziom bazowy SKU) | przeciętna sprzedaż SKU w zwykły dzień: `mean()` sprzedaży dziennej z dni „czystych” (sklep otwarty, bez promocji, poza oknami wydarzeń) w oknie życia SKU; dni z zerową sprzedażą też się liczą; okres 2023–2024 albo ostatnie N tygodni | statystyka: poziom (*level*); handel: „średnia sprzedaż” | 10 szt./dzień w zwykłe dni, 18 w promocji → Baza = 10 |
| 3 | **średnia krocząca** | średnia z ostatnich N tygodni, przesuwana co tydzień (nie suma narastająca) | statystyka (*moving average*); handel: „średnia z N tygodni” | sprzedaż 10, 12, 8, 14, 20, 10, 12, 16 → prognoza: N=1: 16, N=2: 14, N=4: 14,5, N=8: 12,75 |
| 3, 9 | **zimny start** | nowe SKU bez historii sprzedaży z lat poprzednich | ML / systemy rekomendacji (*cold start*); handel: „nowy towar / nowy indeks”, wprowadzenie nowego produktu (NPI) | towar wprowadzony w 2025 |
| 4–7 | **mnożnik** | ile razy więcej/mniej sprzedaje się w danej sytuacji niż przeciętnie (stosunek średnich, nie różnica w sztukach); liczony na grupie, stosowany do SKU; mnożniki się mnoży | statystyka: indeks sezonowy (model multiplikatywny, Holt-Winters); handel: profil sezonowy; w ML - typowa cecha (np. konkurs M5) | grupa BUŁKI: średnia w piątki 650 / średnia wszystkich dni 500 = 1,3 → kajzerka (Baza 100) w piątek: 100 × 1,3 = 130 |
| 2, 9 | **skośność** | czy rozkład sprzedaży ma długi ogon w jedną stronę; > 0 = rzadkie duże piki, średnia > mediana | statystyka; handel: brak odpowiednika (najbliżej „sprzedaż nierówna, z pikami”) | zwykle 2–3 szt./dzień, raz 40 szt. → średnia 5, mediana 3 |
| 2, 9 | **kurtoza** | jak często zdarzają się wartości skrajne (outliery); pandas `.kurt()`: ≈ 0 rozkład normalny, > 0 częste piki | statystyka; handel: brak odpowiednika | wysoka kurtoza → SKU z pikami do sprawdzenia przy czyszczeniu; mediana zamiast średniej jako Baza |
| 8 | **typy popytu** | klasyfikacja Syntetosa–Boylana po dwóch miarach: **ADI** - średni odstęp w dniach między dniami ze sprzedażą (1 = codziennie); **CV²** - jak bardzo różnią się ilości w dniach ze sprzedażą; progi ADI 1,32 i CV² 0,49 | prognozowanie popytu / statystyka; handel: „szybko / wolno rotujące”, „rotacja nieregularna” | patrz niżej |

**Typy popytu (pkt 8):**

| Typ | ADI | CV² | Co znaczy | Przykład |
|---|---|---|---|---|
| smooth (regularny) | < 1,32 | < 0,49 | prawie codziennie, podobne ilości | mleko, kajzerka |
| erratic (zmienny) | < 1,32 | ≥ 0,49 | prawie codziennie, ilości skaczą | piwo (zgrzewki w weekend) |
| intermittent (sporadyczny) | ≥ 1,32 | < 0,49 | rzadko, zwykle po 1–2 szt. | przyprawa niszowa |
| lumpy (nieregularny) | ≥ 1,32 | ≥ 0,49 | rzadko i w różnych ilościach | bombonierki |

Typ popytu ≠ `KategoriaABC`: ABC mówi o **ważności** SKU (udział w wartości sprzedaży, zł) i służy do filtrowania / grupowania; typ popytu mówi o **wzorcu sprzedaży**. Można je łączyć w macierz (np. A × lumpy).

**Czyszczenie i zimny start (pkt 9)** - przykładowe przypadki; decyzje do ustalenia w E6:

| Przypadek | Przykład | Decyzja (przykład) |
|---|---|---|
| nowe SKU bez historii (zimny start) | towar wprowadzony w 2025 | średnia z dostępnych tygodni × mnożniki grupy |
| wycofywane SKU | koniec sprzedaży, towar martwy | nie prognozujemy |
| jednorazowy duży zakup | firma kupuje 50 szt. wody | obciąć do typowego poziomu |
| ujemne ilości / korekty | zwrot na paragonie | pominąć |

## A2. Wejście

| Element | Wartość |
|---|---|
| Plik | `dane/interim/fact_inka_final.parquet`; dla E7 i E8 `dane/interim/fact_inka_final_stany.parquet` (+ `StanPoRuchu`, `StanKoniecDnia`) |
| Rozmiar | 9 485 872 wiersze, 60 kolumn, 12 481 SKU |
| Zakres dat | 2023-01-01 – 2026-01-31 (pełne lata 2023–2025 + styczeń 2026) |
| Ziarno | pozycja dokumentu (nie dzień) |
| Hash | do wyjaśnienia - hashe od kroku transform różnią się między środowiskami autorów; porównanie po ustaleniu (sortowanie `['SKU','Data','DokId','Kolejnosc']`) |

Wiersze zerowe z kroku `calendar`: `DokId = -1`, `TypDok = 21`, `IloscPlus = 0` (5 428 540 wierszy). Pozostałe ruchy (PZ, REM, BO i inne, 683 357 wierszy) są w pliku, ale nie wchodzą do popytu.

**Kolumny używane:** `SKU`, `Data`, `DokId`, `TypDok`, `IloscPlus`, `Wartosc`, `AsId`, `NazwaAsort`, `CzyWazony`, `DzienTygodnia`, `TydzienRokuISO`, `RokISO`, `Rok`, `Miesiac`, `DzienMiesiaca`, `CzyZamkniety`, `CzySwieto`, `CzyDlugiWeekend`, `CzyNiedzielaHandlowa`, `CzyRoboczy`, `DniDoSwieta`, `DniPoSwiecie`, `OknoSwiateczne`, `CzyPromocja`, `TypPromocji`, `ObnizkaPct`.

**Kroki startowe (każdy notebook EDA):**
1. hash wejściowy,
2. wczytanie tylko potrzebnych kolumn,
3. filtr `TypDok == 21`,
4. agregacja do poziomu danej analizy,
5. kontrola: suma `IloscPlus` po agregacji = suma `IloscPlus` dla `TypDok == 21` przed nią.

## A3. Definicje wspólne

Jedna definicja dla wszystkich analiz (najlepiej jedna funkcja w `utils/`), żeby żadna analiza nie liczyła popytu po swojemu.

- **Popyt dzienny** (SKU × `Data`) = Σ `IloscPlus` dla `TypDok == 21`. Dni zerowe z `calendar` dają 0.
- **Dzień otwarty:** `CzyZamkniety = 0`. Średnie popytu liczymy z dni otwartych.
- **Wykluczenia z popytu:** `AsId 319 ***PRZECENY` (odpad towarowy sprzedawany taniej - nie jest popytem na towar).
- **Jednostki:** `IloscPlus` to sztuki albo kg (`CzyWazony`). Agregaty ponad SKU (grupa, sklep) liczymy osobno dla `CzyWazony = 0 / 1` albo jako indeks względem średniej SKU - surowa suma miesza sztuki z kilogramami.
- **Okno życia SKU:** wiersze istnieją od pierwszej sprzedaży do ostatniej + 14 dni. Brak wiersza ≠ popyt zero.
- **Poziomy agregacji:** sklep, grupa (`AsId`), SKU. Czas: dzień (punkt wyjścia), tydzień (tylko do przeglądu trendu), okno zamówienia (po E5).
- **Agregacja:** sumujemy wyłącznie wielkości addytywne (`IloscPlus`, `Wartosc`). Cena dnia = `Wartosc / IloscPlus` (ważona). Nie `first()`, nie średnia arytmetyczna cen. Flagi dodajemy do kluczy `groupby`, a nie zwijamy przez `first()`.
- **Zwroty** (`TypDok` 8): marginalne, na tym etapie poza popytem.
- **Podział czasowy train/test:** wspólny dla wszystkich analiz, które coś oceniają (patrz A8).
- **Okres analiz:** EDA wzorców sprzedaży (szeregi, sezonowość, podobieństwo lat, wydarzenia, promocje, typy popytu) tylko na **2023–2024**. **2025 to rok testowy** - nie oglądamy go przed oceną algorytmów (inaczej wyciek z przyszłości). Analizy procesu (E5 - zamówienia) i ogólna jakość danych na wszystkich latach - nie dostrajają prognozy.

## A4. Analizy

| # | Analiza | Pytanie | Co policzyć | Wynik → parametr baseline'u |
|---|---|---|---|---|
| E1 | Szeregi czasowe | Jaki trend i sezonowość? | sprzedaż dzienna i tygodniowa + średnia krocząca (sklep, `AsId`); profil dnia tygodnia z dni otwartych; porównanie lat po `(RokISO, TydzienRokuISO)`; autokorelacja dla lagów 7 i 364 | N, współczynniki dnia tygodnia, poziom bazowy |
| E2 | Dni specjalne i okna świąteczne | Które wydarzenia zmieniają sprzedaż i których grup? | wskaźnik okna wydarzenia (A5) per `AsId` i rok; wpływ `OknoSwiateczne`, `DniDoSwieta`, `DniPoSwiecie` | lista wydarzeń i współczynniki |
| E3 | Promocje | Jak często i jaki efekt? Czy nakładają się na kalendarz? | udział dni z promocją per `AsId`; efekt w zwykłych tygodniach; dla każdego wydarzenia: lata z promocją i bez | czy liczyć bazę bez dni promocyjnych; współczynnik promocji |
| E4 | Charakter popytu SKU | Regularny czy sporadyczny? | udział dni zerowych (dni otwarte), ADI, CV², klasy popytu (B) | średnia vs mediana; typy SKU z osobną regułą |
| E5 | Proces zamówień | Jak często i jak długo się zamawia? | dni zamówień (`ZAM`), lead time `ZAM → PZ`, % niezrealizowanych; per grupa | horyzont i poziom agregacji prognozy |
| E6 | Jakość danych pod prognozę | Co zaburza popyt? | wartości odstające, ilości ujemne, nowe i wygasające SKU, skoki cen | reguły czyszczenia, reguła dla SKU z krótką historią |
| E7 | Braki towaru | Kiedy pusta półka udaje brak popytu? | częstość i długość stanu ≤ 3 szt. | oczyszczenie popytu |
| E8 | Obecna polityka zamawiania | Punkt odniesienia dla rekomendacji | dni zapasu, częstość braków | porównanie z baseline'em |

Zależności: E1 i E4 wymagają dziennej agregacji SKU × `Data` (liczonej w notebooku, bez zapisu do `interim`). E7 i E8 korzystają ze stanów z kroku ETL `stany.ipynb` (`fact_inka_final_stany.parquet`). Pieczywo świeże bez stanów - patrz A7.

**Kolejność:** E1 i E4 → E2 i E3 → E5 → E6 → E7 i E8 → podsumowanie (1 dzień).

## A5. Szczegóły E2 - dni specjalne

Cel: ocenić nie tylko święta i okna wokół nich, ale także **dni** wpływające na wybrane grupy (całość sprzedaży nie skoczy, pojedyncze `AsId` tak).

**Dwa rodzaje dni** (rozróżnienie po rodzaju dnia):
- **dni świąt** - święta ustawowe, długie weekendy i okna wokół nich (m.in. Wielki Piątek, Wielka Sobota, Wielkanoc, Boże Ciało, Wniebowzięcie NMP, Wszystkich Świętych, Wigilia). Opisują je `swieta_pl`, `dlugie_weekendy`, `okna_swiateczne` i kolumna `OknoSwiateczne`.
- **dni okazji** - pojedyncze dni z okazją, które nie są świętem (Dzień Kobiet, Walentynki, Mikołajki). Opisuje je słownik `dni_specjalne`.

Klasyfikacja zależy od rodzaju dnia, a nie od tego, czy w danym roku dzień wpada w okno świąteczne. Nakładanie jest normalne i rozdzielamy je w analizie (efekt dnia vs efekt okna, jak przy promocjach). W danych 2023–2025 nakładają się: Dzień Dziecka (2023, 2024), Dzień Matki (2024) i Dzień Ojca (2025) z oknem Bożego Ciała, Halloween z oknem Wszystkich Świętych (każdy rok), Sylwester z oknem Nowego Roku (każdy rok). Dzień Kobiet i Tłusty czwartek leżą poza oknami.

**Słownik `dni_specjalne`** (do weryfikacji danymi). Typ `stala` = (miesiąc, dzień). Typ `od_wielkanocy` = przesunięcie w dniach od niedzieli wielkanocnej, więc datę ruchomą liczymy z daty Wielkanocy bez ręcznych wpisów na kolejne lata.

```python
dni_specjalne = {
    # stałe daty
    'dzien_babci':              ('stala', (1, 21)),
    'dzien_dziadka':            ('stala', (1, 22)),
    'walentynki':               ('stala', (2, 14)),
    'dzien_kobiet':             ('stala', (3, 8)),
    'dzien_matki':              ('stala', (5, 26)),
    'dzien_dziecka':            ('stala', (6, 1)),
    'dzien_ojca':               ('stala', (6, 23)),
    'poczatek_roku_szkolnego':  ('stala', (9, 1)),
    'dzien_chlopaka':           ('stala', (9, 30)),
    'dzien_nauczyciela':        ('stala', (10, 14)),
    'halloween':                ('stala', (10, 31)),
    'andrzejki':                ('stala', (11, 29)),
    'mikolajki':                ('stala', (12, 6)),
    'sylwester':                ('stala', (12, 31)),
    # zależne od Wielkanocy
    'tlusty_czwartek':          ('od_wielkanocy', -52),
}
```

Poza słownikiem: Komunie (maj) i Euro 2024 (nie opisuje ich jedna reguła) oraz dni wypłat (z `DzienMiesiaca`).

**Wskaźnik okna wydarzenia:**
`W = średnia sprzedaż dzienna w oknie [−k, +m] dni od wydarzenia / średnia sprzedaż w dniach tego samego typu (ten sam dzień tygodnia, dzień otwarty) w sąsiednich tygodniach, poza oknami innych wydarzeń`

Parametry `k`, `m` wybieramy w EDA. Wynik: ranking `AsId` wg `W`, osobno dla każdego roku, żeby widać było stabilność.

**Zasada:** wydarzenia ruchome wyrównujemy po **dacie wydarzenia**, a nie po numerze tygodnia ISO. Ten sam dzień wypada w różnych tygodniach (Wielkanoc 2023: w14, 2024: w13, 2025: w16).

## A6. Zasady techniczne

- **Układ notebooka:** Opis → Importy → **[PARAMETRY]** → **[FUNKCJE]** → Wczytanie → Obliczenia → [WALIDACJA] → Zapis + hash.
  - **[PARAMETRY]** - jedna komórka zaraz pod importami: ścieżki plików, progi, zakresy dat, listy (np. wykluczone `AsId`). Z niej korzysta już wczytanie danych i hash wejściowy.
  - **[FUNKCJE]** - jedna komórka z wszystkimi funkcjami (z docstringiem).
  - W dalszych komórkach **bez** „magicznych” liczb i ścieżek wpisanych na sztywno - zmiana parametru w jednym miejscu.
- Hash wejściowy w każdym notebooku, nazwy plików i kolumn wg konwencji z README (`CamelCase` kolumny, `snake_case` pliki i zmienne, notebooki `eda_<temat>.ipynb`).
- Kontrola sumy po każdej agregacji.
- **Nie sumować** wielkości nieaddytywnych (cena, flagi, stany magazynowe).
- Sprawdzać liczność i zakres każdej flagi przed użyciem w warunkach (assert), a nie zakładać.
- **Wyciek z przyszłości:** kolumny liczone na całej historii (`KategoriaABC`, `KategoriaABCD`, `CzySezonowy`, `PrzerwaHistoryczna95pct`, `CzyMartwyNaKoniecDanych`, `AlarmMartwe`) nie służą do oceny na teście bez przeliczenia tylko na train. `PrognMartwy` i `CzyMartwyWTymDniu` - sprawdzić w kodzie, czy są liczone „na dany dzień”.
- Wyniki każdej analizy w dwóch wersjach tam, gdzie wpływa na nie nakładanie się efektów (np. z promocjami i bez).
- **Mnożniki grup - szum:** grupa poniżej progu wielkości (do ustalenia w E1) dostaje profil wyższego poziomu (AsId → nadgrupa → sklep). Mnożnik tygodnia wygładzony średnią z tygodni N−1, N, N+1.
- **Bez podwójnego liczenia:** najpierw efekty wydarzeń (E2) i promocji (E3), potem mnożniki dnia tygodnia i tygodnia roku liczone na dniach „czystych” - bez okien wydarzeń i dni promocyjnych.

## A7. Ograniczenia danych i znane uproszczenia

- **Około 3 lata historii:** wzorzec tygodniowy ma ok. 150 powtórzeń, ale pojedyncze wydarzenia roczne tylko ok. 3. Współczynniki dla nich są niepewne.
- **Nakładanie efektów:** trend, sezonowość, dni specjalne, promocje i braki towaru są w danych jednocześnie. Nie wszystko da się rozdzielić.
- **`CzyPromocja`** jest wykrywana z cen i nie jest w pełni poprawna. Używamy jej jako przybliżenia. Wersja w przeglądzie (PR #11).
- **Stany magazynowe** z kroku ETL `stany.ipynb` (reset na inwentaryzacji REM, potem ruchy), szczegóły: `docs/stany_hiu.md`. Zgodność ze stanem systemowym przy REM: 96,2% (nieważone 97,1%, ważone 65,9%). Niezgodności i ujemne stany to głównie artefakty danych - dokumenty wpisane później z wcześniejszą datą, PZ zbiorczy.
- **Pieczywo świeże:** stan na koniec dnia przyjmujemy jako 0 (niesprzedane wraca do piekarni lub idzie w straty); zamówienie = prognoza sprzedaży. Rozdzielenie świeże / paczkowane po MVP.
- **Baseline MVP nie koryguje popytu o dni z pustą półką** - popyt szybko rotujących SKU może być lekko zaniżony; korektę umożliwia E7.
- **Brak danych SPAR o zamówieniach:** harmonogram i lead time wyznaczamy z dokumentów `ZAM` i `PZ`.
- **Projekt edukacyjny:** dokładność ograniczona jakością danych, bez wdrożenia produkcyjnego.

## A8. Decyzje do podjęcia

1. Podział train/test (długość okna testowego, jeden podział czy rolling origin).
2. Poziom agregacji prognozy i horyzont (po E5; możliwe różne dla grup, np. pieczywo codziennie).
3. Szerokość okna wydarzeń `k`, `m`.
4. Czy dni promocyjne wchodzą do bazy (po E3).
5. Średnia czy mediana (po E4).
6. Reguła dla nowych i wygasających SKU (po E6).

---

# Część B - Teoria i terminy

Krótki słownik pojęć używanych w EDA i baseline'ie.

## B1. Struktura szeregu czasowego

- **Szereg czasowy** - obserwacje uporządkowane w czasie (u nas dzienna sprzedaż SKU, grupy lub sklepu).
- **Trend** - długookresowy kierunek zmian (wzrost, spadek, stabilność) w skali miesięcy i lat.
- **Sezonowość** - powtarzalny wzorzec o stałym okresie: tygodniowa (sobota vs wtorek), roczna (lody latem, znicze w listopadzie).
- **Wpływ kalendarza** - przewidywalne zdarzenia o zmiennej dacie lub układzie: święta ruchome, długie weekendy, dni specjalne, niedziele handlowe, dni zamknięte.
- **Szum** - losowe wahania, których nie tłumaczy żaden z powyższych składników.
- **Model addytywny i multiplikatywny** - składniki można dodawać (efekt stały w sztukach) albo mnożyć (efekt proporcjonalny do poziomu). W baseline'ie używamy współczynników mnożących bazę.
- **Autokorelacja (ACF)** - korelacja szeregu z nim samym przesuniętym o lag. Wysoka dla lagu 7 oznacza wzorzec tygodniowy.

## B2. Popyt i sprzedaż

- **Sprzedaż ≠ popyt.** Sprzedaż to to, co się sprzedało. Popyt to to, co klienci chcieli kupić. Przy braku towaru lub zamkniętym sklepie sprzedaż zaniża popyt (popyt „ucięty”, *censored demand*).
- **Dni zerowe** - mogą oznaczać brak popytu albo brak możliwości zakupu (zamknięcie, pusta półka). Trzeba je rozróżniać.
- **Okno życia SKU** - okres między pierwszą a ostatnią sprzedażą. Poza nim zero nie jest informacją o popycie.
- **Typy popytu (klasyfikacja Syntetosa i Boylana):**
  - **ADI** (*average demand interval*) - średni odstęp w dniach między dniami ze sprzedażą,
  - **CV²** - kwadrat współczynnika zmienności niezerowych ilości,
  - progi z literatury: ADI = 1,32 i CV² = 0,49 dzielą popyt na *smooth* (regularny), *erratic* (zmienny), *intermittent* (sporadyczny) i *lumpy* (sporadyczny i zmienny). Do zweryfikowania w źródle przed cytowaniem w raporcie.

## B3. Nakładanie się efektów

- **Zafałszowanie (*confounding*)** - dwa czynniki działają jednocześnie i nie da się przypisać efektu żadnemu z nich. Przykład: promocja w każde Walentynki.
- **Rozdzielanie efektów** - porównania w sytuacjach, gdy jeden czynnik jest obecny, a drugi nie (lata z promocją i bez, zwykłe tygodnie z promocją).
- **Wersja z i bez** - gdy rozdzielenie nie jest możliwe, pokazujemy wynik w obu wariantach i opisujemy wrażliwość.

## B4. Algorytm deterministyczny i baseline

- **Algorytm deterministyczny** - te same dane wejściowe zawsze dają ten sam wynik, bez losowości. Oparty na jawnych regułach i formułach.
- **Baseline (punkt odniesienia)** - prosta prognoza, z którą porównuje się każde bardziej złożone podejście.
- **Typowe warianty:**
  - *naive* - prognoza = ostatnia obserwacja,
  - *seasonal naive* - prognoza = ta sama wartość sprzed okresu sezonowego (np. tydzień temu),
  - *średnia / mediana z ostatnich N dni*, w tym *średnia krocząca* (*moving average*),
  - średnia z uwzględnieniem **współczynników sezonowych** (dzień tygodnia, wydarzenia, promocja).
- **Mediana vs średnia** - mediana jest odporna na pojedyncze skoki, ale przy dużym udziale zer bywa równa 0 i nic nie mówi o popycie.

## B5. Walidacja i wyciek danych

- **Walidacja czasowa** - dane dzielimy według czasu: trening wcześniej, test później, bez mieszania. Mieszanie dałoby zawyżoną dokładność.
- **Rolling origin** - wiele takich podziałów z przesuwanym punktem odcięcia.
- **Wyciek danych (*data leakage*)** - informacja z przyszłości trafia do procesu oceny. Przykład: kategoria ABC liczona na całej historii, a użyta do oceny na jej końcu.

## B6. Metryki błędu

- **MAE** - średni błąd bezwzględny, w tych samych jednostkach co sprzedaż.
- **RMSE** - pierwiastek ze średniego błędu kwadratowego, mocniej karze duże pomyłki.
- **WAPE** = Σ|y − ŷ| / Σy - błąd względny ważony wolumenem. Dobry dla SKU z dużą liczbą zer, bo nie dzieli przez pojedyncze zera.
- **Bias** = Σ(ŷ − y) / Σy - systematyczne zawyżanie (+) albo zaniżanie (−). Dla zamawiania ma znaczenie, bo niedoszacowanie i nadmiar kosztują inaczej.

## B7. Zamawianie

- **Lead time** - czas od zamówienia do dostawy (`ZAM → PZ`).
- **Okres przeglądu** - odstęp między kolejnymi zamówieniami. Horyzont prognozy to zwykle lead time + okres przeglądu.
- **Zgrzewka** - jednostka zamawiania, więc wynik prognozy trzeba zaokrąglić do opakowań.
- **Analiza ABC (Pareto)** - podział SKU wg udziału w wartości sprzedaży: A (ok. 80% wartości), B (kolejne 15%), C (reszta). Służy do segmentacji i raportowania błędu per segment.

## B8. Dane i agregacja

- **Wielkość addytywna** - taka, którą można sumować bez utraty sensu (`IloscPlus`, `Wartosc`). Cena, flagi i stany nie są addytywne.
- **Ziarno tabeli** - co oznacza jeden wiersz (u nas pozycja dokumentu). Zmiana ziarna to agregacja, więc wymaga kontroli sumy.
- **Artefakt** - słowo ma dwa znaczenia:
  - *w inżynierii danych* - trwały wytwór pracy, np. plik `.parquet` z kroku pipeline'u lub model,
  - *w analizie danych* - wynik wyglądający jak realne zjawisko, a powstały przez sposób zapisu lub liczenia (np. ujemny stan po dokumencie wpisanym z wsteczną datą).
- **Cichy błąd** (*silent bug*) - błąd bez wyjątku i ostrzeżenia, dający wiarygodnie wyglądający, ale zły wynik (np. `first()` na niespójnych flagach). Dlatego asserty i kontrola sum.

---

# Część C - Pomysły (burza mózgów)

> Robocza lista do rozważenia. Niczego tu nie przesądzamy - zbieramy pomysły i decydujemy, jak i do czego je użyć. Część A i B opisują stan bieżący, ta część jest szkicem.

## C1. Baseline

- **Sezonowa średnia z lat poprzednich** (*seasonal average*): prognoza na tydzień N roku 2026 = średnia lub mediana tygodnia N z lat 2023–2025. Założenie: lata są do siebie podobne. Wersja z jednym rokiem to *seasonal naive*.
- **Pierwszy krok EDA:** wykres tygodniowej sprzedaży całego sklepu dla trzech lat na jednej osi (numer tygodnia) i jedna liczba opisująca różnice między latami. Jeśli lata są podobne, baseline ma sens, jeśli nie, widać dlaczego.
- **Test bez 2026:** przewidzieć 2025 z lat 2023–2024 oraz styczeń 2026 (ok. 5 tygodni) z lat 2023–2025.
- **Zasięg wniosku:** podobieństwo lat sprawdzamy dla całego sklepu. Dla grup i SKU osobno, bo tam różnice między latami bywają duże (np. bombonierki).
- **Dwa warianty:** baseline_0 - dopasowanie po numerze tygodnia ISO; baseline_1 - jak baseline_0 + wyrównanie Wielkanocy (C2). Różnica = ile daje sam ten faktor.
- **Dni otwarte:** baseline tygodniowy = średnia na dzień otwarty × liczba dni otwartych w prognozowanym tygodniu (lata różnią się świętami i niedzielami handlowymi).
- **Tydzień 53:** 2026 ma 53 tygodnie ISO, lata 2023–2025 po 52 - reguła do ustalenia (np. kopia tygodnia 52).
- **Średnia vs mediana:** przy teście 2025 z 2 lat (2023–2024) mediana = średnia; wybór ma sens od 3 lat.

## C2. Święta ruchome - wyrównanie po wydarzeniu

- Wyrównujemy po wydarzeniu, a nie po numerze tygodnia. Dotyczy to wydarzeń zależnych od Wielkanocy: okna wielkanocnego, Bożego Ciała i Tłustego czwartku.
- **Tydzień wydarzenia** dostaje średnią lub medianę tygodni wydarzenia z lat poprzednich (np. Wielkanoc 2026 w tygodniu 14 ← tygodnie 14, 13, 16).
- **Zwykłe tygodnie** dostają średnią z tego samego numeru tygodnia, ale tylko z lat, w których ten tydzień nie był wydarzeniem. Alternatywa: zastąpić sąsiednimi tygodniami.
- **Test mechanizmu:** przewidzieć 2025 z 2023–2024. Wielkanoc przeskakuje z tygodnia 14 i 13 na 16, więc widać, czy wyrównanie po wydarzeniu daje mniejszy błąd niż dopasowanie po numerze tygodnia.
- **Do uzupełnienia:** słowniki okien obejmują tylko styczeń 2026, a na pełny 2026 potrzebne są okna wielkanocne i pozostałe.

## C3. Święta i dni okazji

- **Rozróżnienie po kształcie efektu:** święta mają okno dłuższe (min. 3–4 dni, do 10–12), dni okazji mają około 1 dzień plus 0–3 dni przed i nic po. Tłusty czwartek to tylko ten jeden dzień.
- **Parametry okna dla dni okazji:** dzień plus 0–3 dni przed, długość dostrajana w E2 z danych.
- **Rozbieżność z kodem:** `okna_swiateczne` ma okno jako rdzeń plus do 7 dni przed i po, czyli dłużej niż „weekend, 3 dni przed, 2 po". Przy węższym oknie zniknęłyby nakładania Dnia Dziecka i Dnia Matki z oknem Bożego Ciała (liczone z dat rdzeni, bez przeliczania słownika).
- **Granica płynna:** Dzień Matki ma efekt do 4 dni, okna świąt mają 3–5 dni rdzenia plus marginesy. Długość okna warto wyznaczyć z danych, a nie przyjąć z góry.
- **Sylwester:** dzień okazji, ale co roku leży w oknie Nowego Roku. Do decyzji, czy traktować go jako dzień okazji, czy część okna.
- **Wyszukiwanie dni okazji:** głównie w wybranych grupach `AsId`, a nie w całym sklepie. Całość sprzedaży nie skacze, ale pojedyncze grupy tak.

## C4. Nakładanie się efektów i promocje

- Kalendarz, promocje i okna działają jednocześnie. Gdzie się da, rozdzielamy je porównaniem lat z promocją i bez oraz zwykłych tygodni z promocją. Gdzie się nie da, pokazujemy wynik w wersji z i bez.
- `CzyPromocja` jest wykrywana z cen i nie jest w pełni poprawna, więc traktujemy ją jako przybliżenie.
- **Po MVP:** zebrać z sieci możliwie dużo gazetek z okresu 2023 – 01.2026 - potwierdzenie algorytmu `CzyPromocja` i ręczne uzupełnienie brakujących promocji.
- **Black Friday:** wykreślony ze słownika dni okazji. Jeśli ma jakikolwiek efekt, to raczej przez promocje.

## C5. Na później

- Komunie (maj, ruchome), Euro 2024 (jednorazowe), dni wypłat (`DzienMiesiaca`).
- Czynniki poza kalendarzem, np. pogoda dla lodów i napojów (dane zewnętrzne).
- Korekta popytu o braki towaru (E7) w baseline'ie.
