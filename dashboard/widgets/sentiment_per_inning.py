import pandas as pd
import streamlit as st
import plotly.graph_objects as go


@st.cache_data
def compute_inning_sentiment(comments_df, events_df):
    # Ensure datetime
    events_df = events_df.copy()
    events_df["est"] = pd.to_datetime(events_df["est"])
    comments_df = comments_df.copy()
    comments_df["created_est"] = pd.to_datetime(comments_df["created_est"])

    # --- Find inning boundaries: last event time per (game_id, inning)
    inning_bounds = (
        events_df.groupby(["game_id", "inning"])["est"]
        .max()
        .reset_index()
        .sort_values(["game_id", "est"])
    )

    # --- Add start time = previous boundary (or game start)
    inning_bounds["start_time"] = inning_bounds.groupby("game_id")["est"].shift(1)
    inning_bounds["start_time"] = inning_bounds["start_time"].fillna(
        events_df.groupby("game_id")["est"].transform("min")
    )

    # --- Join with comments
    merged = pd.merge(
        comments_df,
        inning_bounds,
        on="game_id",
        how="inner",
    )

    mask = (merged["created_est"] >= merged["start_time"]) & (
        merged["created_est"] < merged["est"]
    )
    merged = merged[mask]

    # Average sentiment per inning across games
    results = (
        merged.groupby("inning")["sentiment_score"]
        .mean()
        .reset_index(name="avg_sentiment")
    )

    return results


def render_inning_sentiment_widget(comments_df, events_df, games_df):
    st.html(
        """
        <style>
        .st-key-inning-sentiment-container {
            background-color: #FFFFFF;
            padding: 10px;
        }
        </style>
        """
    )
    with st.container(border=True, key="inning-sentiment-container", height=530):
        if (
            comments_df is None
            or comments_df.empty
            or events_df is None
            or events_df.empty
        ):
            st.info("No data available.")
            return

        st.markdown(
            """
            <div style="
                background-color:#F8F9FC;
                padding:10px;
                border-radius:6px 6px 0px 0px;
                border-color:#DADADA;
                border-width:1px;
                border-style:solid;
                margin:-10px;
                font-size:1.2em;
                font-weight:400;
            ">
                Average Inning Sentiment (All Games)
            </div>
            """,
            unsafe_allow_html=True,
        )

        agg_df = compute_inning_sentiment(comments_df, events_df)

        if agg_df.empty:
            st.info("No inning sentiment could be computed across games.")
            return

        # --- Plot
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=agg_df["inning"],
                y=agg_df["avg_sentiment"],
                marker_color=[
                    "rgba(52,194,48,0.8)" if v > 0 else "rgba(255,0,0,0.8)"
                    for v in agg_df["avg_sentiment"]
                ],
                text=[f"{v:.2f}" for v in agg_df["avg_sentiment"]],
                textposition="outside",
            )
        )
        fig.update_layout(
            paper_bgcolor="white",
            plot_bgcolor="white",
            yaxis=dict(title="Average Sentiment"),
            xaxis=dict(
                title="Inning",
                tickmode="array",
                tickvals=list(agg_df["inning"]),
                ticktext=list(agg_df["inning"]),
            ),
            margin=dict(l=40, r=20, t=40, b=40),
        )

        st.plotly_chart(fig, use_container_width=True)
