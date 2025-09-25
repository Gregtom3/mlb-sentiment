import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np


def render_sentiment_vs_run_diff(
    comments_df: pd.DataFrame,
    events_df: pd.DataFrame,
    team_acronym: str,
    window_minutes: int = 4,
) -> None:
    """
    Scatter plot of average sentiment (per window) vs. run differential
    for the given team, using closest event differential in time.

    Parameters
    ----------
    comments_df : pd.DataFrame
        Must contain ['created_est','sentiment_score'].
    events_df : pd.DataFrame
        Must contain ['est','home_team','away_team','home_score','away_score'].
    team_acronym : str
        Team of interest (positive differential if this team is leading).
    window_minutes : int
        Size of rolling window in minutes (default = 4).
    """

    # --- Styling
    container_css = """
.st-key-sentiment-run-diff {
    background-color: #FFFFFF;
    padding: 10px;
}
    """
    st.html(f"<style>{container_css}</style>")

    with st.container(border=True, key="sentiment-run-diff"):
        if comments_df is None or comments_df.empty:
            st.info("No comments available for sentiment vs run diff.")
            return
        if events_df is None or events_df.empty:
            st.info("No events available for run differential.")
            return
        required_events = {"est", "home_team", "away_team", "home_score", "away_score"}
        required_comments = {"created_est", "sentiment_score"}
        if not required_events.issubset(
            events_df.columns
        ) or not required_comments.issubset(comments_df.columns):
            st.warning(
                "events_df must contain est, scores & teams; comments_df must contain created_est, sentiment_score."
            )
            return

        st.markdown(
            f"""
            <div style="
                background-color:#F8F9FC;
                padding:10px;
                border-radius:6px;
                border-color:#DADADA;
                margin:0px 0;
                font-size:1.2em;
                font-weight:400;
            ">
                Sentiment vs. Run Differential — {team_acronym}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # --- Average sentiment in rolling windows
        comments_df = comments_df.copy()
        comments_df["created_est"] = pd.to_datetime(comments_df["created_est"])
        comments_df = comments_df.set_index("created_est")

        sentiment_windowed = (
            comments_df["sentiment_score"]
            .resample(f"{window_minutes}Min")
            .mean()
            .dropna()
            .reset_index()
            .rename(columns={"sentiment_score": "avg_sentiment"})
        )

        # --- Compute run differential at each event
        events_df = events_df.copy()
        events_df["est"] = pd.to_datetime(events_df["est"])
        diffs = []
        for _, row in events_df.iterrows():
            if row["home_team"] == team_acronym:
                diff = row["home_score"] - row["away_score"]
            elif row["away_team"] == team_acronym:
                diff = row["away_score"] - row["home_score"]
            else:
                diff = np.nan
            diffs.append(diff)
        events_df["run_diff"] = diffs
        events_df = events_df.dropna(subset=["run_diff"])

        # --- For each sentiment window, find closest run differential in time
        run_diffs = []
        for ts in sentiment_windowed["created_est"]:
            # compute absolute time difference
            closest_idx = (events_df["est"] - ts).abs().idxmin()
            run_diffs.append(events_df.loc[closest_idx, "run_diff"])
        sentiment_windowed["run_diff"] = run_diffs

        if sentiment_windowed.empty:
            st.info("No valid sentiment vs run differential data after matching.")
            return

        x = sentiment_windowed["run_diff"].values
        y = sentiment_windowed["avg_sentiment"].values

        # --- Linear regression
        m, b = np.polyfit(x, y, 1)
        y_pred = m * x + b
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        # --- Build figure
        fig = go.Figure()

        # Scatter points
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="markers",
                name="Windows",
                marker=dict(size=9, color="rgba(63,131,242,0.7)"),
                hovertemplate="Run Diff: %{x}<br>Avg Sentiment: %{y:.2f}<extra></extra>",
            )
        )

        # Best-fit line
        line_x = np.linspace(min(x), max(x), 100)
        line_y = m * line_x + b
        fig.add_trace(
            go.Scatter(
                x=line_x,
                y=line_y,
                mode="lines",
                name=f"Fit: y={m:.2f}x+{b:.2f}, R²={r2:.2f}",
                line=dict(color="black", dash="dash"),
            )
        )

        fig.update_layout(
            autosize=True,
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=dict(family="Montserrat, sans-serif", size=14, color="black"),
            xaxis=dict(title="Run Differential"),
            yaxis=dict(title="Average Sentiment (per 4 min)", range=[-1, 1]),
            margin=dict(l=75, r=20, t=40, b=40),
            showlegend=True,
        )

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
