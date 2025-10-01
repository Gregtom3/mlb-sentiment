import pandas as pd
from mlb_sentiment.config import load_synapse_engine
from mlb_sentiment.info import get_team_info
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
# Test load comments
# -------------------
# @st.cache_data
def test_load_comments(team_acronym, _engine):
    query = f"""
    SELECT game_id, team
    FROM dbo.commentsTruncated_{team_acronym}
    """
    df = safe_read_sql(
        query,
        _engine,
        columns=[
            "game_id",
        ],
    )
    return df


# -------------------
# Cached all comments count
# -------------------
@st.cache_data
def get_total_comments(_engine):
    """Return the total number of rows in dbo.comments."""
    query = "SELECT total_comments FROM dbo.totals;"
    df = safe_read_sql(query, _engine, columns=["total_comments"])
    if df.empty:
        return 0
    return int(df.iloc[0]["total_comments"])


# -------------------
# Cached all games count
# -------------------
@st.cache_data
def get_total_games(_engine):
    """Return the row count of dbo.games where the game_id (apart from the first three characters) is unique."""
    query = """
    SELECT total_games
    FROM dbo.totals;
    """
    df = safe_read_sql(query, _engine, columns=["total_games"])
    if df.empty:
        return 0
    return int(df.iloc[0]["total_games"])


# -------------------
# Cached queries
# -------------------
@st.cache_data
def load_games(game_dates, team_acronym, _engine):
    # old: WHERE SUBSTRING(CAST(game_id AS VARCHAR), 1, 3) = '{team_acronym}'
    game_id_first_three = get_team_info(team_acronym, "id")
    query = f"""
    SELECT game_id, game_start_time_est, home_team, away_team, game_date, home_score, away_score, wins, losses
    FROM dbo.games_{team_acronym}
    WHERE CAST(game_date AS DATE) BETWEEN '{game_dates[0]}' AND '{game_dates[-1]}'
    """
    games = safe_read_sql(
        query,
        _engine,
        columns=[
            "game_id",
            "game_start_time_est",
            "home_team",
            "away_team",
            "game_date",
            "home_score",
            "away_score",
            "wins",
            "losses",
        ],
    )
    return games


@st.cache_data
def load_events(team_acronym, _engine):
    # old: WHERE SUBSTRING(CAST(game_id AS VARCHAR), 1, 3) = '{team_id}'
    query = f"""
    SELECT game_id, event_id, event, description, inning, halfInning, home_team, visiting_team, home_score, away_score, est, team
    FROM dbo.gameEvents_{team_acronym}
    ORDER BY event_id
    """
    df = safe_read_sql(
        query,
        _engine,
        columns=[
            "game_id",
            "event_id",
            "event",
            "description",
            "inning",
            "halfInning",
            "home_team",
            "visiting_team",
            "home_score",
            "away_score",
            "est",
        ],
    )
    # rename visiting_team to away_team for consistency
    df = df.rename(columns={"visiting_team": "away_team"})
    # Rename half innings to "Top" and "Bottom"
    df["halfInning"] = df["halfInning"].replace({"top": "Top", "bottom": "Bottom"})
    df["halfInning"] = df["halfInning"] + " " + df["inning"].astype(str)
    df["game_id"] = df["game_id"].astype(int)
    return df


@st.cache_data
def load_comments(team_acronym, _engine):
    # Use commentsTruncated which trims comments within game window
    # -5 minutes before game start to +8 minutes after game end
    query = f"""
    SELECT game_id,author,text,created_est,sentiment,sentiment_score,team
    FROM dbo.commentsTruncated_{team_acronym}
    ORDER BY created_est
    """
    df = safe_read_sql(
        query,
        _engine,
        columns=[
            "game_id",
            "author",
            "text",
            "created_est",
            "sentiment",
            "sentiment_score",
        ],
    )
    if not df.empty:
        df["created_est"] = pd.to_datetime(df["created_est"])
    # If sentiment is neutral set score to 0.0
    df.loc[df["sentiment"] == "neutral", "sentiment_score"] = 0.0
    # If sentiment is negative force score to negative value
    df.loc[df["sentiment"] == "negative", "sentiment_score"] = -df.loc[
        df["sentiment"] == "negative", "sentiment_score"
    ].abs()
    df["game_id"] = df["game_id"].astype(int)
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
