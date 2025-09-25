import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import textwrap


def wrap_comment(text: str, width: int = 100) -> str:
    """Remove newlines and wrap text with <br> every `width` chars at word boundaries."""
    clean = " ".join(str(text).split())  # remove existing newlines/extra spaces
    return "<br>".join(textwrap.wrap(clean, width=width, break_long_words=False))


def render_sentiment_distribution_histogram(comments_df: pd.DataFrame) -> None:
    """
    Render a histogram showing the distribution of positive, neutral,
    and negative sentiments for the selected date range.

    On hover, show the first comment in that bin.
    """

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
        if not {"sentiment", "sentiment_score", "text"}.issubset(comments_df.columns):
            st.warning("comments_df must contain 'sentiment','sentiment_score','text'.")
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

        fig = go.Figure()

        # Shared binning for consistency
        all_scores = comments_df["sentiment_score"].dropna()
        bins = np.histogram_bin_edges(all_scores, bins=100)

        def add_histogram(sentiment, color):
            subset = comments_df[comments_df["sentiment"] == sentiment]
            if subset.empty:
                return

            # Digitize to bins
            inds = np.digitize(subset["sentiment_score"].values, bins) - 1

            # Store first comment (and score) per bin
            bin_text = {}
            for pos, (_, row) in enumerate(subset.iterrows()):
                b = inds[pos]
                if b not in bin_text:  # keep only first seen in that bin
                    score = row["sentiment_score"]
                    text = wrap_comment(row["text"], 100)
                    bin_text[b] = f"({score:.2f}) {text}"

            # Build bar heights
            counts, _ = np.histogram(subset["sentiment_score"], bins=bins)

            # Align hover texts with bins
            texts = [bin_text.get(i, "") for i in range(len(bins) - 1)]

            # Add to Bar trace
            fig.add_trace(
                go.Bar(
                    x=(bins[:-1] + bins[1:]) / 2,
                    y=counts,
                    name=sentiment.capitalize(),
                    marker=dict(color=color),
                    opacity=0.7,
                    text=texts,
                    hovertemplate="<b>%{y}</b> comments<br>%{text}<extra></extra>",
                )
            )

        add_histogram("positive", "rgba(0,200,0,0.6)")
        add_histogram("negative", "rgba(200,0,0,0.6)")

        fig.update_layout(
            barmode="overlay",
            autosize=True,
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=dict(family="Montserrat, sans-serif", size=14, color="black"),
            xaxis=dict(title="Sentiment Score", showgrid=True, zeroline=False),
            yaxis=dict(title="Count", zeroline=True, zerolinecolor="black"),
            margin=dict(l=60, r=20, t=40, b=40),
        )

        st.plotly_chart(fig, use_container_width=True)
