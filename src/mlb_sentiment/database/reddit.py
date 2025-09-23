import pandas as pd
from mlb_sentiment import config
from mlb_sentiment import utility
from datetime import date


def get_connection(db_filename: str = "MyDatabase.db"):
    conn = sqlite3.connect(db_filename, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def format_reddit_text(text):
    """
    Format Reddit text by replacing newlines and commas to ensure CSV compatibility.

    Args:
        text (str): The original Reddit text.
    Returns:
        str: The formatted text.
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
    return text


def save_reddit_comments(comments, limit=5, filename: str = "MyDatabase"):
    """
    Save multiple Reddit comments to a CSV file.

    Args:
        comments (list): A list of dictionaries (from fetch_reddit_comments).
        limit (int): Number of top-level comments to save per post.
        filename (str): Base filename (extension auto-added).
    """
    comments_csv = (
        filename if filename.endswith("_comments.csv") else filename + "_comments.csv"
    )

    all_comments = []
    comment_id_counter = 1  # mimic autoincrement ids
    for comment in comments:
        # Collect comment info with an ID
        comment_row = {
            "id": comment_id_counter,
            "game_id": comment.get("game_id"),
            "author": comment["author"],
            "text": format_reddit_text(comment["text"]),
            "created_est": utility.utc_to_est(comment["created_utc"]),
            "sentiment": comment["sentiment"]["emotion"],
            "sentiment_score": comment["sentiment"]["score"],
        }
        all_comments.append(comment_row)
        comment_id_counter += 1

    # Write CSV
    pd.DataFrame(all_comments).to_csv(comments_csv, index=False, encoding="utf-8")
    print(f"Saved {len(all_comments)} comments into CSV: {comments_csv}")


def save_reddit_posts(posts, limit=5, filename: str = "MyDatabase"):
    """
    Save multiple Reddit posts to a CSV file.

    Args:
        posts (list): A list of dictionaries (from fetch_reddit_posts).
        limit (int): Number of top-level comments to save per post.
        filename (str): Base filename (extension auto-added).
    """
    posts_csv = filename if filename.endswith("_posts.csv") else filename + "_posts.csv"

    all_posts = []
    post_id_counter = 1  # mimic autoincrement ids
    for post in posts:
        # Collect post info with an ID
        post_row = {
            "id": post_id_counter,
            "game_id": post["game_id"],
            "team_acrononym": post["team_acronym"].upper(),
            "post_title": post["title"],
            "post_url": post["url"],
            "created_est": post["created_est"],
        }
        all_posts.append(post_row)
        post_id_counter += 1

    # Write CSV
    pd.DataFrame(all_posts).to_csv(posts_csv, index=False, encoding="utf-8")
    print(f"Saved {len(all_posts)} posts into CSV: {posts_csv}")


## Removed all database functions and logic
