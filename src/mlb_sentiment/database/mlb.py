import sqlite3
import os
import pandas as pd
import csv
from datetime import date


def get_connection(db_filename: str = "MyDatabase.db"):
    conn = sqlite3.connect(db_filename, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def save_mlb_games(games, filename: str = "MyDatabase", mode: str = "db"):
    """
    Save MLB game data to either a SQLite database (.db) or a CSV file (.csv).

    Parameters
    ----------
    games : list of dicts
        Each dict represents one game's data.
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

        # Create the games table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER,
                home_team TEXT,
                away_team TEXT,
                game_date TEXT,
                venue TEXT,
                UNIQUE(game_id)
            )
            """
        )

        # Insert game data into the table
        for game in games:
            cursor.execute(
                """
                INSERT OR IGNORE INTO games (
                    game_id, home_team, away_team, game_date, venue
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    game["game_id"],
                    game["home_team"],
                    game["away_team"],
                    game["game_date"],
                    game["venue"],
                ),
            )

        conn.commit()
        conn.close()
        print(f"Saved {len(games)} games into database: {db_filename}")

    elif mode == "csv":
        csv_filename = filename if filename.endswith(".csv") else filename + ".csv"
        if ".db" in csv_filename:
            csv_filename = csv_filename.replace(".db", "")

        # Convert to DataFrame for easy CSV export
        df = pd.DataFrame(games)

        # Replace commas in all string columns with "..."
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace(",", "...")

        df.to_csv(csv_filename, index=False, encoding="utf-8")
        print(f"Saved {len(games)} games into CSV: {csv_filename}")

    else:
        raise ValueError("Mode must be either 'db' or 'csv'")

    return True


def save_mlb_events(game_events, filename: str = "MyDatabase", mode: str = "db"):
    """
    Save game events to either a SQLite database (.db) or a CSV file (.csv),
    and append today's date to each row.

    Parameters
    ----------
    game_events : list of tuples
        Each tuple represents one row of game data
        (inning, halfInning, event, description, est, home_team, visiting_team,
         home_score, away_score, outs, people_on_base, captivatingIndex).
    filename : str
        Base filename (no extension needed, .db or .csv is added automatically).
    mode : str
        "db"  -> save into SQLite database
        "csv" -> save directly into CSV
    """

    # Add today's date to each row
    today = date.today().strftime("%Y-%m-%d")
    events_with_date = [row + (today,) for row in game_events]

    if mode == "db":
        db_filename = filename if filename.endswith(".db") else filename + ".db"
        conn = get_connection(db_filename)
        cursor = conn.cursor()

        # Create the game data table with save_date column
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
                game_id INTEGER,
                save_date TEXT,
                UNIQUE(inning, halfInning, event, est, home_team, visiting_team,
                       home_score, away_score, outs, people_on_base, captivatingIndex, game_id, save_date)
            )
            """
        )

        # Insert game data into the table
        cursor.executemany(
            """
            INSERT OR IGNORE INTO games (
                inning, halfInning, event, description, est, home_team,
                visiting_team, home_score, away_score, outs,
                people_on_base, captivatingIndex, game_id, save_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            events_with_date,
        )

        conn.commit()
        conn.close()
        print(f"Saved {len(events_with_date)} events into database: {db_filename}")

    elif mode == "csv":
        csv_filename = filename if filename.endswith(".csv") else filename + ".csv"
        if ".db" in csv_filename:
            csv_filename = csv_filename.replace(".db", "")

        # Convert to DataFrame for easy CSV export
        df = pd.DataFrame(
            events_with_date,
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
                "game_id",
                "save_date",
            ],
        )

        # Replace commas in all string columns with "..."
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace(",", "...")

        df.to_csv(csv_filename, index=False, encoding="utf-8")
        print(f"Saved {len(events_with_date)} events into CSV: {csv_filename}")

    else:
        raise ValueError("Mode must be either 'db' or 'csv'")

    return True
