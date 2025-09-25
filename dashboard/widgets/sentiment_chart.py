import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_plotly_events import plotly_events
from compute import compute_sentiment_ts
import numpy as np


def render_sentiment_widget(
    comments_df: pd.DataFrame,
    events_df: pd.DataFrame,
    team_is_home: int,
    team_acronym: str = "",
) -> None:
    """
    Renders sentiment-over-time + score differential overlay,
    with interactive tables of game events and Reddit comments.

    Expects:
      comments_df: ['created_est','author','sentiment_score','text']
      events_df: ['est','home_score','away_score','event','description']
      team_is_home: boolean indicating if the team is home team
      team_acronym: used for reference
    """

    # --- Styling
    container_css = """
.st-key-sentiment-container {
    background-color: #FFFFFF;
    padding: 10px;
}
    """
    st.html(f"<style>{container_css}</style>")
    with st.container(border=True, key="sentiment-container"):
        # Defensive checks
        if comments_df is None or comments_df.empty:
            st.info("No comments available for sentiment chart.")
            return
        if "created_est" not in comments_df.columns:
            st.warning("Comments missing timestamp column 'created_est'.")
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
                Fan Sentiment & Game Events Over Time
            </div>
            """,
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
                    ~team_is_home, home_scores - away_scores, away_scores - home_scores
                ).astype(int)
                diff_series = pd.Series(differential, index=times)
            except Exception:
                diff_series = None

        # --- Build figure
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        mask = sentiment_ts["sentiment_smooth"] >= 0
        sentiment_pos = np.where(mask, sentiment_ts["sentiment_smooth"], 0)
        sentiment_neg = np.where(~mask, sentiment_ts["sentiment_smooth"], 0)
        fig.add_trace(
            go.Scatter(
                x=list(diff_series.index),
                y=list(diff_series.values),
                line=dict(color="gray", width=2, dash="dot"),
                mode="lines",
                name="Run Differential",
                hoverinfo="skip",
            ),
            secondary_y=False,
        )
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
            secondary_y=True,
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
            secondary_y=True,
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
            secondary_y=True,
        )

        fig.update_layout(autosize=True, paper_bgcolor="white", plot_bgcolor="white")
        max_abs_diff = (
            np.nanmax(np.abs(diff_series.values)) if diff_series is not None else 1
        )
        fig.update_yaxes(
            title_text=f"{team_acronym} Lead (+/-)",
            secondary_y=False,
            title_font=dict(size=18),
            showgrid=False,
            color="gray",
            zeroline=True,
            zerolinecolor="gray",
            zerolinewidth=1,
            range=[-max_abs_diff, max_abs_diff],  # symmetric around 0
        )
        fig.update_xaxes(title_text="EST Time", title_font=dict(size=18))
        fig.update_yaxes(
            title_text="Sentiment",
            secondary_y=True,
            title_font=dict(size=18),
            color="black",
            zeroline=True,
            zerolinecolor="black",
            zerolinewidth=1,
            range=[-1, 1],  # symmetric around 0
            anchor="x",
            overlaying="y",
        )
        # --- Interactive click events
        with st.container(border=False):
            selected_click = plotly_events(fig, click_event=True, key="sentiment-plot")

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
                events_table = window_events.loc[:, ["description"]].copy()
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
