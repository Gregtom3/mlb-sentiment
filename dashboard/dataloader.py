import pandas as pd
from mlb_sentiment.config import load_synapse_engine
import streamlit as st


def safe_read_sql(query, engine, columns=None):
    try:
        df = pd.read_sql(query, engine)
        if columns:
            df = df[columns]
        return df
    except Exception as e:
        print(f"Error reading SQL: {e}")
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
    SELECT event_id, home_score, away_score, est
    FROM dbo.gameEvents
    WHERE game_id = {game_id}
    ORDER BY event_id
    """
    return safe_read_sql(
        query, _engine, columns=["event_id", "home_score", "away_score", "est"]
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
