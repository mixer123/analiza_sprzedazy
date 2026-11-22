"""Wspólne funkcje dla notebooków EDA (kroki 01-09).

Zasady, które obowiązują we wszystkich krokach (zgodnie ze specyfikacją EDA):
- EDA używa tylko lat 2023-2024. Rok 2025 jest rokiem testowym i nie wchodzi do analizy (brak wycieku z przyszłości).
- Sprzedaż = wiersze z TypDok == 21 i DokId != -1; miara = IloscPlus (sztuki).
- Asortyment AsId 319 (towary przecenione) jest pominięty.
- "Dzień czysty" (podstawa poziomu, tzw. Baza): dzień otwarty Pn-So, poza okolicami świąt i Wielkanocy.
"""
import os
import warnings
import numpy as np
import pandas as pd
from dateutil.easter import easter

PLIK_REL = "dane/interim/fact_inka_final.parquet"
KATALOG_WYNIKOW = "dane/eda"
MIARA = "IloscPlus"
POCZATEK_EDA = pd.Timestamp("2023-01-01")          # pierwszy dzień EDA (dane mogą mieć wiersze techniczne sprzed)
KONIEC_EDA = pd.Timestamp("2024-12-31")          # ostatni dzień, który wolno oglądać w EDA
ROK_TEST = 2025
WYKLUCZ_AS = (319,)
ADI_PROG, CV2_PROG = 1.32, 0.49                   # progi Syntetosa-Boylana
MIN_TYG_TYP = 13                                  # poniżej tylu tygodni aktywności typ popytu jest niewiarygodny
OKNO_WLK = (-9, 1)                                # okno wielkanocne: od 9 dni PRZED do 1 dnia PO Wielkanocy (data minus Wielkanoc)
BLISKO_SWIETA = 3                                 # dni od święta, które wyłączają dzień z "czystych"

NIEB, POM, MOR, SZARY = "#2a78d6", "#eb6834", "#1baf7a", "#8a8a85"
DNI = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Nd"]


def wejdz_do_korzenia():
    """Przechodzi do katalogu głównego projektu (tam, gdzie jest plik z danymi)."""
    d = os.path.abspath(os.getcwd())
    while True:
        if os.path.exists(os.path.join(d, PLIK_REL)):
            os.chdir(d)
            return d
        nowy = os.path.dirname(d)
        if nowy == d:
            raise FileNotFoundError(f"Nie znaleziono {PLIK_REL} w katalogu bieżącym ani nadrzędnych")
        d = nowy


def ma_kolumne(nazwa):
    """Czy plik z danymi ma kolumnę o tej nazwie (czyta tylko nagłówek pliku)."""
    try:
        import pyarrow.parquet as pq
        return nazwa in pq.read_schema(PLIK_REL).names
    except Exception:
        try:
            pd.read_parquet(PLIK_REL, columns=[nazwa])
            return True
        except Exception:
            return False


def wczytaj_sprzedaz(dodatkowe=(), do=None):
    """Sprzedaż z lat EDA bez wykluczonych asortymentów. Kolumny: SKU, AsId, Data, IloscPlus + dodatkowe.
    `do` = ostatni dzień (domyślnie KONIEC_EDA; późniejszej daty używa tylko notebook 10, który ocenia baseline'y na roku testowym)."""
    do = KONIEC_EDA if do is None else pd.Timestamp(do)
    kol = ["SKU", "AsId", "Data", "DokId", "TypDok", MIARA, *dodatkowe]
    fa = pd.read_parquet(PLIK_REL, columns=list(dict.fromkeys(kol)))
    fa = fa[(fa["DokId"] != -1) & (fa["TypDok"] == 21)]
    fa = fa[(fa["Data"] >= POCZATEK_EDA) & (fa["Data"] <= do) & ~fa["AsId"].isin(WYKLUCZ_AS)]
    return fa.drop(columns=["DokId", "TypDok"])


