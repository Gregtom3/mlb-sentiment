import pandas as pd
import streamlit as st


def render_commenter_summary_widget(comments_df: pd.DataFrame) -> None:
    """
    Render metrics for comments in the selected date range:
    - Top 3 most active commenters
    - Top 3 positive commenters (+ top 2 comments from #1, green)
    - Top 3 negative commenters (+ top 2 comments from #1, red)
    """

    if comments_df is None or comments_df.empty:
        st.info("No comments available for this date range.")
        return

    if not {"author", "sentiment", "sentiment_score", "created_est", "text"}.issubset(
        comments_df.columns
    ):
        st.warning(
            "comments_df must contain 'author','sentiment','sentiment_score','created_est','text' columns."
        )
        return

    # --- Compute Top ---
    # Remove 'None' from authors
    comments_df = comments_df[comments_df["author"] != "None"]
    top_commenters = comments_df["author"].value_counts().head(6)

    pos_df = comments_df[comments_df["sentiment"] == "positive"]
    top_positive = pos_df["author"].value_counts().head(3)

    neg_df = comments_df[comments_df["sentiment"] == "negative"]
    top_negative = neg_df["author"].value_counts().head(3)

    # --- Inject CSS for containers ---
    container_css = """
    <style>
    .metric-container {
        background-color: #FFFFFF;
        padding: 12px;
        border-radius: 8px;
        border: 1px solid #DADADA;
        box-shadow: 0px 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 12px;
        font-family: 'Poppins', sans-serif;
        height: 250px;
        overflow-y: auto;
    }
    .metric-title {
        font-weight: 600;
        font-size: 1.1em;
        margin-bottom: 6px;
    }
    .comment-green { color: #2E8B57; margin-top: 4px; }
    .comment-red { color: #B22222; margin-top: 4px; }
    .user-line { margin-bottom: 4px; }
    </style>
    """
    st.markdown(container_css, unsafe_allow_html=True)

    def format_top(series: pd.Series) -> str:
        """Format top 3 results into 'user (count)' lines."""
        return " ".join(
            [
                f"<div class='user-line'>{idx} ({val})</div>"
                for idx, val in series.items()
            ]
        )

    # --- Column layout ---
    col1, col2, col3 = st.columns(3)

    # Column 1: Most Active
    with col1:
        html = f"""
        <div class='metric-container'>
            <div class='metric-title'>Most Active Commenters</div>
            {format_top(top_commenters) if not top_commenters.empty else 'N/A'}
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)

    # Column 2: Most Positive
    with col2:
        extra = ""
        if not top_positive.empty:
            top_user = top_positive.index[0]
            user_comments = pos_df.sort_values("sentiment_score", ascending=False).head(
                3
            )
            for _, row in user_comments.iterrows():
                ts = pd.to_datetime(row["created_est"]).strftime("%Y-%m-%d %H:%M")
                score = round(row["sentiment_score"], 5)
                text = row["text"]
                extra += (
                    f"<div class='comment-green'>[{ts}] (Score {score}) — {text}</div>"
                )
        html = f"""
        <div class='metric-container'>
            <div class='metric-title'>Most Positive Commenters</div>
            {format_top(top_positive) if not top_positive.empty else 'N/A'}
            {extra}
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)

    # Column 3: Most Negative
    with col3:
        extra = ""
        if not top_negative.empty:
            top_user = top_negative.index[0]
            user_comments = neg_df.sort_values("sentiment_score", ascending=True).head(
                3
            )
            for _, row in user_comments.iterrows():
                ts = pd.to_datetime(row["created_est"]).strftime("%Y-%m-%d %H:%M")
                score = round(row["sentiment_score"], 5)
                text = row["text"]
                extra += (
                    f"<div class='comment-red'>[{ts}] (Score {score}) — {text}</div>"
                )
        html = f"""
        <div class='metric-container'>
            <div class='metric-title'>Most Negative Commenters</div>
            {format_top(top_negative) if not top_negative.empty else 'N/A'}
            {extra}
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)
