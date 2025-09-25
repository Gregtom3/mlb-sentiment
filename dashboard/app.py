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
from widgets.game_events import render_game_events_widget
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

# Pick a timezone
# -------------------
selected_timezone = st.sidebar.radio(
    "Select Timezone",
    ["EST", "CST", "MST", "PST"],
    index=0,  # Default to EST
    horizontal=True,
)


# Pick a team
# -------------------
team_name = st.sidebar.selectbox(
    "Select Team",
    options=get_all_team_names(),
    index=18,
)
team_acronym = get_team_acronym_from_team_name(team_name)

# Pick a date range
# Default to yesterday and today
# -------------------
game_dates = st.sidebar.date_input(
    "Select a range of dates",
    # Value will use datetime to get yesterday and today
    value=(
        datetime.today().date() - timedelta(days=1),  # yesterday
        datetime.today().date(),  # today
    ),
)

# Map user-friendly timezone names to pytz timezone strings
timezone_mapping = {
    "EST": "America/New_York",
    "CST": "America/Chicago",
    "MST": "America/Denver",
    "PST": "America/Los_Angeles",
}

# Update cached queries to use imported functions
games_df = load_games(game_dates, team_acronym, engine)

if games_df.empty:
    st.warning("No games found for this date.")
    st.stop()


# -------------------
# Step 2: Pick a game
# Include game number (1 or 2) depending on doubleheader
# -------------------
def convert_to_timezone(time_obj, target_timezone):
    utc_time = datetime.combine(datetime.today(), time_obj).replace(tzinfo=pytz.utc)
    target_time = utc_time.astimezone(timezone(timezone_mapping[target_timezone]))
    return target_time.strftime("%-I:%M %p")


options = [
    (
        f"{r['away_team']} @ {r['home_team']} {convert_to_timezone(r.game_start_time_est, selected_timezone)} (Game {r.name+1})",
        r["game_id"],
    )
    for _, r in games_df.iterrows()
]

# Selectbox shows only the label (first element), but returns the full tuple
label, selected_game_id = st.sidebar.selectbox(
    "Choose a game:",
    options,
    format_func=lambda x: x[0],  # show only label
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
    render_sentiment_widget(comments_df)
with col00:
    render_game_events_widget(events_df)
