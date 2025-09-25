import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_plotly_events2 import plotly_events
import os


def render_avg_sentiment_by_game_widget(
    comments_df: pd.DataFrame, games_df: pd.DataFrame, current_game_id: int
) -> None:
    """
    Render average sentiment score per game_id, aligned with game start times.

    Parameters
    ----------
    comments_df : pd.DataFrame
        Must contain ['game_id','sentiment_score'].
    games_df : pd.DataFrame
        Must contain ['game_id','game_start_time_est'].
    current_game_id : int
        The currently selected game_id (for reference).
    """

    # --- Styling
    container_css = """
.st-key-avg-sentiment-container {
    background-color: #FFFFFF;
    padding: 10px;
}
    """
    st.html(f"<style>{container_css}</style>")

    with st.container(border=True, key="avg-sentiment-container"):
        # Defensive checks
        if comments_df is None or comments_df.empty:
            st.info("No comments available to compute average sentiment.")
            return
        if not {"game_id", "sentiment_score"}.issubset(comments_df.columns):
            st.warning("comments_df must contain 'game_id' and 'sentiment_score'.")
            return
        if games_df is None or games_df.empty:
            st.info("No game data available to align sentiment with times.")
            return
        if not {"game_id", "game_start_time_est"}.issubset(games_df.columns):
            st.warning("games_df must contain 'game_id' and 'game_start_time_est'.")
            return

        st.markdown(
            """
            <div style="
                background-color:#F8F9FC;
                padding:10px;
                border-radius:6px;
                border-color:#DADADA;
                margin:0px 0;
                font-size:1.2em;
                font-weight:400;
            ">
                Average Sentiment by Game Start Time (EST)
            </div>
            """,
            unsafe_allow_html=True,
        )

        # --- Compute averages
        avg_sentiment = (
            comments_df.groupby("game_id")["sentiment_score"]
            .mean()
            .reset_index()
            .rename(columns={"sentiment_score": "avg_sentiment"})
        )

        # --- Merge with game start times
        merged = pd.merge(
            avg_sentiment,
            games_df[["game_id", "game_date"]],
            on="game_id",
            how="inner",
        ).dropna(subset=["game_date"])
        merged["game_date"] = pd.to_datetime(merged["game_date"])
        merged = merged.sort_values("game_date", ascending=True).reset_index(drop=True)
        abs_max_sentiment = merged["avg_sentiment"].abs().max() + 0.1
        # --- Build figure
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=list(merged["game_date"]),
                y=list(merged["avg_sentiment"]),
                mode="lines+markers",
                marker=dict(
                    # marker shape
                    symbol=[
                        (
                            "circle"
                            if merged.iloc[i]["game_id"] != current_game_id
                            else "star"
                        )
                        for i in range(len(merged))
                    ],
                    size=[
                        16 if merged.iloc[i]["game_id"] == current_game_id else 8
                        for i in range(len(merged))
                    ],
                    color=[
                        (
                            "rgb(63,131,242)"
                            if merged.iloc[i]["game_id"] != current_game_id
                            else "rgb(255,0,0)"
                        )
                        for i in range(len(merged))
                    ],
                ),
                line=dict(width=2, color="rgba(63,131,242,0.8)"),
                name="Avg Sentiment",
                text=merged["game_id"],
                hovertemplate="Date: %{x|%Y-%m-%d}<br>Avg Sentiment: %{y:.2f}<extra></extra>",
            )
        )

        fig.update_layout(
            autosize=True,
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=dict(family="Montserrat, sans-serif", size=14, color="black"),
            xaxis=dict(
                title="Game Start Time (EST)",
                showgrid=True,
                zeroline=False,
            ),
            yaxis=dict(
                title="Average Sentiment Score",
                zeroline=True,
                zerolinecolor="black",
                range=[-abs_max_sentiment, abs_max_sentiment],
            ),
        )
        selected_points = plotly_events(
            fig,
            click_event=True,
            select_event=False,
            hover_event=False,
            key="Avg Sentiment",
            config={"displayModeBar": False},  # works in the v2 fork
        )

        if selected_points:
            idx = selected_points[0]["pointIndex"]
            if 0 <= idx < len(merged):
                clicked_id = int(merged.iloc[idx]["game_id"])
                if clicked_id != current_game_id:  # only update if it changed
                    return clicked_id
        return None