def kalendarz(do=None):
    """Kalendarz dzienny od początku danych do KONIEC_EDA (flagi z pliku + święta ruchome liczone z daty).
    `do` pozwala wydłużyć kalendarz (kalendarz jest znany z góry); używa tego tylko notebook 10."""
    do = KONIEC_EDA if do is None else pd.Timestamp(do)
    kol = ["Data", "CzyZamkniety", "CzySwieto", "CzyNiedzielaHandlowa", "CzyDlugiWeekend"]
    k = pd.read_parquet(PLIK_REL, columns=kol)
    k = k[(k["Data"] >= POCZATEK_EDA) & (k["Data"] <= do)].groupby("Data").max()
    dni = pd.date_range(k.index.min(), do, freq="D"); dni.name = "Data"
    k = k.reindex(dni)
    c = pd.DataFrame(index=dni)
    c["Rok"] = dni.year
    c["DzienTyg"] = dni.dayofweek
    c["Tydzien"] = dni - pd.to_timedelta(dni.dayofweek, unit="D")          # poniedziałek tygodnia
    c["TydzienISO"] = np.asarray(dni.isocalendar().week)
    c["Zamkniety"] = k["CzyZamkniety"].fillna(1).astype(bool)
    c["Swieto"] = k["CzySwieto"].fillna(0).astype(bool)
    c["NdHandlowa"] = k["CzyNiedzielaHandlowa"].fillna(0).astype(bool)
    c["DlugiWeekend"] = k["CzyDlugiWeekend"].fillna(0).astype(bool)
    wlk = {y: pd.Timestamp(easter(y)) for y in range(dni.year.min(), dni.year.max() + 2)}
    c["DniDoWielkanocy"] = [(wlk[d.year] - d).days for d in dni]
    sw = c["Swieto"].values.astype(int)
    blisko = np.zeros(len(c), bool)
    for s in range(-BLISKO_SWIETA, BLISKO_SWIETA + 1):
        blisko |= np.roll(sw, s).astype(bool)
    c["BliskoSwieta"] = blisko
    c["OknoWielkanocne"] = (-c["DniDoWielkanocy"]).between(*OKNO_WLK)      # DniDoWielkanocy > 0 = przed Wielkanocą, więc znak odwracamy
    c["Czysty"] = (~c["Zamkniety"]) & (c["DzienTyg"] < 6) & (~c["BliskoSwieta"]) & (~c["OknoWielkanocne"])
    return c


def terminy_wydarzen(kal, lata, stale, ruchome):
    """Daty wydarzeń w podanych latach: {wydarzenie: {rok: [daty]}}.
    stale = {nazwa: (miesiąc, dzień)}, ruchome = {nazwa: dni względem Wielkanocy}; do tego długie weekendy
    (pierwszy dzień każdego bloku CzyDlugiWeekend) i niedziele handlowe (otwarte, z flagi kalendarza)."""
    ev = {}
    for nazwa, (m, d) in stale.items():
        ev[nazwa] = {r: [pd.Timestamp(r, m, d)] for r in lata}
    for nazwa, przes in ruchome.items():
        ev[nazwa] = {r: [pd.Timestamp(easter(r)) + pd.Timedelta(days=przes)] for r in lata}
    dw = kal["DlugiWeekend"].values
    start = [kal.index[i] for i in range(len(dw)) if dw[i] and (i == 0 or not dw[i - 1])]
    ev["Długi weekend"] = {r: [d for d in start if d.year == r] for r in lata}
    nd = (kal["NdHandlowa"] & ~kal["Zamkniety"] & (kal["DzienTyg"] == 6)).values
    ev["Niedziela handlowa"] = {r: [d for d in kal.index[nd] if d.year == r] for r in lata}
    return ev


def pelne_tygodnie(kal):
    """Poniedziałki pełnych tygodni (Pn-Nd) mieszczących się w EDA."""
    d0 = kal.index.min()
    pn0 = d0 + pd.Timedelta(days=(7 - d0.dayofweek) % 7)      # pierwszy poniedziałek >= pierwszy dzień danych
    ost = kal.index.max()
    pn_ost = ost - pd.Timedelta(days=ost.dayofweek)
    if ost.dayofweek < 6:
        pn_ost -= pd.Timedelta(days=7)
    return pd.date_range(pn0, pn_ost, freq="7D")


def panel_dzienny(fa, kal, poziom="AsId"):
    """Dni x jednostki (zero = brak sprzedaży; dni zamknięte też zero)."""
    return (fa.pivot_table(index="Data", columns=poziom, values=MIARA, aggfunc="sum", observed=True)
              .reindex(kal.index).fillna(0))


def panel_tygodniowy(fa, kal, poziom="SKU"):
    """Jednostki x tygodnie (poniedziałek-niedziela), tylko pełne tygodnie."""
    tyg = pelne_tygodnie(kal)
    f = fa[fa["Data"] <= tyg[-1] + pd.Timedelta(days=6)]
    pn = f["Data"] - pd.to_timedelta(f["Data"].dt.dayofweek, unit="D")
    return (f.assign(Tyg=pn).groupby([poziom, "Tyg"], observed=True)[MIARA].sum()
              .unstack("Tyg").reindex(columns=tyg).fillna(0))


