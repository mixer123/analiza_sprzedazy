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
