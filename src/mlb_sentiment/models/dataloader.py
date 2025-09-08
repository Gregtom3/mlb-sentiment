import sqlite3
import os


def load_comments():
    """
    Loads all comments from the database.

    Returns:
        list: A list of strings, where each string is the text of a comment.
    """
    data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")
    db_path = os.path.join(data_dir, "reddit.db")

    if not os.path.exists(db_path):
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM comments")
    comments = cursor.fetchall()
    conn.close()

    return comments
