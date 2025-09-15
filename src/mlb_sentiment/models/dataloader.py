import sqlite3
import os


def load_comments():
    """
    Loads all comments from the database.

    Returns:
        list: A list of strings, where each string is the text of a comment.
    """
    conn = sqlite3.connect("MyDatabase.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM comments")
    comments = cursor.fetchall()
    conn.close()

    return comments
