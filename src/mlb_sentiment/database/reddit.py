import sqlite3
import os
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
        text.replace("\n", " ").replace("\r", " ").replace(",", " ").replace("* ", " ")
    )
    if len(text) > 255:
        text = text[:255] + "..."
    return text


def save_reddit_comments(
    comments, limit=5, filename: str = "MyDatabase", mode: str = "db"
):
    """
    Save multiple Reddit comments to either a DB or CSV.

    Args:
        comments (list): A list of dictionaries (from fetch_reddit_comments).
        limit (int): Number of top-level comments to save per post.
        filename (str): Base filename (extension auto-added).
        mode (str): 'db' (SQLite) or 'csv' (flat files).
    """
    if mode == "db":
        db_filename = filename if filename.endswith(".db") else filename + ".db"
        for comment in comments:
            save_comment_to_db(comment, post_id=None, db_filename=db_filename)

    elif mode == "csv":
        comments_csv = (
            filename
            if filename.endswith("_comments.csv")
            else filename + "_comments.csv"
        )

        all_comments = []
        comment_id_counter = 1  # mimic autoincrement ids
        today = date.today().strftime("%Y-%m-%d")
        for comment in comments:
            # Collect comment info with an ID
            comment_row = {
                "id": comment_id_counter,
                "game_id": comment.get("game_id"),
                "author": comment["author"],
                "text": format_reddit_text(comment["text"]),
                "created_est": utility.utc_to_est(comment["created_utc"]),
                "save_date": today,
            }
            all_comments.append(comment_row)
            comment_id_counter += 1

        # Write CSV
        pd.DataFrame(all_comments).to_csv(comments_csv, index=False, encoding="utf-8")
        print(f"Exported comments to CSV: {comments_csv}")

    else:
        raise ValueError("Mode must be either 'db' or 'csv'")


def save_reddit_posts(posts, limit=5, filename: str = "MyDatabase", mode: str = "db"):
    """
    Save multiple Reddit posts to either a DB or CSV.

    Args:
        posts (list): A list of dictionaries (from fetch_reddit_posts).
        limit (int): Number of top-level comments to save per post.
        filename (str): Base filename (extension auto-added).
        mode (str): 'db' (SQLite) or 'csv' (flat files).
    """
    if mode == "db":
        db_filename = filename if filename.endswith(".db") else filename + ".db"
        for post in posts:
            save_post_to_db(post, limit=limit, db_filename=db_filename)

    elif mode == "csv":
        posts_csv = (
            filename if filename.endswith("_posts.csv") else filename + "_posts.csv"
        )

        all_posts = []
        post_id_counter = 1  # mimic autoincrement ids
        today = date.today().strftime("%Y-%m-%d")
        for post in posts:
            # Collect post info with an ID
            post_row = {
                "id": post_id_counter,
                "game_id": post["game_id"],
                "team_acronym": post["team_acronym"].upper(),
                "post_title": post["title"],
                "post_url": post["url"],
                "created_est": post["created_est"],
                "save_date": today,
            }
            all_posts.append(post_row)
            post_id_counter += 1

        # Write both CSVs
        pd.DataFrame(all_posts).to_csv(posts_csv, index=False, encoding="utf-8")
        print(f"Exported posts to CSV: {posts_csv}")

    else:
        raise ValueError("Mode must be either 'db' or 'csv'")


def save_comment_to_db(comment, post_id, db_filename: str = "MyDatabase.db"):
    """
    Save a single Reddit comment to the SQLite database.
    """
    conn = get_connection(db_filename)
    cursor = conn.cursor()
    today = date.today().strftime("%Y-%m-%d")
    # Create comments table if not exist
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            game_id INTEGER,
            author TEXT,
            text TEXT,
            created_est TEXT,
            save_date TEXT,
            FOREIGN KEY (post_id) REFERENCES posts (id),
            UNIQUE(author, created_est, save_date)
        )
        """
    )
    conn.commit()

    # Insert comment
    cursor.execute(
        """
        INSERT OR IGNORE INTO comments (post_id, game_id, author, text, created_est, save_date)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            post_id,
            comment.get("game_id"),
            comment["author"],
            comment["author"],
            comment["text"],
            utility.utc_to_est(comment["created_utc"]),
            today,
        ),
    )

    conn.commit()
    conn.close()
    print(f"Saved comment by '{comment.get('author')}' to database ({db_filename}).")


def save_post_to_db(post, limit=5, db_filename: str = "MyDatabase.db"):
    """
    Save a Reddit post to the SQLite database.
    """
    conn = get_connection(db_filename)
    cursor = conn.cursor()
    today = date.today().strftime("%Y-%m-%d")
    # Create tables if not exist
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER,
            team_acronym TEXT,
            post_title TEXT,
            post_url TEXT,
            created_est TEXT,
            save_date TEXT
        ) 
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            game_id INTEGER,
            author TEXT,
            text TEXT,
            created_est TEXT,
            save_date TEXT,
            FOREIGN KEY (post_id) REFERENCES posts (id),
            UNIQUE(author, created_est, save_date)
        )
        """
    )
    conn.commit()

    # Insert post if new
    cursor.execute("SELECT id FROM posts WHERE post_url = ?", (post["url"],))
    result = cursor.fetchone()
    if result:
        post_id = result[0]
    else:
        cursor.execute(
            """
            INSERT INTO posts (team_acronym, post_title, post_url, created_est, save_date, game_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                post["team_acronym"].upper(),
                post["title"],
                post["url"],
                post["created_est"],
                today,
            ),
        )
        post_id = cursor.lastrowid

    conn.commit()
    conn.close()
    print(f"Saved post '{post.get('title')}'")
