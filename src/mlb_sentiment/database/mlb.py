import sqlite3
import os
import pandas as pd
import csv


def get_connection(db_filename: str = "MyDatabase.db"):
    conn = sqlite3.connect(db_filename, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def save_game_events(game_events, filename: str = "MyDatabase", mode: str = "db"):
    """
    Save game events to either a SQLite database (.db) or a CSV file (.csv).

    Parameters
    ----------
    game_events : list of tuples
        Each tuple represents one row of game data
        (inning, halfInning, event, description, est, home_team, visiting_team).
    filename : str
        Base filename (no extension needed, .db or .csv is added automatically).
    mode : str
        "db"  -> save into SQLite database
        "csv" -> save directly into CSV
    """

    if mode == "db":
        db_filename = filename if filename.endswith(".db") else filename + ".db"
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
                home_score INTEGER,
                away_score INTEGER,
                outs INTEGER,
                people_on_base INTEGER,
                captivatingIndex INTEGER,
                UNIQUE(inning, halfInning, event, est, home_team, visiting_team, home_score, away_score, outs, people_on_base, captivatingIndex)
            )
            """
        )

        # Insert game data into the table
        cursor.executemany(
            """
            INSERT OR IGNORE INTO games (inning, halfInning, event, description, est, home_team, visiting_team, home_score, away_score, outs, people_on_base, captivatingIndex)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            game_events,
        )

        conn.commit()
        conn.close()
        print(f"Saved {len(game_events)} events into database: {db_filename}")

    elif mode == "csv":
        csv_filename = filename if filename.endswith(".csv") else filename + ".csv"
        if ".db" in csv_filename:
            csv_filename = csv_filename.replace(".db", "")
        # Convert to DataFrame for easy CSV export
        df = pd.DataFrame(
            game_events,
            columns=[
                "inning",
                "halfInning",
                "event",
                "description",
                "est",
                "home_team",
                "visiting_team",
                "home_score",
                "away_score",
                "outs",
                "people_on_base",
                "captivatingIndex",
            ],
        )
        # Replace commas in all string columns with "..."
        for col in df.columns:
            if df[col].dtype == object:  # only apply to text fields
                df[col] = df[col].astype(str).str.replace(",", "...")
        df.to_csv(csv_filename, index=False, encoding="utf-8")
        print(f"Saved {len(game_events)} events into CSV: {csv_filename}")

    else:
        raise ValueError("Mode must be either 'db' or 'csv'")

    return True
