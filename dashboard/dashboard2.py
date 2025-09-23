import streamlit as st
import pandas as pd
from mlb_sentiment.config import load_synapse_engine
import numpy as np
from utility import safe_read_sql

st.title("MLB Game Score Dashboard")

# -------------------
# Step 1: Pick a date
# Default: 09/14/2025
# -------------------
game_date = st.sidebar.date_input(
    "Select a game date", value=pd.to_datetime("2025-09-14")
)

# Query games for that date
query_games = f"""
SELECT game_id, home_team, away_team, game_date, home_score, away_score
FROM dbo.games
WHERE CAST(game_date AS DATE) = '{game_date}'
"""

engine = load_synapse_engine()
games_df = safe_read_sql(
    query_games,
    engine,
    columns=[
        "game_id",
        "home_team",
        "away_team",
        "game_date",
        "home_score",
        "away_score",
    ],
)

if games_df.empty:
    st.warning("No games found for this date.")
    st.stop()

# -------------------
# Step 2: Pick a game
# -------------------
game_choice = st.sidebar.selectbox(
    "Choose a game:",
    games_df.apply(
        lambda r: f"{r['away_team']} @ {r['home_team']} (ID {r['game_id']})", axis=1
    ),
)

# Extract selected game_id
selected_game_id = int(game_choice.split("ID")[-1].strip(" )"))

# -------------------
# Query events
# (est) is Eastern Standard Time ex: 2025-09-14 13:41:06
# -------------------
query_events = f"""
SELECT event_id, home_score, away_score, est
FROM dbo.gameEvents
WHERE game_id = {selected_game_id}
ORDER BY event_id
"""
events_df = safe_read_sql(
    query_events, engine, columns=["event_id", "home_score", "away_score", "est"]
)

# -------------------
# Query comments
# -------------------
query_comments = f"""
SELECT game_id,author,text,created_est,sentiment_score
FROM dbo.comments
WHERE game_id = {selected_game_id}
ORDER BY created_est
"""
comments_df = safe_read_sql(
    query_comments,
    engine,
    columns=["game_id", "author", "text", "created_est", "sentiment_score"],
)

# -------------------
# Plot scores
# x = EST time
# y = home_score - away_score
# -------------------
if not events_df.empty:
    events_df["score_diff"] = events_df["home_score"] - events_df["away_score"]
    events_df["est"] = pd.to_datetime(events_df["est"])
    st.line_chart(data=events_df, x="est", y="score_diff", height=400)
    st.subheader("Game Events Data")
else:
    st.info("No events found for this game.")

# -------------------
# Plot sentiment moving average
# -------------------
if not comments_df.empty:
    # Make sure timestamp is datetime
    comments_df["created_est"] = pd.to_datetime(comments_df["created_est"])

    # Resample into 30-second bins, compute mean sentiment
    sentiment_ts = (
        comments_df.set_index("created_est")
        .resample("2Min")["sentiment_score"]
        .mean()
        .reset_index()
    )

    # Optional: rolling average smoothing (if bins are sparse)
    sentiment_ts["sentiment_smooth"] = (
        sentiment_ts["sentiment_score"]
        .rolling(window=3, min_periods=1, center=True)
        .mean()
    )

    st.subheader("Fan Sentiment (2Min bins)")
    st.line_chart(data=sentiment_ts, x="created_est", y="sentiment_smooth", height=400)
else:
    st.info("No comments found for this game.")
