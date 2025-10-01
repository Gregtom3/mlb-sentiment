from mlb_sentiment.config import load_synapse_engine
from mlb_sentiment.utility import upload_to_azure_blob
import pandas as pd
import time
import os


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


def load_comment_data(engine):
    query = """
    SELECT COUNT(*) AS comment_count
    FROM dbo.commentsTruncated
    """
    return safe_read_sql(query, engine, columns=["comment_count"])


def load_total_games(engine):
    query = """
    SELECT COUNT(DISTINCT SUBSTRING(CAST(game_id AS VARCHAR), 4, LEN(CAST(game_id AS VARCHAR))-3)) AS total_games
    FROM dbo.games
    """
    return safe_read_sql(query, engine, columns=["total_games"])


def main():
    engine = load_synapse_engine()

    comment_data = load_comment_data(engine)
    total_games = load_total_games(engine)

    # Combine into a single row DataFrame
    summary_df = pd.DataFrame(
        {
            "total_comments": [comment_data["comment_count"].iloc[0]],
            "total_games": [total_games["total_games"].iloc[0]],
        }
    )

    # Write locally then upload
    local_path = "database_totals.parquet"
    summary_df.to_parquet(local_path, index=False)

    upload_to_azure_blob(
        file_path=local_path,
        blob_name="database_totals.parquet",
        subdirectory="activeDatabase/summary",
        remove_local=True,
    )

    print("Uploaded summary to Azure Blob Storage.")


if __name__ == "__main__":
    main()
