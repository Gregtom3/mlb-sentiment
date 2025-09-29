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

    with st.container(border=True, key="sentiment-distribution", height=620):
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
                border-radius:6px 6px 0px 0px;
                border-color:#DADADA;
                border-width:1px;
                border-style:solid;
                margin:-10px;
                font-size:1.2em;
                font-weight:400;
            ">
                Sentiment Distribution (Selected Date Range)
            </div>
            """,
            unsafe_allow_html=True,
        )

        fig = go.Figure()

        # Shared binning for all sentiments
        all_scores = comments_df["sentiment_score"].dropna().values
        bins = np.histogram_bin_edges(all_scores, bins=100)
        bin_centers = (bins[:-1] + bins[1:]) / 2

        def add_histogram(sentiment, color):
            subset = comments_df[comments_df["sentiment"] == sentiment]
            if subset.empty:
                return

            scores = subset["sentiment_score"].values
            texts = subset["text"].astype(str).values

            # Vectorized bin assignment
            inds = np.digitize(scores, bins) - 1
            inds = np.clip(inds, 0, len(bins) - 2)  # keep in range

            # --- Vectorized counts ---
            counts = np.bincount(inds, minlength=len(bins) - 1)

            # --- First comment per bin ---
            # Use pandas groupby to pick first text per bin
            df_bins = pd.DataFrame({"bin": inds, "score": scores, "text": texts})
            first_texts = (
                df_bins.groupby("bin")
                .first(numeric_only=False)  # keep first row per bin
                .apply(
                    lambda row: f"({row['score']:.2f}) {wrap_comment(row['text'], 100)}",
                    axis=1,
                )
            )
            hover_texts = [first_texts.get(i, "") for i in range(len(bins) - 1)]

            # Add trace
            fig.add_trace(
                go.Bar(
                    x=bin_centers,
                    y=counts,
                    name=sentiment.capitalize(),
                    marker=dict(color=color),
                    opacity=0.7,
                    text=hover_texts,
                    hovertemplate="<b>%{y}</b> comments<br>%{text}<extra></extra>",
                )
            )

        add_histogram("positive", "rgba(0,200,0,0.6)")
        add_histogram("negative", "rgba(200,0,0,0.6)")

        fig.update_layout(
            barmode="overlay",
            autosize=True,
            height=550,
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=dict(family="Montserrat, sans-serif", size=14, color="black"),
            xaxis=dict(title="Sentiment Score", showgrid=True, zeroline=False),
            yaxis=dict(title="Count", zeroline=True, zerolinecolor="black"),
            margin=dict(l=60, r=20, t=40, b=40),
            showlegend=False,
        )

        st.plotly_chart(fig, use_container_width=True)
