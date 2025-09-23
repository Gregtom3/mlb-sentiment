import streamlit as st
import pandas as pd
import numpy as np
from dataloader import get_engine, load_games, load_events, load_comments
from compute import compute_sentiment_ts
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_plotly_events import plotly_events

st.title("MLB Game Score Dashboard")

# -------------------
# Step 1: Pick a date
# -------------------
game_date = st.sidebar.date_input(
    "Select a game date", value=pd.to_datetime("2025-09-14")
)

# Initialize engine
engine = get_engine()

# Update cached queries to use imported functions
games_df = load_games(game_date, engine)

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

selected_game_id = int(game_choice.split("ID")[-1].strip(" )"))

# -------------------
# Query events & comments (cached)
# -------------------
events_df = load_events(selected_game_id, engine)
comments_df = load_comments(selected_game_id, engine)
sentiment_ts = compute_sentiment_ts(comments_df)

# -------------------
# Sentiment chart
# -------------------
if not comments_df.empty:
    st.subheader("Fan Sentiment (2Min bins)")
    fig = make_subplots()
    fig.add_trace(
        go.Scattergl(
            x=list(sentiment_ts["created_est"]),
            y=list(sentiment_ts["sentiment_smooth"]),
            mode="lines+markers",
            name="Sentiment (smoothed)",
        )
    )
    fig.update_layout(width=1100)

    selected_click = plotly_events(fig, click_event=True)

    # -------------------
    # Show top 3 comments for clicked window
    # -------------------
    if selected_click:
        clicked_time = pd.to_datetime(selected_click[0]["x"])
        bin_start = clicked_time.floor("2Min")
        bin_end = bin_start + pd.Timedelta(minutes=2)

        window_comments = comments_df[
            (comments_df["created_est"] >= bin_start)
            & (comments_df["created_est"] < bin_end)
        ]

        if not window_comments.empty:
            top_comments = window_comments.sort_values(
                "sentiment_score", ascending=False
            ).head(3)

            st.subheader(
                f"Top 3 Comments {bin_start.strftime('%H:%M')}–{bin_end.strftime('%H:%M')}"
            )
            for _, row in top_comments.iterrows():
                st.markdown(
                    f"**{row['author']}** ({row['sentiment_score']:.2f})\n\n{row['text']}"
                )
        else:
            st.info("No comments found in this time window.")
