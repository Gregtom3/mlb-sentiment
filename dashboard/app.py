# Standard library
from datetime import datetime, timedelta

# Third-party packages
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from streamlit_date_picker import date_picker, PickerType
from streamlit_plotly_events import plotly_events
from pytz import timezone
import pytz

# Local modules
from compute import compute_sentiment_ts
from dataloader import get_engine, load_comments, load_events, load_games
from mlb_sentiment.info import (
    get_all_team_acronyms,
    get_team_acronym_from_game_id,
    get_all_team_names,
)
from mlb_sentiment.info import get_team_acronym_from_team_name
from widgets.data_summary import data_summary
from widgets.sentiment_chart import render_sentiment_widget
from widgets.avg_sentiment_chart import render_avg_sentiment_by_game_widget

st.markdown(
    """
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
    <style>
    * { font-family: 'Poppins', sans-serif; }
    </style>
    """,
    unsafe_allow_html=True,
)
# Initialize engine
# -------------------
engine = get_engine()

# Streamlit page config
# -------------------
st.set_page_config(layout="wide")

# Centered title
# -------------------
st.title("MLB Pulse Dashboard")

# Pick a team
# -------------------
team_name = st.sidebar.selectbox("Select Team", options=get_all_team_names(), index=18)
team_acronym = get_team_acronym_from_team_name(team_name)

# Pick a date range
# Default to yesterday and today
# -------------------
game_dates = st.sidebar.date_input(
    "Select a range of dates",
    # Value will use datetime to get yesterday and today
    value=(
        datetime.today().date() - timedelta(days=1),  # yesterday
        datetime.today().date() - timedelta(days=1),  # yesterday
    ),
)

# Update cached queries to use imported functions
games_df = load_games(game_dates, team_acronym, engine)

if games_df.empty:
    st.warning("No games found for this date.")
    st.stop()


# -------------------
# Step 2: Pick a game
# -------------------
def convert_time(dt_est):
    """Convert EST to HH:MM format string."""
    if pd.isna(dt_est):
        return "TBD"
    return dt_est.strftime("%I:%M %p")


options = [
    (
        f"{r['away_team']} @ {r['home_team']} {convert_time(r.game_start_time_est)} {r.game_date}",
        r["game_id"],
    )
    for _, r in games_df.iterrows()
]

options = sorted(options, key=lambda x: -x[1])

if "selected_game_id" not in st.session_state:
    st.session_state["selected_game_id"] = options[0][1]  # default to first game

# Find the index of the currently selected game_id in options
current_index = next(
    (
        i
        for i, (_, gid) in enumerate(options)
        if gid == st.session_state["selected_game_id"]
    ),
    0,
)

# Sidebar selectbox, bound to session_state
selected_option = st.sidebar.selectbox(
    "Choose a game:",
    options,
    index=current_index,
    format_func=lambda x: x[0],
    key="game_selector",  # <--- give it its own key
)

# Update session_state when dropdown changes
label, selected_game_id = selected_option
st.session_state["selected_game_id"] = selected_game_id


team_id = int(str(selected_game_id)[:3])
team_is_home = (
    games_df.loc[games_df["game_id"] == selected_game_id, "home_team"].values[0]
    == team_acronym
)
# -------------------
# Query events & comments (cached)
# -------------------
events_df = load_events(team_id, engine)
comments_df = load_comments(team_id, engine)
# Ensure events_df and comments_df have game_id column values that are in games_df
events_df = events_df[events_df["game_id"].isin(games_df["game_id"].values)]
comments_df = comments_df[comments_df["game_id"].isin(games_df["game_id"].values)]

# -------------------
# Render the data summary metrics
# -------------------
data_summary(comments_df, games_df, events_df, team_acronym)

# -------------------
# Render the sentiment widget
# -------------------
game_specific_events_df = events_df[events_df["game_id"] == selected_game_id]
game_specific_comments_df = comments_df[comments_df["game_id"] == selected_game_id]
row1_col1, row1_col2 = st.columns(2)
with row1_col1:
    clicked_game_id = render_avg_sentiment_by_game_widget(
        comments_df, games_df, selected_game_id
    )
    if clicked_game_id is not None:
        st.session_state["selected_game_id"] = int(clicked_game_id)
        st.rerun()


with row1_col2:
    render_sentiment_widget(
        game_specific_comments_df, game_specific_events_df, team_is_home, team_acronym
    )
