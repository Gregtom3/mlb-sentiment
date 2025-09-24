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

    container_css = """
.st-key-sentiment-container {
	background-color: #FFFFFF; /* White background */
    padding: 10px;
}
	"""
    st.html(f"<style>{container_css}</style>")
    with st.container(border=True, key="sentiment-container"):
        # Defensive: ensure we have a DataFrame and the expected column
        if comments_df is None or comments_df.empty:
            st.info(
                "No comments available for sentiment chart. "
                "If comments were recently uploaded, try reloading the app or selecting the date again."
            )
            return
        if "created_est" not in comments_df.columns:
            st.warning(
                "Comments data is missing timestamp column 'created_est'. "
                "Check the data source or try reloading."
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
                Fan Sentiment Over Time
            </div>
            """,
            unsafe_allow_html=True,
        )
        # --- Slider to control bin size ---
        window_minutes = st.slider(
            "Select time window (minutes)",
            min_value=1,
            max_value=10,
            value=2,
            step=1,
            key="sentiment_window",
        )

        # compute_sentiment_ts is cached; pass through defensive typing
        try:
            sentiment_ts = compute_sentiment_ts(comments_df, window_minutes)
        except Exception as e:
            st.error(f"Error computing sentiment time series: {e}")
            return

        # Count comments per bin dynamically
        # Count comments per bin dynamically (defensive: ensure datetime index)
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
            autosize=True,
            barmode="overlay",
        )
        fig.update_yaxes(title_text="Sentiment", secondary_y=False)
        fig.update_yaxes(title_text="Comment count", secondary_y=True)

        # Display and capture clicks
        with st.container(border=False):
            selected_click = plotly_events(fig, click_event=True, key="sentiment-plot")
        # selected_click = plotly_events(fig, click_event=True)

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
