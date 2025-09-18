import sqlite3
import os
import pandas as pd
from mlb_sentiment import config
from mlb_sentiment import utility
from mlb_sentiment.fetch.reddit import fetch_post_comments
from mlb_sentiment.fetch.reddit import fetch_team_game_threads


def get_connection(db_filename: str = "MyDatabase.db"):
    conn = sqlite3.connect(db_filename, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def save_posts_to_db(
    posts, limit=5, db_filename: str = "MyDatabase.db", as_csv: bool = False
):
    """
    Save multiple Reddit posts and their top-level comments to the database.

    Args:
        posts (list): A list of dictionaries containing post details (output from fetch_team_game_threads).
        limit (int): The maximum number of top-level comments to save per post.
    """
    for post in posts:
        save_post_to_db(post, limit=limit, db_filename=db_filename)

    # Optionally export to CSV after all posts saved
    if as_csv:
        base, ext = os.path.splitext(db_filename)
        # Create filenames for posts and comments
        posts_csv = base + "_posts.csv"
        comments_csv = base + "_comments.csv"
        # Ensure .csv extension
        if not posts_csv.lower().endswith(".csv"):
            posts_csv = posts_csv + ".csv"
        if not comments_csv.lower().endswith(".csv"):
            comments_csv = comments_csv + ".csv"

        conn = sqlite3.connect(db_filename)
        try:
            posts_df = pd.read_sql_query("SELECT * FROM posts", conn)
            comments_df = pd.read_sql_query("SELECT * FROM comments", conn)
            posts_df.to_csv(posts_csv, index=False)
            comments_df.to_csv(comments_csv, index=False)
            print(f"Exported posts to CSV: {posts_csv}")
            print(f"Exported comments to CSV: {comments_csv}")
        finally:
            conn.close()


def save_post_to_db(post, limit=5, db_filename: str = "MyDatabase.db"):
    """
    Save a Reddit post and its top-level comments to the database.

    Args:
        post (dict): A dictionary containing post details (output from fetch_team_game_threads).
        limit (int): The maximum number of top-level comments to save.
    """

    conn = get_connection(db_filename)
    cursor = conn.cursor()

    # Create the posts table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_acronym TEXT,
            post_title TEXT,
            post_url TEXT,
            created_est TEXT
        )
        """
    )

    # Create the comments table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            author TEXT,
            text TEXT,
            created_est TEXT,
            FOREIGN KEY (post_id) REFERENCES posts (id),
            UNIQUE(author, created_est)
        )
        """
    )
    conn.commit()

    # Check if the post already exists
    cursor.execute(
        """
        SELECT id FROM posts WHERE post_url = ?
        """,
        (post["url"],),
    )
    result = cursor.fetchone()

    if result:
        post_id = result[0]
    else:
        # Insert the post into the posts table
        cursor.execute(
            """
            INSERT INTO posts (team_acronym, post_title, post_url, created_est)
            VALUES (?, ?, ?, ?)
            """,
            (
                post["team_acronym"].upper(),
                post["title"],
                post["url"],
                post["created_est"],
            ),
        )
        post_id = cursor.lastrowid  # Get the ID of the inserted post

    # Fetch comments for the post
    comments = fetch_post_comments(post["url"], limit=limit)

    # Insert the comments into the comments table
    for comment in comments:
        cursor.execute(
            """
            INSERT OR IGNORE INTO comments (post_id, author, text, created_est)
            VALUES (?, ?, ?, ?)
            """,
            (
                post_id,
                comment["author"],
                comment["text"],
                utility.utc_to_est(comment["created_utc"]),
            ),
        )
    conn.commit()

    conn.close()
    print(f"Saved post '{post.get('title')}' and comments to database ({db_filename}).")


def create_sentiment_results_table():
    """
    Create the sentiment_results table if it doesn't exist.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sentiment_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            comment_id INTEGER,
            model_type TEXT,
            emotion TEXT,
            score REAL,
            FOREIGN KEY (comment_id) REFERENCES comments (id),
            UNIQUE(comment_id, model_type)
        )
        """
    )
    conn.commit()
    conn.close()


def save_sentiment_result(comment_id, model_type, emotion, score):
    """
    Save a sentiment analysis result to the database.

    Args:
        comment_id (int): The ID of the comment.
        model_type (str): The type of sentiment model used.
        emotion (str): The detected emotion.
        score (float): The sentiment score.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO sentiment_results (comment_id, model_type, emotion, score)
        VALUES (?, ?, ?, ?)
        """,
        (comment_id, model_type, emotion, score),
    )
    conn.commit()
    conn.close()
