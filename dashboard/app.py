# Standard library
from datetime import datetime, timedelta, date
import time
import logging

# Third-party packages
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_plotly_events2 import plotly_events

# Local modules
from compute import compute_sentiment_ts
from dataloader import (
    get_engine,
    load_comments,
    load_events,
    load_games,
    get_total_comments,
    get_total_games,
)
from mlb_sentiment.info import (
    get_all_team_names,
    get_team_acronym_from_team_name,
)
from widgets.data_summary import data_summary
from widgets.sentiment_chart import render_sentiment_widget
from widgets.avg_sentiment_chart import render_avg_sentiment_by_game_widget
from widgets.sentiment_score_dists import render_sentiment_distribution_histogram
from widgets.comment_summary import render_commenter_summary_widget
from widgets.sentiment_vs_run_diff import render_sentiment_vs_run_diff
from widgets.event_pie import render_event_pie_chart
from widgets.sentiment_per_inning import render_inning_sentiment_widget
from widgets.sentiment_per_game import render_win_loss_sentiment_widget

# -------------------
# Logging setup
# -------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def log_time(msg, start_time):
    elapsed = time.time() - start_time
    logger.info(f"{msg} (took {elapsed:.2f} s)")
    return time.time()


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

logger.info("==== Streamlit app rerun started ====")
t0 = time.time()

# -------------------
# Initialize engine
# -------------------
t = time.time()
engine = get_engine()
t = log_time("Initialized SQL engine", t)

# -------------------
# Title
# -------------------
st.title("MLB Pulse Dashboard")
logger.info("Rendered app title")

# -------------------
# Pick a team
# -------------------
team_name = st.sidebar.selectbox("Select Team", options=get_all_team_names(), index=18)
team_acronym = get_team_acronym_from_team_name(team_name)
logger.info(f"Selected team: {team_name} ({team_acronym})")

# -------------------
# Pick a date range (default: last 30 days)
# -------------------
default_start = date(2025, 3, 27)
default_end = datetime.today().date()

game_dates = st.sidebar.date_input(
    "Select a range of dates",
    value=(default_start, default_end),
    min_value=datetime(2024, 1, 1).date(),
    max_value=datetime.today().date(),
)
logger.info(f"Selected date range: {game_dates}")

# Sidebar: overall database stats
with st.sidebar:
    t = time.time()
    total_comments = get_total_comments(engine)
    t = log_time("Fetched total comments", t)
    st.metric("Total Comments in Database", f"{total_comments:,}")

with st.sidebar:
    total_games = get_total_games(engine)
    st.metric("Total Games in Database", f"{total_games:,}")

# -------------------
# Load games in range
# -------------------
t = time.time()
games_df = load_games(game_dates, team_acronym, engine)
t = log_time("Loaded games_df", t)

if games_df.empty:
    logger.warning("No games found for this team in the selected range.")
    st.warning("No games found for this team in the selected range.")
    st.stop()

# -------------------
# Session state setup
# -------------------
if "selected_game_id" not in st.session_state:
    st.session_state["selected_game_id"] = int(games_df.iloc[0]["game_id"])
    logger.info(f"Initialized selected_game_id={st.session_state['selected_game_id']}")

if st.session_state["selected_game_id"] not in games_df["game_id"].values:
    st.session_state["selected_game_id"] = int(games_df.iloc[0]["game_id"])
    logger.info(f"Reset selected_game_id={st.session_state['selected_game_id']}")

selected_game_id = st.session_state["selected_game_id"]
logger.info(f"Using selected_game_id={selected_game_id}")

# -------------------
# Team/game context
# -------------------
team_id = int(str(selected_game_id)[:3])
team_is_home = (
    games_df.loc[games_df["game_id"] == selected_game_id, "home_team"].values[0]
    == team_acronym
)
logger.info(f"team_id={team_id}, team_is_home={team_is_home}")

# -------------------
# Query events & comments
# -------------------
t = time.time()
events_df = load_events(team_id, engine)
t = log_time("Loaded events_df", t)

t = time.time()
comments_df = load_comments(team_id, engine)
t = log_time("Loaded comments_df", t)

# Filter
events_df = events_df[events_df["game_id"].isin(games_df["game_id"])]
comments_df = comments_df[comments_df["game_id"].isin(games_df["game_id"])]
logger.info(f"Filtered events_df={len(events_df)}, comments_df={len(comments_df)}")

# -------------------
# Render data summary metrics
# -------------------
t = time.time()
data_summary(comments_df, games_df, events_df, team_acronym)
t = log_time("Rendered data_summary widget", t)

# -------------------
# Render widgets
# -------------------
row1_col1, row1_col2 = st.columns(2)

with row1_col1:
    t = time.time()
    clicked_game_id = render_avg_sentiment_by_game_widget(
        comments_df, games_df, selected_game_id, team_acronym
    )
    t = log_time("Rendered avg_sentiment_by_game_widget", t)
    if clicked_game_id is not None:
        logger.info(f"User clicked game_id={clicked_game_id}, rerunning")
        st.session_state["selected_game_id"] = int(clicked_game_id)
        st.rerun()

with row1_col2:
    game_specific_events_df = events_df[events_df["game_id"] == selected_game_id]
    game_specific_comments_df = comments_df[comments_df["game_id"] == selected_game_id]
    t = time.time()
    render_sentiment_widget(
        game_specific_comments_df,
        game_specific_events_df,
        team_is_home,
        team_acronym,
        games_df,
        selected_game_id,
    )
    t = log_time("Rendered sentiment_widget", t)

# Row 2
row2_col1, row2_col2 = st.columns(2)
with row2_col1:
    t = time.time()
    render_win_loss_sentiment_widget(comments_df, games_df, team_acronym)
    t = log_time("Rendered win_loss_sentiment_widget", t)
with row2_col2:
    t = time.time()
    render_sentiment_vs_run_diff(comments_df, games_df, events_df, team_acronym)
    t = log_time("Rendered sentiment_vs_run_diff", t)

row3_col1, row3_col2 = st.columns(2)
with row3_col1:
    t = time.time()
    render_sentiment_distribution_histogram(comments_df)
    t = log_time("Rendered sentiment_distribution_histogram", t)

# Commenter summary widget
with row3_col2:
    t = time.time()
    render_commenter_summary_widget(comments_df)
    t = log_time("Rendered commenter_summary_widget", t)

# Sentiment vs Run Differential
row4_col1, row4_col2, row4_col3 = st.columns([1, 1, 2])

with row4_col1:
    t = time.time()
    render_event_pie_chart(
        events_df,
        title=f"{team_acronym} Batting Events",
        team_acronym=team_acronym,
        do_opponent=False,
    )
    t = log_time("Rendered event_pie_chart", t)
with row4_col2:
    t = time.time()
    render_event_pie_chart(
        events_df,
        title=f"Opponent Batting Events",
        team_acronym=team_acronym,
        do_opponent=True,
    )
    t = log_time("Rendered event_pie_chart", t)

with row4_col3:
    t = time.time()
    render_inning_sentiment_widget(comments_df, events_df, games_df)
    t = log_time("Rendered inning_sentiment_widget", t)

logger.info("==== Streamlit app rerun finished ====")
logger.info(f"TOTAL runtime for rerun: {time.time() - t0:.2f} s")
