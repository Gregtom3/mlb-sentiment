import os

USE_DELTA = os.environ.get("USE_DELTA", "false").lower() in ("1", "true", "yes")


def save_game_to_db(game):
    """Save game events. On Databricks (or when USE_DELTA is set) this will write
    to a Delta path using the Spark adapter. Otherwise it falls back to the
    existing local SQLite database to preserve current behavior.
    """
    if USE_DELTA:
        try:
            from .adapter import save_game_to_delta

            path = os.environ.get("GAME_TABLE_PATH")
            save_game_to_delta(game, path=path)
            print(f"Saved {len(game)} game events to Delta at {path or 'default path'}.")
            return True
        except Exception as e:
            # If the Delta path write fails, surface the error so callers can
            # decide how to proceed. Don't silently fall back to SQLite.
            raise

    # Fallback: local SQLite for development / CI
    import sqlite3


    def get_connection():
        conn = sqlite3.connect("MyDatabase.db", timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn


    conn = get_connection()
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
        game,
    )

    conn.commit()
    conn.close()
    print(f"Saved {len(game)} game events to the database.")
    return True
