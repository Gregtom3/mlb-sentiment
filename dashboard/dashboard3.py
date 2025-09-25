# Standard library
from datetime import datetime

# Third-party packages
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from streamlit_date_picker import date_picker, PickerType
from streamlit_plotly_events import plotly_events

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

# Pick a team
# -------------------
team_name = st.sidebar.selectbox(
    "Select Team",
    options=get_all_team_names(),
    index=18,
)
team_acronym = get_team_acronym_from_team_name(team_name)

# Pick a date range
# -------------------
game_dates = st.sidebar.date_input(
    "Select a range of dates",
    value=(pd.to_datetime("2025-09-20"), pd.to_datetime("2025-09-21")),
)


# Update cached queries to use imported functions
games_df = load_games(game_dates, team_acronym, engine)

if games_df.empty:
    st.warning("No games found for this date.")
    st.stop()

# -------------------
# Step 2: Pick a game
# Include game number (1 or 2) depending on doubleheader
# -------------------
# Build list of tuples: (label, game_id)
options = [
    (f"{r['away_team']} @ {r['home_team']} Game {r.name+1}", r["game_id"])
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
# Two simple placeholder widgets (y=x^2 and y=x^3)
col1, col2 = st.columns(2)
# make plots
with col1:
    x = np.linspace(0, 10, 100)
    y1 = x**2
    fig1 = go.Figure(data=go.Scatter(x=x, y=y1, mode="lines", name="y=x^2"))
    fig1.update_layout(title="Plot of y=x^2", xaxis_title="x", yaxis_title="y")
    st.plotly_chart(fig1, use_container_width=True)
with col2:
    x = np.linspace(0, 10, 100)
    y2 = x**3
    fig2 = go.Figure(data=go.Scatter(x=x, y=y2, mode="lines", name="y=x^3"))
    fig2.update_layout(title="Plot of y=x^3", xaxis_title="x", yaxis_title="y")
    st.plotly_chart(fig2, use_container_width=True)
