import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np


@st.cache_data
def get_game_outcome(game_events: pd.DataFrame, team: str) -> str | None:
    """Return 'win', 'loss', or None for the given team based on final score."""
    if game_events.empty:
        return None
    last_event = game_events.sort_values("est").iloc[-1]
    if last_event["home_team"] == team:
        return "win" if last_event["home_score"] > last_event["away_score"] else "loss"
    elif last_event["away_team"] == team:
        return "win" if last_event["away_score"] > last_event["home_score"] else "loss"
    return None


def render_sentiment_vs_run_diff(
    comments_df: pd.DataFrame,
    games_df: pd.DataFrame,
    events_df: pd.DataFrame,
    team_acronym: str,
    window_minutes: int = 4,
) -> None:
    """Fast scatter plot of avg sentiment vs run differential."""

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

    with st.container(border=True, key="sentiment-run-diff", height=620):
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

        # --- Game filters
        row1_col1, row1_col2 = st.columns(2)
        with row1_col1:
            include_home = st.checkbox("Home Games", value=True, key="sent-home")
        with row1_col2:
            include_away = st.checkbox("Away Games", value=True, key="sent-away")

        if not include_home and not include_away:
            st.info("Select at least one of Home or Away games.")
            return

        row2_col1, row2_col2 = st.columns(2)
        with row2_col1:
            include_wins = st.checkbox("Won Games", value=True, key="sent-wins")
        with row2_col2:
            include_losses = st.checkbox("Lost Games", value=True, key="sent-losses")
        if not include_wins and not include_losses:
            st.info("Select at least one of Won or Lost games.")

        # --- Filter events_df
        if include_home and not include_away:
            events_df = events_df[events_df["home_team"] == team_acronym]
        elif include_away and not include_home:
            events_df = events_df[events_df["away_team"] == team_acronym]

        if include_wins ^ include_losses:  # XOR → only wins OR only losses
            valid_games = [
                gid
                for gid, gdf in events_df.groupby("game_id")
                if get_game_outcome(gdf, team_acronym)
                == ("win" if include_wins else "loss")
            ]
            events_df = events_df[events_df["game_id"].isin(valid_games)]

        # --- Ensure datetime
        comments_df = comments_df.copy()
        comments_df["created_est"] = pd.to_datetime(comments_df["created_est"])
        events_df = events_df.copy()
        events_df["est"] = pd.to_datetime(events_df["est"])

        # --- Vectorized run differential
        is_home = events_df["home_team"] == team_acronym
        is_away = events_df["away_team"] == team_acronym
        events_df.loc[is_home, "run_diff"] = (
            events_df["home_score"] - events_df["away_score"]
        )
        events_df.loc[is_away, "run_diff"] = (
            events_df["away_score"] - events_df["home_score"]
        )
        events_df = events_df.dropna(subset=["run_diff"])

        results = []

        # --- Process each game (fewer Python loops, more groupby)
        for game_id, gdf in events_df.groupby("game_id"):
            gdf = gdf.sort_values("est")
            # identify change points: True where diff changes
            change_points = gdf["run_diff"].ne(gdf["run_diff"].shift()).cumsum()
            gdf["block_id"] = change_points

            block_summary = (
                gdf.groupby("block_id")
                .agg(
                    run_diff=("run_diff", "first"),
                    start_time=("est", "min"),
                    end_time=("est", "max"),
                )
                .reset_index(drop=True)
            )
            block_summary["game_id"] = game_id
            block_summary["game_date"] = gdf["est"].iloc[0].date().strftime("%Y-%m-%d")

            # --- Assign comments to blocks (vectorized join)
            for _, block in block_summary.iterrows():
                mask = (comments_df["created_est"] >= block["start_time"]) & (
                    comments_df["created_est"] <= block["end_time"]
                )
                block_comments = comments_df.loc[mask, "sentiment_score"]
                if len(block_comments) < 8:
                    continue
                results.append(
                    {
                        "game_id": game_id,
                        "game_date": block["game_date"],
                        "run_diff": block["run_diff"],
                        "avg_sentiment": block_comments.mean(),
                        "n_comments": len(block_comments),
                    }
                )

        if not results:
            st.info("No sentiment/run differential data available for plotting.")
            return

        results = pd.DataFrame(results)

        # --- Scatter + regression
        x = results["run_diff"].to_numpy()
        y = results["avg_sentiment"].to_numpy()
        customdata = np.stack([results["game_date"], results["n_comments"]], axis=-1)

        # Linear regression
        if len(x) >= 2:
            m, b = np.polyfit(x, y, 1)
            y_pred = m * x + b
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        else:
            m, b, r2 = 0, 0, 0

        fig = go.Figure()

        # Scatter
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

        # Regression line
        if len(x) >= 2:
            line_x = np.linspace(min(x), max(x), 100)
            line_y = m * line_x + b
            fig.add_trace(
                go.Scatter(
                    x=line_x,
                    y=line_y,
                    mode="lines",
                    name=f"Fit: y={m:.2f}x{'+' if b > 0 else ''}{b:.2f}, R²={r2:.2f}",
                    line=dict(color="black", dash="dash"),
                )
            )

        fig.update_layout(
            autosize=True,
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=dict(family="Montserrat, sans-serif", size=14, color="black"),
            xaxis=dict(title="Run Differential"),
            yaxis=dict(
                title=f"Average Sentiment (per {window_minutes} min)", range=[-1, 1]
            ),
            margin=dict(l=75, r=20, t=40, b=40),
            showlegend=True,
        )

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
