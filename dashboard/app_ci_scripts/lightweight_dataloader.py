import pandas as pd
import time


def safe_read_sql(query, engine, columns=None, retries: int = 3, backoff: float = 0.5):
    """Read SQL into a DataFrame with simple retry/backoff for transient errors."""
    attempt = 0
    while attempt < retries:
        try:
            df = pd.read_sql(query, engine)
            if columns:
                df = df[columns]
            return df
        except Exception as e:
            attempt += 1
            msg = f"Error reading SQL (attempt {attempt}/{retries}): {e}"
            print(msg)
            if attempt < retries:
                time.sleep(backoff * attempt)
            else:
                print(
                    "There was a problem loading data from the database. "
                    "This may be a transient connection issue."
                )
                return pd.DataFrame()
