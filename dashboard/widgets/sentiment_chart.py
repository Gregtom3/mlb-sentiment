import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_plotly_events2 import plotly_events
from compute import compute_sentiment_ts
import numpy as np


def render_sentiment_widget(
    comments_df: pd.DataFrame,
    events_df: pd.DataFrame,
    team_is_home: int,
    team_acronym: str = "",
    games_df: pd.DataFrame = None,
    current_game_id: int = None,
) -> None:
    """
    Renders sentiment-over-time + score differential overlay,
    with interactive tables of game events and Reddit comments.

    Expects:
      comments_df: ['created_est','author','sentiment_score','text']
      events_df: ['est','home_score','away_score','event','description']
      team_is_home: boolean indicating if the team is home team
      team_acronym: used for reference
      games_df: ['game_id','home_team','away_team','game_date'] for header info
      current_game_id: for header info
    """

    # --- Styling
    container_css = """
.st-key-sentiment-container {
    background-color: #FFFFFF;
    padding: 10px;
}
    """
    st.html(f"<style>{container_css}</style>")
    with st.container(border=True, key="sentiment-container", height=620):
        # Defensive checks
        if comments_df is None or comments_df.empty:
            st.info("No comments available for sentiment chart.")
            return
        if "created_est" not in comments_df.columns:
            st.warning("Comments missing timestamp column 'created_est'.")
            return

        if games_df is not None and current_game_id is not None:
            try:
                game_row = games_df.loc[games_df["game_id"] == current_game_id].iloc[0]
                home = game_row["home_team"]
                away = game_row["away_team"]
                date = pd.to_datetime(game_row["game_date"]).strftime("%Y-%m-%d")

                home_score = game_row.get("home_score", None)
                away_score = game_row.get("away_score", None)

                # --- Compute W/L ---
                if pd.notna(home_score) and pd.notna(away_score):
                    if home_score > away_score:
                        winner, loser = home, away
                        score_str = f"{home_score}-{away_score}"
                    elif away_score > home_score:
                        winner, loser = away, home
                        score_str = f"{away_score}-{home_score}"
                    else:
                        winner, loser = None, None
                        score_str = f"Tied {home_score}-{away_score}"

                    if winner is not None:
                        header_text = (
                            f"Individual Game: {away} @ {home} — {date} "
                            f"(<b>{winner} won {score_str}</b>)"
                        )
                    else:
                        header_text = (
                            f"Individual Game: {away} @ {home} — {date} ({score_str})"
                        )
                else:
                    header_text = f"Individual Game: {away} @ {home} — {date}"
            except Exception:
                header_text = "Fan Sentiment & Game Events Over Time"
        else:
            header_text = "Fan Sentiment & Game Events Over Time"

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
                {header_text}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Italic note
        st.markdown(
            "<i>Click on sentiment peaks/valleys to see related game events and comments.</i>",
            unsafe_allow_html=True,
        )
        window_minutes = 4

        # --- Compute rolling sentiment
        try:
            sentiment_ts = compute_sentiment_ts(comments_df, window_minutes)
        except Exception as e:
            st.error(f"Error computing sentiment time series: {e}")
            return

        # --- Comment counts (y2 axis)
        try:
            comment_counts = (
                comments_df.set_index("created_est")
                .resample(f"{window_minutes}Min")
                .size()
                .rename("comment_count")
            )
        except Exception as e:
            st.error(f"Error aggregating comment counts: {e}")
            return

        # --- Compute score differential from events_df
        diff_series = None
        if events_df is not None and not events_df.empty:
            try:
                events_df = pd.DataFrame(events_df)
                times = pd.to_datetime(events_df["est"])
                home_scores = pd.to_numeric(
                    events_df["home_score"], errors="coerce"
                ).fillna(0)
                away_scores = pd.to_numeric(
                    events_df["away_score"], errors="coerce"
                ).fillna(0)
                differential = np.where(
                    team_is_home, home_scores - away_scores, away_scores - home_scores
                ).astype(int)
                diff_series = pd.Series(differential, index=times)

            except Exception:
                diff_series = None

        # --- Build figure
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        mask = sentiment_ts["sentiment_smooth"] >= 0
        sentiment_pos = np.where(mask, sentiment_ts["sentiment_smooth"], 0)
        sentiment_neg = np.where(~mask, sentiment_ts["sentiment_smooth"], 0)
        # Positive fill
        fig.add_trace(
            go.Scatter(
                x=list(sentiment_ts["created_est"]),
                y=list(sentiment_pos),
                fill="tozeroy",
                fillcolor="rgba(0, 255, 0, 0.5)",
                mode="none",
                hoverinfo="skip",
                showlegend=False,
            ),
            secondary_y=False,
        )
        # Negative fill
        fig.add_trace(
            go.Scatter(
                x=list(sentiment_ts["created_est"]),
                y=list(sentiment_neg),
                fill="tozeroy",
                fillcolor="rgba(255, 0, 0, 0.5)",
                mode="none",
                hoverinfo="skip",
                showlegend=False,
            ),
            secondary_y=False,
        )
        # Black line (sentiment smooth)
        fig.add_trace(
            go.Scatter(
                x=list(sentiment_ts["created_est"]),
                y=list(sentiment_ts["sentiment_smooth"]),
                name="Sentiment",
                line=dict(color="black", width=2),
                mode="lines",
                showlegend=True,
            ),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=list(diff_series.index),
                y=list(diff_series.values),
                line=dict(color="gray", width=2, dash="dot"),
                mode="lines",
                name="Run Differential",
                hoverinfo="skip",
            ),
            secondary_y=True,
        )
        fig.update_layout(
            autosize=True,
            paper_bgcolor="white",
            plot_bgcolor="white",
            margin=dict(l=75, r=20, t=20, b=60),
        )
        max_abs_diff = (
            np.nanmax(np.abs(diff_series.values)) if diff_series is not None else 1
        )
        fig.update_yaxes(
            title_text=f"{team_acronym} Lead (+/-)",
            secondary_y=True,
            side="right",
            title_font=dict(size=18, family="Montserrat, sans-serif"),
            showgrid=False,
            color="gray",
            zeroline=True,
            zerolinecolor="gray",
            zerolinewidth=1,
            range=[-max_abs_diff, max_abs_diff],  # symmetric around 0
        )
        fig.update_xaxes(
            title_text="4-Minute Comment Intervals (EST)",
            title_font=dict(size=18, family="Montserrat, sans-serif"),
        )
        fig.update_yaxes(
            title_text="Sentiment",
            secondary_y=False,
            side="left",
            title_font=dict(size=18, family="Montserrat, sans-serif"),
            color="black",
            zeroline=True,
            zerolinecolor="black",
            zerolinewidth=1,
            range=[-1, 1],  # symmetric around 0
        )
        # --- Interactive click events
        with st.container(border=False):
            selected_click = plotly_events(
                fig,
                click_event=True,
                key="sentiment-plot",
                config={"displayModeBar": False},
            )

        # --- Show data tables for clicked bin
        if selected_click:
            clicked_time = pd.to_datetime(selected_click[0]["x"])
            bin_start = clicked_time.floor(f"{window_minutes}Min")
            bin_end = bin_start + pd.Timedelta(minutes=window_minutes)

            # 1) Game events in this window
            window_events = events_df[
                (pd.to_datetime(events_df["est"]) >= bin_start)
                & (pd.to_datetime(events_df["est"]) < bin_end)
            ]

            if not window_events.empty:
                events_table = window_events.loc[
                    :, ["halfInning", "description"]
                ].copy()
                events_table = events_table.rename(
                    columns={"halfInning": "Inning", "description": "Event Description"}
                )
                st.subheader(
                    f"Game Events {bin_start.strftime('%H:%M')}–{bin_end.strftime('%H:%M')}"
                )
                st.dataframe(events_table, height=200)

            # 2) Reddit comments in this window
            window_comments = comments_df[
                (comments_df["created_est"] >= bin_start)
                & (comments_df["created_est"] < bin_end)
            ]
            if not window_comments.empty:
                table_df = (
                    window_comments.sort_values("sentiment_score", ascending=False)
                    .loc[:, ["author", "sentiment_score", "text"]]
                    .copy()
                )
                table_df["sentiment_score"] = table_df["sentiment_score"].round(2)
                table_df = table_df.rename(
                    columns={
                        "author": "User",
                        "sentiment_score": "Sentiment Score",
                        "text": "Comment",
                    }
                )
                st.subheader(
                    f"Reddit Comments {bin_start.strftime('%H:%M')}–{bin_end.strftime('%H:%M')}"
                )
                st.dataframe(
                    table_df,
                    height=300,
                    column_config={
                        "User": st.column_config.TextColumn("User", width="stretch"),
                        "Sentiment Score": st.column_config.NumberColumn(
                            "Sentiment", width=50
                        ),
                        "Comment": st.column_config.TextColumn("Comment", width=1200),
                    },
                )
