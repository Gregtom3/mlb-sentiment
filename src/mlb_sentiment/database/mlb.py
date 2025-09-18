import sqlite3
import os
import pandas as pd


def get_connection(db_filename: str = "MyDatabase.db"):
    conn = sqlite3.connect(db_filename, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def save_game_events_to_db(
    game_events, db_filename: str = "MyDatabase.db", as_csv: bool = False
):

    conn = get_connection(db_filename)
    cursor = conn.cursor()

    # Create the game data table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inning INTEGER,
            halfInning TEXT,
            event TEXT,
            description TEXT,
            est TEXT,
            home_team TEXT,
            visiting_team TEXT,
            UNIQUE(inning, halfInning, event, est, home_team, visiting_team)
        )
        """
    )

    # Insert game data into the table
    cursor.executemany(
        """
        INSERT OR IGNORE INTO games (inning, halfInning, event, description, est, home_team, visiting_team)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        game_events,
    )

    conn.commit()
    conn.close()
    print(f"Saved {len(game_events)} game events to the database ({db_filename}).")

    # Optionally export to CSV
    if as_csv:
        # Derive csv filename from db_filename
        base, ext = os.path.splitext(db_filename)
        csv_filename = base + (".csv" if ext.lower() != ".csv" else "")
        if not csv_filename.lower().endswith(".csv"):
            csv_filename = csv_filename + ".csv"
        # Read the games table into a DataFrame and write to CSV
        conn = sqlite3.connect(db_filename)
        try:
            df = pd.read_sql_query("SELECT * FROM games", conn)
            df.to_csv(csv_filename, index=False)
            print(f"Exported games table to CSV: {csv_filename}")
        finally:
            conn.close()
    return True
