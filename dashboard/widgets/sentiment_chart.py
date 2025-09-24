import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_plotly_events import plotly_events
from compute import compute_sentiment_ts


def render_sentiment_widget(comments_df: pd.DataFrame):
    """
    Renders the sentiment-over-time chart and interactive comments table.
    Expects comments_df to have ['created_est', 'author', 'sentiment_score', 'text'].
    Expects sentiment_ts to have ['created_est', 'sentiment_smooth'].
    """
    css = """
.st-key-my_custom_container {
	background-color: #ADD8E6; /* Light blue background */
}
	"""
    st.html(f"<style>{css}</style>")

    with st.container(border=True, key="my_custom_container"):
        if comments_df.empty:
            st.info("No comments available for sentiment chart.")
            return

        # --- Slider to control bin size ---
        window_minutes = st.slider(
            "Select time window (minutes)",
            min_value=1,
            max_value=10,
            value=2,
            step=1,
            key="sentiment_window",
        )

        sentiment_ts = compute_sentiment_ts(comments_df, window_minutes)

        st.subheader(f"Fan Sentiment ({window_minutes}-min bins)")

        # Count comments per bin dynamically
        comment_counts = (
            comments_df.set_index("created_est")
            .resample(f"{window_minutes}Min")
            .size()
            .rename("comment_count")
        )

        # Create figure
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Scattergl(
                x=list(sentiment_ts["created_est"]),
                y=list(sentiment_ts["sentiment_smooth"]),
                mode="lines+markers",
                name="Sentiment (smoothed)",
            ),
            secondary_y=False,
        )
        fig.add_trace(
            go.Bar(
                x=list(comment_counts.index),
                y=list(comment_counts.values),
                width=window_minutes * 60 * 1000,  # bar width in ms
                name="Comment count",
                marker_color="rgba(200,0,0,0.4)",
                opacity=1,
            ),
            secondary_y=True,
        )

        fig.update_layout(
            width=1000,
            barmode="overlay",
            plot_bgcolor="rgba(240,240,240,0.95)",
            paper_bgcolor="rgba(0,0,0,0)",  # outer background (transparent)
        )
        fig.update_yaxes(title_text="Sentiment", secondary_y=False)
        fig.update_yaxes(title_text="Comment count", secondary_y=True)

        # Display and capture clicks
        selected_click = plotly_events(fig, click_event=True)

        # Show comments table if a bin was clicked
        if selected_click:
            clicked_time = pd.to_datetime(selected_click[0]["x"])
            bin_start = clicked_time.floor(f"{window_minutes}Min")
            bin_end = bin_start + pd.Timedelta(minutes=window_minutes)

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
                    f"Comments {bin_start.strftime('%H:%M')}–{bin_end.strftime('%H:%M')}"
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
            else:
                st.info("No comments found in this time window.")
