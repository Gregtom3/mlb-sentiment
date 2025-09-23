import pandas as pd
from datetime import date


def save_mlb_games(games, filename: str = "MyDatabase"):
    """
    Save MLB game data to a CSV file (.csv).

    Parameters
    ----------
    games : list of dicts
        Each dict represents one game's data.
    filename : str
        Base filename (no extension needed, .csv is added automatically).
    """
    csv_filename = (
        filename if filename.endswith("_games.csv") else filename + "_games.csv"
    )
    if ".db" in csv_filename:
        csv_filename = csv_filename.replace(".db", "")

    # Convert to DataFrame for easy CSV export
    df = pd.DataFrame(
        games,
        columns=[
            "game_id",
            "home_team",
            "away_team",
            "home_score",
            "away_score",
            "wins",
            "losses",
        ],
    )

    # Replace commas in all string columns with "..."
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.replace(",", "...")

    df.to_csv(csv_filename, index=False, encoding="utf-8")
    print(f"Saved {len(games)} games into CSV: {csv_filename}")
    return True


def save_mlb_events(game_events, filename: str = "MyDatabase"):
    """
    Save game events to a CSV file (.csv), and append today's date to each row.

    Parameters
    ----------
    game_events : list of tuples
        Each tuple represents one row of game data
        (inning, halfInning, event, description, est, home_team, visiting_team,
         home_score, away_score, outs, people_on_base, captivatingIndex).
    filename : str
        Base filename (no extension needed, .csv is added automatically).
    """
    # Add today's date to each row
    today = date.today().strftime("%Y-%m-%d")
    events_with_date = [row + (today,) for row in game_events]

    csv_filename = (
        filename
        if filename.endswith("_game_events.csv")
        else filename + "_game_events.csv"
    )
    if ".db" in csv_filename:
        csv_filename = csv_filename.replace(".db", "")

    # Convert to DataFrame for easy CSV export
    df = pd.DataFrame(
        events_with_date,
        columns=[
            "game_id",
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
            "save_date",
        ],
    )

    # Replace commas in all string columns with "..."
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.replace(",", "...")

    df.to_csv(csv_filename, index=False, encoding="utf-8")
    print(f"Saved {len(events_with_date)} events into CSV: {csv_filename}")
    return True
