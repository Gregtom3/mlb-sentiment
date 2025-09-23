import streamlit as st
import pandas as pd
import pyodbc
from mlb_sentiment.config import load_synapse_connection

st.title("MLB Game Score Dashboard")

# -------------------
# Step 1: Pick a date
# -------------------
game_date = st.sidebar.date_input("Select a game date")

# Query games for that date
query_games = f"""
SELECT game_id, home_team, away_team, game_date, home_score, away_score
FROM dbo.games
WHERE CAST(game_date AS DATE) = '{game_date}'
"""
with load_synapse_connection() as conn:
    games_df = pd.read_sql(query_games, conn)

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
# Step 3: Query events
# -------------------
query_events = f"""
SELECT event_id, home_score, away_score
FROM dbo.gameEvents
WHERE game_id = {selected_game_id}
ORDER BY event_id
"""
with load_synapse_connection() as conn:
    events_df = pd.read_sql(query_events, conn)

# -------------------
# Step 4: Plot scores
# -------------------
if not events_df.empty:
    st.line_chart(events_df.set_index("event_id")[["home_score", "away_score"]])
    st.dataframe(events_df)
else:
    st.info("No events found for this game.")