def typ_popytu(tyg, adi_prog=ADI_PROG, cv2_prog=CV2_PROG, min_tyg=MIN_TYG_TYP):
    """Typ popytu każdego towaru wg Syntetosa-Boylana na danych tygodniowych (jednostki x tygodnie).
    ADI = średni odstęp (w tygodniach) między tygodniami ze sprzedażą; CV2 = (odchylenie / średnia)^2 niezerowych tygodni.
    Liczymy od tygodnia pierwszej sprzedaży (wcześniejsze zera to brak towaru w ofercie)."""
    A = tyg.values.astype(float)
    W = A.shape[1]
    ma = (A > 0).any(axis=1)
    pierwszy = np.where(ma, (A > 0).argmax(axis=1), W)
    aktywne = W - pierwszy
    ze_sprz = (A > 0).sum(axis=1)
    adi = np.where(ze_sprz > 0, aktywne / np.maximum(ze_sprz, 1), np.nan)
    nz = np.where(A > 0, A, np.nan)
    with warnings.catch_warnings(), np.errstate(all="ignore"):
        warnings.simplefilter("ignore")                      # towary bez żadnej sprzedaży dają puste wiersze
        mu, sd = np.nanmean(nz, axis=1), np.nanstd(nz, axis=1)
        cv2 = (sd / mu) ** 2
    maska = np.arange(W)[None, :] >= pierwszy[:, None]
    skos = pd.DataFrame(A).where(maska).skew(axis=1).values
    typ = np.select(
        [~ma | (aktywne < min_tyg),
         (adi < adi_prog) & (cv2 < cv2_prog), (adi < adi_prog) & (cv2 >= cv2_prog),
         (adi >= adi_prog) & (cv2 < cv2_prog)],
        ["za_malo_danych", "regularny", "zmienny", "sporadyczny"], default="nieregularny")
    return pd.DataFrame({"pierwszy_tydzien": tyg.columns[np.minimum(pierwszy, W - 1)], "tygodnie_aktywne": aktywne,
                         "tygodnie_ze_sprzedaza": ze_sprz, "ADI": adi, "CV2": cv2,
                         "udzial_zer": 1 - ze_sprz / np.maximum(aktywne, 1), "skosnosc": skos,
                         "sprzedaz": A.sum(axis=1), "typ": typ}, index=tyg.index)


def aktywne_tygodnie(tyg):
    """Maska (jednostki x tygodnie): True od tygodnia pierwszej sprzedaży."""
    A = tyg.values
    pierwszy = np.where((A > 0).any(axis=1), (A > 0).argmax(axis=1), A.shape[1])
    return np.arange(A.shape[1])[None, :] >= pierwszy[:, None]


def wape(rzecz, prog):
    rzecz, prog = np.asarray(rzecz, float), np.asarray(prog, float)
    s = np.nansum(rzecz)
    return 100 * np.nansum(np.abs(rzecz - prog)) / s if s > 0 else np.nan


def norma_dnia(panel, kal, okno_tyg=6):
    """Oczekiwana sprzedaż dnia: mediana tego samego dnia tygodnia z dni czystych w oknie +-okno_tyg tygodni.
    (Używa dni po obu stronach, więc służy tylko do opisu danych z lat EDA, nigdy jako cecha prognozy.)"""
    czysty = kal["Czysty"].reindex(panel.index)
    X = panel.where(czysty, axis=0)
    wynik = pd.DataFrame(np.nan, index=panel.index, columns=panel.columns)
    dt = kal["DzienTyg"].reindex(panel.index).values
    for d in range(6):
        idx = np.where(dt == d)[0]
        wynik.iloc[idx] = X.iloc[idx].rolling(2 * okno_tyg + 1, center=True, min_periods=4).median().values
    return wynik


def zapisz_wynik(df, nazwa, index=True):
    os.makedirs(KATALOG_WYNIKOW, exist_ok=True)
    sciezka = os.path.join(KATALOG_WYNIKOW, nazwa)
    df.to_csv(sciezka, index=index)
    print(f"Zapisano: {sciezka} ({len(df)} wierszy)")
    return sciezka


def wczytaj_wynik(nazwa, **kw):
    sciezka = os.path.join(KATALOG_WYNIKOW, nazwa)
    if not os.path.exists(sciezka):
        raise FileNotFoundError(f"Brak {sciezka}: najpierw uruchom notebook, który go tworzy")
    return pd.read_csv(sciezka, **kw)


def styl():
    """Wspólny wygląd wykresów."""
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": "#e6e6e3", "grid.linewidth": 0.8,
        "axes.axisbelow": True, "axes.titlesize": 12, "axes.titleweight": "bold",
        "axes.titlelocation": "left", "font.size": 10,
    })
