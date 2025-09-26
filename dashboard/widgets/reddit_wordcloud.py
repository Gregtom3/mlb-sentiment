import streamlit as st
import pandas as pd
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt
import re


def _normalize_text(text: str) -> str:
    """Clean text: lowercase, strip punctuation, fix possessives."""
    if not isinstance(text, str):
        return ""

    # Lowercase for consistency
    text = text.lower()

    # Normalize apostrophes and possessives
    text = re.sub(r"(\w+)'s", r"\1s", text)  # "Met's" -> "Mets"
    text = re.sub(r"(\w+)'", r"\1", text)  # "Yankees'" -> "Yankees"

    # Common contractions
    text = text.replace("don't", "dont")
    text = text.replace("can't", "cant")
    text = text.replace("won't", "wont")
    text = text.replace("it's", "its")

    # Strip non-letters except spaces
    text = re.sub(r"[^a-z\s]", " ", text)

    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()

    # Remove short words (1-2 letters)
    text = " ".join([word for word in text.split() if len(word) > 2])
    return text


@st.cache_data
def get_wordcloud_cleaned_texts(comments_df: pd.DataFrame) -> str:
    """Helper to get cleaned combined text from comments_df for word cloud generation."""
    if comments_df is None or comments_df.empty:
        return ""
    if "text" not in comments_df.columns:
        return ""

    # Normalize all comments
    cleaned_texts = [_normalize_text(t) for t in comments_df["text"].dropna()]
    cleaned_texts = " ".join(cleaned_texts)
    return cleaned_texts


def render_wordcloud_widget(comments_df: pd.DataFrame, max_words: int = 50) -> None:
    """
    Render a word cloud from the 'text' column of comments_df.

    Parameters
    ----------
    comments_df : pd.DataFrame
        Must contain ['text'] column.
    max_words : int
        Maximum number of words to show in the word cloud.
    """

    # --- Styling
    container_css = """
    .st-key-wordcloud-container {
        background-color: #FFFFFF;
        padding: 10px;
    }
    """
    st.html(f"<style>{container_css}</style>")
    with st.container(border=True, key="wordcloud-container", height=530):
        if comments_df is None or comments_df.empty:
            st.info("No comments available for word cloud.")
            return
        if "text" not in comments_df.columns:
            st.warning("comments_df must contain a 'text' column.")
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
                Comment Word Cloud
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Normalize all comments
        cleaned_texts = get_wordcloud_cleaned_texts(comments_df)

        # Default stopwords + some extras
        stopwords = set(STOPWORDS)
        extra_stopwords = {
            "hes",
            "got",
            "don",
            "will",
            "see",
            "right",
            "let",
            "make",
            "game",
            "team",
            "season",
            "play",
            "year",
        }
        stopwords |= extra_stopwords
        # Generate word cloud
        wc = WordCloud(
            width=800,
            height=520,
            background_color="white",
            stopwords=stopwords,
            max_words=max_words,
            collocations=False,
            normalize_plurals=False,
            colormap="tab10",
            random_state=40,
        ).generate(cleaned_texts)

        # Plot
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")

        st.pyplot(fig)
