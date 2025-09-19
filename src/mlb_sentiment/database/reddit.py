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


def save_posts(posts, limit=5, filename: str = "MyDatabase", mode: str = "db"):
    """
    Save multiple Reddit posts and their top-level comments to either a DB or CSV.

    Args:
        posts (list): A list of dictionaries (from fetch_team_game_threads).
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
        comments_csv = (
            filename
            if filename.endswith("_comments.csv")
            else filename + "_comments.csv"
        )

        all_posts = []
        all_comments = []
        post_id_counter = 1  # mimic autoincrement ids

        for post in posts:
            # Collect post info with an ID
            post_row = {
                "id": post_id_counter,
                "team_acronym": post["team_acronym"].upper(),
                "post_title": post["title"],
                "post_url": post["url"],
                "created_est": post["created_est"],
            }
            all_posts.append(post_row)

            # Fetch and collect comments
            comments = fetch_post_comments(post["url"], limit=limit)
            for c in comments:
                all_comments.append(
                    {
                        "id": None,  # will be auto-assigned if DB, leave None in CSV
                        "post_id": post_id_counter,
                        "author": c["author"],
                        "text": format_reddit_text(c["text"]),
                        "created_est": utility.utc_to_est(c["created_utc"]),
                    }
                )

            post_id_counter += 1

        # Write both CSVs
        pd.DataFrame(all_posts).to_csv(posts_csv, index=False, encoding="utf-8")
        pd.DataFrame(all_comments).to_csv(comments_csv, index=False, encoding="utf-8")
        print(f"Exported posts to CSV: {posts_csv}")
        print(f"Exported comments to CSV: {comments_csv}")

    else:
        raise ValueError("Mode must be either 'db' or 'csv'")


def save_post_to_db(post, limit=5, db_filename: str = "MyDatabase.db"):
    """
    Save a Reddit post and its top-level comments to the SQLite database.
    """
    conn = get_connection(db_filename)
    cursor = conn.cursor()

    # Create tables if not exist
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

    # Insert post if new
    cursor.execute("SELECT id FROM posts WHERE post_url = ?", (post["url"],))
    result = cursor.fetchone()
    if result:
        post_id = result[0]
    else:
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
        post_id = cursor.lastrowid

    # Insert comments
    comments = fetch_post_comments(post["url"], limit=limit)
    for c in comments:
        cursor.execute(
            """
            INSERT OR IGNORE INTO comments (post_id, author, text, created_est)
            VALUES (?, ?, ?, ?)
            """,
            (post_id, c["author"], c["text"], utility.utc_to_est(c["created_utc"])),
        )

    conn.commit()
    conn.close()
    print(f"Saved post '{post.get('title')}' and comments to database ({db_filename}).")
