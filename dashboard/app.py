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

# Selectbox shows only the label (first element), but returns the full tuple
label, selected_game_id = st.sidebar.selectbox(
    "Choose a game:", options, format_func=lambda x: x[0]  # show only label
)
team_is_home = (
    games_df.loc[games_df["game_id"] == selected_game_id, "home_team"].values[0]
    == team_acronym
)
# -------------------
# Query events & comments (cached)
# -------------------
events_df = load_events(selected_game_id, engine)
comments_df = load_comments(selected_game_id, engine)

# -------------------
# Render the data summary metrics
# -------------------
data_summary(comments_df, games_df, events_df)

# -------------------
# Render the sentiment widget
# -------------------
col0, col00 = st.columns(2)
with col0:
    render_sentiment_widget(comments_df, events_df, team_is_home, team_acronym)
