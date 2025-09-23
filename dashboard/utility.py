import pandas as pd


def safe_read_sql(query, engine, columns):
    try:
        df = pd.read_sql(query, engine)
    except Exception:
        df = pd.DataFrame(columns=columns)
    return df
