import pandas as pd
from mlb_sentiment.config import load_synapse_engine
import streamlit as st
import time


def safe_read_sql(query, engine, columns=None, retries: int = 3, backoff: float = 0.5):
    """Read SQL into a DataFrame with simple retry/backoff for transient errors.

    On final failure returns an empty DataFrame and logs a Streamlit warning so
    the UI can hint at transient connectivity issues.
    """
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
            # Print for local logs and surface a non-intrusive Streamlit warning
            print(msg)
            if attempt < retries:
                time.sleep(backoff * attempt)
            else:
                st.warning(
                    "There was a problem loading data from the database. "
                    "This may be a transient connection issue — try reloading the page."
                )
                return pd.DataFrame()


# -------------------
# Load engine
# -------------------
@st.cache_resource
def get_engine():
    return load_synapse_engine()


# -------------------
# Cached queries
# -------------------
@st.cache_data
def load_games(game_date, _engine):
    query = f"""
    SELECT game_id, home_team, away_team, game_date, home_score, away_score
    FROM dbo.games
    WHERE CAST(game_date AS DATE) = '{game_date}'
    """
    return safe_read_sql(
        query,
        _engine,
        columns=[
            "game_id",
            "home_team",
            "away_team",
            "game_date",
            "home_score",
            "away_score",
        ],
    )


@st.cache_data
def load_events(game_id, _engine):
    query = f"""
    SELECT event_id, event, description, home_score, away_score, est
    FROM dbo.gameEvents
    WHERE game_id = {game_id}
    ORDER BY event_id
    """
    return safe_read_sql(
        query,
        _engine,
        columns=["event_id", "event", "description", "home_score", "away_score", "est"],
    )


@st.cache_data
def load_comments(game_id, _engine):
    query = f"""
    SELECT game_id,author,text,created_est,sentiment_score
    FROM dbo.comments
    WHERE game_id = {game_id}
    ORDER BY created_est
    """
    df = safe_read_sql(
        query,
        _engine,
        columns=["game_id", "author", "text", "created_est", "sentiment_score"],
    )
    if not df.empty:
        df["created_est"] = pd.to_datetime(df["created_est"])
    if len(df) > 2:
        df = df.iloc[:-2]  # drop last two rows (usually later stickied comments)
    return df


@st.cache_data
def compute_sentiment_ts(comments_df):
    if comments_df.empty:
        return pd.DataFrame()
    sentiment_ts = (
        comments_df.set_index("created_est")
        .resample("2Min")["sentiment_score"]
        .mean()
        .reset_index()
    )
    sentiment_ts["sentiment_smooth"] = (
        sentiment_ts["sentiment_score"]
        .rolling(window=3, min_periods=1, center=True)
        .mean()
    )
    return sentiment_ts
