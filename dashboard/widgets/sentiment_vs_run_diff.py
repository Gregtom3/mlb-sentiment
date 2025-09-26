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

    with st.container(border=True, key="sentiment-run-diff", height=530):
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
                border-radius:6px 6px 0px 0px;
                border-color:#DADADA;
                border-width:1px;
                border-style:solid;
                margin:-10px;
                font-size:1.2em;
                font-weight:400;
            ">
                Sentiment vs. Run Differential — {team_acronym}
            </div>
            """,
            unsafe_allow_html=True,
        )

        comments_df = comments_df.copy()
        comments_df["created_est"] = pd.to_datetime(comments_df["created_est"])
        events_df = events_df.copy()
        events_df["est"] = pd.to_datetime(events_df["est"])

        # Compute run differential for each event
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

        results = []

        # --- Group by game_id
        for game_id, gdf in events_df.groupby("game_id"):
            gdf = gdf.sort_values("est").reset_index(drop=True)

            # Identify run_diff change points
            gdf["block_id"] = (gdf["run_diff"].shift() != gdf["run_diff"]).cumsum()

            for block_id, bdf in gdf.groupby("block_id"):
                run_diff = bdf["run_diff"].iloc[0]
                start_time = bdf["est"].min()
                end_time = bdf["est"].max()
                game_date = bdf["est"].iloc[0].date().strftime("%Y-%m-%d")
                # Select comments that fall inside this block window
                mask = (comments_df["created_est"] >= start_time) & (
                    comments_df["created_est"] <= end_time
                )
                block_comments = comments_df.loc[mask, "sentiment_score"]
                if block_comments.size < 8:
                    continue
                results.append(
                    {
                        "game_id": game_id,
                        "game_date": game_date,
                        "block_id": block_id,
                        "run_diff": run_diff,
                        "start_time": start_time,
                        "end_time": end_time,
                        "avg_sentiment": (
                            block_comments.mean()
                            if not block_comments.empty
                            else np.nan
                        ),
                        "n_comments": len(block_comments),
                    }
                )
        results = pd.DataFrame(results).dropna(subset=["avg_sentiment"])
        if results.empty:
            st.info("No sentiment/run differential data available for plotting.")
            return

        x = results["run_diff"].values
        y = results["avg_sentiment"].values
        customdata = np.stack([results["game_date"], results["n_comments"]], axis=-1)
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
                customdata=customdata,
                marker=dict(size=9, color="rgba(63,131,242,0.7)"),
                hovertemplate="Run Diff: %{x}<br>Avg Sentiment: %{y:.2f}<br>Game Date: %{customdata[0]}<br>Comments: %{customdata[1]}<extra></extra>",
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
