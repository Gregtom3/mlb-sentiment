import sqlite3


def get_connection(db_filename: str = "MyDatabase.db"):
    conn = sqlite3.connect(db_filename, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def save_game_to_db(game, db_filename: str = "MyDatabase.db"):

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
        game,
    )

    conn.commit()
    conn.close()
    print(f"Saved {len(game)} game events to the database ({db_filename}).")
    return True
