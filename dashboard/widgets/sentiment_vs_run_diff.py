import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np


def render_sentiment_vs_run_diff(
    comments_df: pd.DataFrame,
    games_df: pd.DataFrame,
    events_df: pd.DataFrame,
    team_acronym: str,
) -> None:
    """Scatter of game-level avg sentiment vs final run differential."""

    # --- Styling
    st.html(
        """
        <style>
        .st-key-sentiment-run-diff {
            background-color: #FFFFFF;
            padding: 10px;
        }
        </style>
        """
    )

    with st.container(border=True, key="sentiment-run-diff", height=530):

        if comments_df is None or comments_df.empty:
            st.info("No comments available for sentiment vs run diff.")
            return
        if events_df is None or events_df.empty:
            st.info("No events available for run differential.")
            return

        required_events = {
            "game_id",
            "est",
            "home_team",
            "away_team",
            "home_score",
            "away_score",
        }
        required_comments = {"game_id", "sentiment_score"}
        if not required_events.issubset(
            events_df.columns
        ) or not required_comments.issubset(comments_df.columns):
            st.warning(
                "events_df must contain est, scores & teams; comments_df must contain game_id, sentiment_score."
            )
            return

        st.markdown(
            f"""
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
                🤖 Game-Level Sentiment vs. Final Run Differential — {team_acronym}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # --- Ensure datetime
        comments_df = comments_df.copy()
        comments_df["created_est"] = pd.to_datetime(comments_df["created_est"])
        events_df = events_df.copy()
        events_df["est"] = pd.to_datetime(events_df["est"])

        # --- Final run differential per game
        final_scores = events_df.sort_values("est").groupby("game_id").tail(1).copy()
        is_home = final_scores["home_team"] == team_acronym
        is_away = final_scores["away_team"] == team_acronym
        final_scores.loc[is_home, "run_diff"] = (
            final_scores["home_score"] - final_scores["away_score"]
        )
        final_scores.loc[is_away, "run_diff"] = (
            final_scores["away_score"] - final_scores["home_score"]
        )
        final_scores = final_scores.dropna(subset=["run_diff"])[
            ["game_id", "run_diff", "est"]
        ]

        # --- Average sentiment per game
        avg_sent = (
            comments_df.groupby("game_id")["sentiment_score"].mean().reset_index()
        )

        # --- Merge
        results = pd.merge(final_scores, avg_sent, on="game_id", how="inner")

        if results.empty:
            st.info("No sentiment/run differential data available for plotting.")
            return

        # --- Scatter + regression
        x = results["run_diff"].to_numpy()
        y = results["sentiment_score"].to_numpy()
        customdata = results[["est", "game_id"]].to_numpy()

        # Regression line
        if len(x) >= 2:
            m, b = np.polyfit(x, y, 1)
            y_pred = m * x + b
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        else:
            m, b, r2 = 0, 0, 0

        fig = go.Figure()
        max_abs_sent = max(abs(y.min()), abs(y.max())) + 0.1

        # Scatter points
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="markers",
                name="Games",
                customdata=customdata,
                marker=dict(size=9, color="rgba(63,131,242,0.7)"),
                hovertemplate="Run Diff: %{x}<br>Avg Sentiment: %{y:.2f}<br>Date: %{customdata[0]|%Y-%m-%d}<br>Game ID: %{customdata[1]}<extra></extra>",
            )
        )

        # Regression line
        if len(x) >= 2:
            line_x = np.linspace(min(x), max(x), 100)
            line_y = m * line_x + b
            fig.add_trace(
                go.Scatter(
                    x=line_x,
                    y=line_y,
                    mode="lines",
                    name=f"Fit: y={m:.3f}x{'+' if b > 0 else ''}{b:.3f}, R²={r2:.3f}",
                    line=dict(color="black", dash="dash"),
                )
            )

        fig.update_layout(
            autosize=True,
            paper_bgcolor="white",
            plot_bgcolor="white",
            # font=dict(family="Montserrat, sans-serif", size=14, color="black"),
            xaxis=dict(title="Final Run Differential"),
            yaxis=dict(
                title="Average Sentiment (whole game)",
                range=[-max_abs_sent, max_abs_sent],
            ),
            margin=dict(l=75, r=20, t=40, b=40),
            showlegend=True,
            legend=dict(
                orientation="h",  # horizontal
                yanchor="bottom",  # anchor legend's bottom
                y=-0.5,  # just below the plotting area
                xanchor="center",  # anchor legend to center
                x=0.5,  # center it horizontally
                font=dict(size=18),
            ),
        )

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
