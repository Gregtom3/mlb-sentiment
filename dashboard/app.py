# Standard library
from datetime import datetime, timedelta

# Third-party packages
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_plotly_events2 import plotly_events

# Local modules
from compute import compute_sentiment_ts
from dataloader import get_engine, load_comments, load_events, load_games
from mlb_sentiment.info import (
    get_all_team_names,
    get_team_acronym_from_team_name,
)
from widgets.data_summary import data_summary
from widgets.sentiment_chart import render_sentiment_widget
from widgets.avg_sentiment_chart import render_avg_sentiment_by_game_widget
from widgets.wins_losses import render_wins_losses_histogram
from widgets.sentiment_score_dists import render_sentiment_distribution_histogram
from widgets.comment_summary import render_commenter_summary_widget
from widgets.sentiment_vs_run_diff import render_sentiment_vs_run_diff

# -------------------
# Streamlit setup
# -------------------
st.set_page_config(layout="wide")

# Load Google Font (Poppins)
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
engine = get_engine()

# -------------------
# Title
# -------------------
st.title("MLB Pulse Dashboard")

# -------------------
# Pick a team
# -------------------
team_name = st.sidebar.selectbox("Select Team", options=get_all_team_names(), index=18)
team_acronym = get_team_acronym_from_team_name(team_name)

# -------------------
# Pick a date range (default: last 30 days)
# -------------------
default_start = datetime.today().date() - timedelta(days=30)
default_end = datetime.today().date()

game_dates = st.sidebar.date_input(
    "Select a range of dates",
    value=(default_start, default_end),
    min_value=datetime(2024, 1, 1).date(),
    max_value=datetime.today().date(),
)

# -------------------
# Load games in range
# -------------------
games_df = load_games(game_dates, team_acronym, engine)

if games_df.empty:
    st.warning("No games found for this team in the selected range.")
    st.stop()

# -------------------
# Session state setup
# -------------------
if "selected_game_id" not in st.session_state:
    st.session_state["selected_game_id"] = int(games_df.iloc[0]["game_id"])

# If the currently selected game is no longer in the new range, reset it
if st.session_state["selected_game_id"] not in games_df["game_id"].values:
    st.session_state["selected_game_id"] = int(games_df.iloc[0]["game_id"])

selected_game_id = st.session_state["selected_game_id"]


# -------------------
# Team/game context
# -------------------
team_id = int(str(selected_game_id)[:3])
team_is_home = (
    games_df.loc[games_df["game_id"] == selected_game_id, "home_team"].values[0]
    == team_acronym
)

# -------------------
# Query events & comments
# -------------------
events_df = load_events(team_id, engine)
comments_df = load_comments(team_id, engine)

# Keep only games in this window
events_df = events_df[events_df["game_id"].isin(games_df["game_id"])]
comments_df = comments_df[comments_df["game_id"].isin(games_df["game_id"])]

# -------------------
# Render data summary metrics
# -------------------
data_summary(comments_df, games_df, events_df, team_acronym)

# -------------------
# Render widgets
# -------------------
row1_col1, row1_col2 = st.columns(2)

# Avg sentiment chart (used to pick the game)
with row1_col1:
    clicked_game_id = render_avg_sentiment_by_game_widget(
        comments_df, games_df, selected_game_id
    )
    if clicked_game_id is not None:
        st.session_state["selected_game_id"] = int(clicked_game_id)
        st.rerun()

# Sentiment timeline for the selected game
with row1_col2:
    game_specific_events_df = events_df[events_df["game_id"] == selected_game_id]
    game_specific_comments_df = comments_df[comments_df["game_id"] == selected_game_id]
    render_sentiment_widget(
        game_specific_comments_df,
        game_specific_events_df,
        team_is_home,
        team_acronym,
        games_df,
        selected_game_id,
    )

# Wins/Losses histogram
row2_col1, row2_col2 = st.columns(2)
with row2_col1:
    render_wins_losses_histogram(games_df, selected_game_id)

with row2_col2:
    render_sentiment_distribution_histogram(comments_df)

# Commenter summary widget
render_commenter_summary_widget(comments_df)

# Sentiment vs Run Differential
row3_col1, row3_col2 = st.columns(2)
with row3_col1:
    render_sentiment_vs_run_diff(comments_df, events_df, team_acronym)
