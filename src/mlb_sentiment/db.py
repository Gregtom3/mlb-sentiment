import sqlite3
import os
from mlb_sentiment import config
from mlb_sentiment import utility
from mlb_sentiment.fetch.reddit import fetch_post_comments
from mlb_sentiment.fetch.reddit import fetch_team_game_threads


def save_post_to_db(post, limit=5):
    """
    Save a Reddit post and its top-level comments to the database.

    Args:
        post (dict): A dictionary containing post details (output from fetch_team_game_threads).
        limit (int): The maximum number of top-level comments to save.
    """

    data_dir = os.path.join(os.path.dirname(__file__), "../../data")
    os.makedirs(data_dir, exist_ok=True)
    db_path = os.path.join(data_dir, "reddit.db")

    conn = sqlite3.connect(db_path)
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
