import streamlit as st
import pandas as pd
from mlb_sentiment.config import load_synapse_engine
import numpy as np
from utility import safe_read_sql
import altair as alt

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
click = alt.selection_point(fields=["created_est"], nearest=True, on="click")

if not comments_df.empty:
    comments_df["created_est"] = pd.to_datetime(comments_df["created_est"])

    # Resample into 2-min bins, mean sentiment
    sentiment_ts = (
        comments_df.set_index("created_est")
        .resample("2Min")["sentiment_score"]
        .mean()
        .reset_index()
    )

    # Rolling smooth
    sentiment_ts["sentiment_smooth"] = (
        sentiment_ts["sentiment_score"]
        .rolling(window=3, min_periods=1, center=True)
        .mean()
    )

    # -------------------
    # Build tooltip text for each window
    # -------------------
    def summarize_comments(window_start, window_end):
        # filter comments in this window
        mask = (comments_df["created_est"] >= window_start) & (
            comments_df["created_est"] < window_end
        )
        subset = comments_df.loc[mask]

        if subset.empty:
            return "", ""

        # top 3 positive
        top_pos = (
            subset.nlargest(3, "sentiment_score")[["author", "text", "sentiment_score"]]
            .apply(
                lambda r: f"{r['author']}: {r['text']} ({r['sentiment_score']:.2f})",
                axis=1,
            )
            .tolist()
        )
        top_pos_str = " | ".join(top_pos)

        # top 3 negative
        top_neg = (
            subset.nsmallest(3, "sentiment_score")[
                ["author", "text", "sentiment_score"]
            ]
            .apply(
                lambda r: f"{r['author']}: {r['text']} ({r['sentiment_score']:.2f})",
                axis=1,
            )
            .tolist()
        )
        top_neg_str = " | ".join(top_neg)

        return top_pos_str, top_neg_str

    # Create aligned window ranges for tooltips
    sentiment_ts["window_start"] = sentiment_ts["created_est"]
    sentiment_ts["window_end"] = sentiment_ts["created_est"] + pd.Timedelta(minutes=2)

    # Fill columns with top comments
    sentiment_ts[["top_pos", "top_neg"]] = sentiment_ts.apply(
        lambda r: pd.Series(summarize_comments(r["window_start"], r["window_end"])),
        axis=1,
    )

    st.subheader("Fan Sentiment (2Min bins)")

    x_min = sentiment_ts["created_est"].min()
    x_max = sentiment_ts["created_est"].max()

    chart = (
        alt.Chart(sentiment_ts)
        .mark_line(color="steelblue", point=True)
        .encode(
            x=alt.X(
                "created_est:T",
                title="Time (EST)",
                scale=alt.Scale(domain=[x_min, x_max], clamp=True),
            ),
            y=alt.Y(
                "sentiment_smooth:Q",
                title="Sentiment",
                scale=alt.Scale(domain=[-1, 1], clamp=True),
            ),
            tooltip=[
                alt.Tooltip("created_est:T", title="Time"),
                alt.Tooltip("sentiment_smooth:Q", title="Sentiment", format=".2f"),
                alt.Tooltip("top_pos:N", title="Top Positive Comments"),
                alt.Tooltip("top_neg:N", title="Top Negative Comments"),
            ],
        )
        .properties(width=1200, height=500)
        .add_params(click)
        .interactive()
    )

    chart = chart.configure_view(stroke="black")
    selected = st.altair_chart(chart, use_container_width=True)
    if selected is not None:
        print("HERE")
else:
    st.info("No comments found for this game.")
