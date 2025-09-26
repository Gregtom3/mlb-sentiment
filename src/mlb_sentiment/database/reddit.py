import pandas as pd
from mlb_sentiment import config
from mlb_sentiment import utility
from datetime import date
import re


def format_reddit_text(text: str) -> str:
    """
    Clean Reddit text for storage:
      - Replace newlines, commas, *, #, and links
      - Trim to 255 chars
      - Remove non-ASCII
      - Collapse whitespace
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)

    text = (
        text.replace("\n", " ")
        .replace("\r", " ")
        .replace(",", " ")
        .replace("*", "")
        .replace("#", "")
    )
    if len(text) > 255:
        text = text[:255] + "..."

    # Remove non-ASCII characters
    text = "".join([c if ord(c) < 128 else " " for c in text])
    # Strip links
    text = re.sub(r"http\S+", "", text)
    # Collapse extra spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text


def save_reddit_comments(comments, limit: int = 5, filename: str = "MyDatabase"):
    """
    Save Reddit comments to a Parquet file.
    """
    comments_file = (
        filename
        if filename.endswith("_comments.parquet")
        else filename + "_comments.parquet"
    )

    all_comments = []
    comment_id_counter = 1
    for comment in comments:
        formatted_text = format_reddit_text(comment["text"])
        # Skip very short/noisy comments
        if len(re.findall(r"[A-Za-z0-9]", formatted_text)) <= 3:
            continue
        all_comments.append(
            {
                "id": comment_id_counter,
                "game_id": comment.get("game_id"),
                "author": comment["author"],
                "text": formatted_text,
                "created_est": utility.utc_to_est(comment["created_utc"]),
                "sentiment": comment["sentiment"]["emotion"],
                "sentiment_score": comment["sentiment"]["score"],
            }
        )
        comment_id_counter += 1

    pd.DataFrame(all_comments).to_parquet(comments_file, index=False, engine="pyarrow")
    print(f"Saved {len(all_comments)} comments into Parquet: {comments_file}")


def save_reddit_posts(posts, limit: int = 5, filename: str = "MyDatabase"):
    """
    Save Reddit posts to a Parquet file.
    """
    posts_file = (
        filename if filename.endswith("_posts.parquet") else filename + "_posts.parquet"
    )

    all_posts = []
    post_id_counter = 1
    for post in posts:
        all_posts.append(
            {
                "id": post_id_counter,
                "game_id": post["game_id"],
                "team_acronym": post["team_acronym"].upper(),
                "post_title": post["title"],
                "post_url": post["url"],
                "created_est": post["created_est"],
            }
        )
        post_id_counter += 1

    pd.DataFrame(all_posts).to_parquet(posts_file, index=False, engine="pyarrow")
    print(f"Saved {len(all_posts)} posts into Parquet: {posts_file}")
