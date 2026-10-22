# Funkcje pomocnicze projektu. Import w notebookach: import utils.tools as tools
import pandas as pd
import numpy as np
import hashlib
import re
# Suma kontrolna (hash) danych w pliku Parquet, z uwzględnieniem sortowania po kolumnach TowId i Data.
def hash_danych_bezpieczny(sciezka_parquet, kolumny_sortowania=['TowId', 'Data']):
    df = pd.read_parquet(sciezka_parquet)
    df = df.sort_values(kolumny_sortowania).reset_index(drop=True)
    return hashlib.sha256(
        pd.util.hash_pandas_object(df, index=False).values.tobytes()
    ).hexdigest()


# Nazwa dnia tygodnia z DzienTygodnia (1 = pn … 7 = nd) — do wykresów i tabel w EDA.
# Kolumna NazwaDnia nie jest trzymana w fact_inka_final (redundancja z DzienTygodnia).
# Zwraca kategorię uporządkowaną pn → nd, niezależną od ustawień językowych systemu.
# Użycie: df['NazwaDnia'] = tools.nazwa_dnia(df['DzienTygodnia'])
NAZWY_DNI = {1: 'Poniedziałek', 2: 'Wtorek', 3: 'Środa', 4: 'Czwartek',
             5: 'Piątek', 6: 'Sobota', 7: 'Niedziela'}

def nazwa_dnia(dzien_tygodnia):
    return pd.Categorical(dzien_tygodnia.map(NAZWY_DNI),
                          categories=list(NAZWY_DNI.values()), ordered=True)


# Rok i miesiąc 'YYYY-MM' z kolumny Data — do wykresów i tabel w EDA.
# Kolumna RokMiesiac nie jest trzymana w fact_inka_final (redundancja z Data / Rok + Miesiac).
# Do samego grupowania miesięcznego wystarczy: df.groupby(df['Data'].dt.to_period('M')).
# Użycie: df['RokMiesiac'] = tools.rok_miesiac(df['Data'])
def rok_miesiac(data):
    return data.dt.strftime('%Y-%m')
