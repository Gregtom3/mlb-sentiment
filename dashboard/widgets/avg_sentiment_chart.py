import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_plotly_events2 import plotly_events
from plotly.subplots import make_subplots
import os


def render_avg_sentiment_by_game_widget(
    comments_df: pd.DataFrame,
    games_df: pd.DataFrame,
    current_game_id: int,
    team_acronym: str = "",
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
    team_acronym : str
        Team of interest acronym (for win/loss determination).
    """

    # --- Styling
    container_css = """
.st-key-avg-sentiment-container {
    background-color: #FFFFFF;
    padding: 10px;
}
    """
    st.html(f"<style>{container_css}</style>")

    with st.container(border=True, key="avg-sentiment-container", height=620):
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
                border-radius:6px 6px 0px 0px;
                border-color:#DADADA;
                border-width:1px;
                border-style:solid;
                margin:-10px;
                font-size:1.2em;
                font-weight:400;
            ">
                Subreddit Sentiment Over Time
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <i>Click a point to select a game. The red star indicates the currently selected game.
            </i>
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
            games_df[
                [
                    "game_id",
                    "game_date",
                    "home_team",
                    "away_team",
                    "home_score",
                    "away_score",
                ]
            ],
            on="game_id",
            how="inner",
        ).dropna(subset=["game_date"])
        merged["game_date"] = pd.to_datetime(merged["game_date"])
        merged = merged.sort_values("game_date", ascending=True).reset_index(drop=True)
        abs_max_sentiment = merged["avg_sentiment"].abs().max() + 0.1

        # Add win/loss label
        def outcome(row):

            if pd.isna(row["home_score"]) or pd.isna(row["away_score"]):
                return ""
            if row["home_score"] > row["away_score"]:
                winner = row["home_team"]
            elif row["away_score"] > row["home_score"]:
                winner = row["away_team"]
            else:
                return f"{row['away_score']}-{row['home_score']} (Tie)"
            if team_acronym == row["home_team"]:
                team_of_interest = row["home_team"]
            elif team_acronym == row["away_team"]:
                team_of_interest = row["away_team"]
            else:
                return ""
            result = "Win" if winner == team_of_interest else "Loss"
            team_of_interest_score = (
                row["home_score"]
                if team_of_interest == row["home_team"]
                else row["away_score"]
            )
            opponent_score = (
                row["away_score"]
                if team_of_interest == row["home_team"]
                else row["home_score"]
            )
            return f"{team_of_interest_score}-{opponent_score} ({result})"

        merged["result_str"] = merged.apply(outcome, axis=1)
        # --- Build figure
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Scatter(
                x=list(merged["game_date"]),
                y=list(merged["avg_sentiment"]),
                mode="lines+markers",
                marker=dict(
                    # marker shape
                    symbol=[
                        (
                            "star"
                            if merged.iloc[i]["game_id"] == current_game_id
                            else (
                                "triangle-up"
                                if "Win" in merged.iloc[i]["result_str"]
                                else "triangle-down"
                            )
                        )
                        for i in range(len(merged))
                    ],
                    size=[
                        20 if merged.iloc[i]["game_id"] == current_game_id else 12
                        for i in range(len(merged))
                    ],
                    color=[
                        (
                            "gold"
                            if merged.iloc[i]["game_id"] == current_game_id
                            else (
                                "rgba(52,194,48,1.0)"
                                if "Win" in merged.iloc[i]["result_str"]
                                else "rgba(255,0,0,1.0)"
                            )
                        )
                        for i in range(len(merged))
                    ],
                    line=dict(width=2, color="rgba(0,0,0,0.5)"),
                    opacity=[1.0 for i in range(len(merged))],
                ),
                line=dict(width=2, color="rgba(0,0,0,0.5)"),
                name="Avg Sentiment",
                text=merged["game_id"],
                customdata=merged[["game_id", "result_str"]],
                hovertemplate=(
                    "Date: %{x|%Y-%m-%d}<br>"
                    "Avg Sentiment: %{y:.2f}<br>"
                    "Score: %{customdata[1]}<extra></extra>"
                ),
                showlegend=False,
            ),
            secondary_y=True,
        )
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="lines+markers",
                marker=dict(symbol="circle", size=10, color="black"),
                name="Avg Sentiment",  # legend label
            ),
            secondary_y=True,
        )
        fig.update_layout(
            autosize=True,
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=dict(family="Montserrat, sans-serif", size=14, color="black"),
            xaxis=dict(showgrid=True, zeroline=False, color="gray"),
            yaxis2=dict(
                zeroline=True,
                zerolinecolor="black",
                side="left",
                range=[-abs_max_sentiment, abs_max_sentiment],
            ),
            margin=dict(l=75, r=20, t=20, b=40),
        )
        # --- Prepare data
        games_df = games_df.copy()
        games_df["game_date"] = pd.to_datetime(games_df["game_date"])
        games_df = games_df.sort_values("game_date", ascending=True).reset_index(
            drop=True
        )

        # Compute cumulative differential
        games_df["differential"] = games_df["wins"] - games_df["losses"]
        daily_diff = games_df.groupby("game_date")["differential"].last().reset_index()
        # Split into positive/negative for coloring
        positive_mask = daily_diff["differential"] >= 0
        negative_mask = ~positive_mask

        # Maximum differential for y-axis range
        max_diff = (
            max(
                abs(daily_diff["differential"].min()),
                abs(daily_diff["differential"].max()),
            )
            + 1
        )

        # Blue bars for positive differential
        fig.add_trace(
            go.Bar(
                x=list(daily_diff.loc[positive_mask, "game_date"]),
                y=list(daily_diff.loc[positive_mask, "differential"]),
                name="Above .500",
                marker_color="rgba(200,200,200,0.6)",
                hovertemplate="Date: %{x|%Y-%m-%d}<br>Differential: %{y}<extra></extra>",
            ),
            secondary_y=False,
        )

        # Red bars for negative differential
        fig.add_trace(
            go.Bar(
                x=list(daily_diff.loc[negative_mask, "game_date"]),
                y=list(daily_diff.loc[negative_mask, "differential"]),
                name="Below .500",
                marker_color="rgba(150,150,150,0.6)",
                hovertemplate="Date: %{x|%Y-%m-%d}<br>Differential: %{y}<extra></extra>",
            ),
            secondary_y=False,
        )

        fig.update_yaxes(
            title_text="W-L Differential",
            color="gray",
            secondary_y=False,
            side="right",
            range=[-max_diff, max_diff],
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
