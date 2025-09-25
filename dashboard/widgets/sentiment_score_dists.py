import streamlit as st
import pandas as pd
import plotly.graph_objects as go


def render_sentiment_distribution_histogram(comments_df: pd.DataFrame) -> None:
    """
    Render a histogram showing the distribution of positive, neutral,
    and negative sentiments for the selected date range.

    Parameters
    ----------
    comments_df : pd.DataFrame
        Must contain ['sentiment', 'sentiment_score', 'created_est'].
    """

    # --- Styling
    container_css = """
.st-key-sentiment-distribution {
    background-color: #FFFFFF;
    padding: 10px;
}
    """
    st.html(f"<style>{container_css}</style>")

    with st.container(border=True, key="sentiment-distribution"):
        if comments_df is None or comments_df.empty:
            st.info("No comments available for sentiment distribution.")
            return
        if not {"sentiment", "sentiment_score"}.issubset(comments_df.columns):
            st.warning("comments_df must contain 'sentiment' and 'sentiment_score'.")
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
                Sentiment Distribution (Selected Date Range)
            </div>
            """,
            unsafe_allow_html=True,
        )

        # --- Prepare figure
        fig = go.Figure()

        # Positive
        pos = comments_df[comments_df["sentiment"] == "positive"]["sentiment_score"]
        fig.add_trace(
            go.Histogram(
                x=pos,
                name="Positive",
                marker=dict(color="rgba(0,200,0,0.6)"),  # green
                opacity=0.7,
            )
        )

        # Negative
        neg = comments_df[comments_df["sentiment"] == "negative"]["sentiment_score"]
        fig.add_trace(
            go.Histogram(
                x=neg,
                name="Negative",
                marker=dict(color="rgba(200,0,0,0.6)"),  # red
                opacity=0.7,
            )
        )

        # Layout
        fig.update_layout(
            barmode="overlay",  # allow overlap w/ transparency
            autosize=True,
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=dict(family="Montserrat, sans-serif", size=14, color="black"),
            xaxis=dict(title="Sentiment Score", showgrid=True, zeroline=False),
            yaxis=dict(title="Count", zeroline=True, zerolinecolor="black"),
            margin=dict(l=60, r=20, t=40, b=40),
        )

        st.plotly_chart(fig, use_container_width=True)
