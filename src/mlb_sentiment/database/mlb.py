import sqlite3


def get_connection():
    conn = sqlite3.connect("MyDatabase.db", timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def save_game_to_db(game):

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
            visiting_team TEXT
        )
        """
    )

    # Insert game data into the table
    cursor.executemany(
        """
        INSERT INTO games (inning, halfInning, event, description, est, home_team, visiting_team)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        game,
    )

    conn.commit()
    conn.close()
    print(f"Saved {len(game)} game events to the database.")
    return True
