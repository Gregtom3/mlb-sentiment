import pandas as pd
from datetime import date


def save_mlb_games(games, filename: str = "MyDatabase"):
    """
    Save MLB game data to a Parquet file (.parquet).

    Parameters
    ----------
    games : list of dicts
        Each dict represents one game's data.
    filename : str
        Base filename (no extension needed, .parquet is added automatically).
    """
    parquet_filename = (
        filename if filename.endswith("_games.parquet") else filename + "_games.parquet"
    )

    # Convert to DataFrame for easy export
    df = pd.DataFrame(
        games,
        columns=[
            "game_id",
            "game_date",
            "game_start_time_est",
            "home_team",
            "away_team",
            "home_score",
            "away_score",
            "wins",
            "losses",
        ],
    )

    # Replace commas in string columns with "..."
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.replace(",", "...")

    df.to_parquet(parquet_filename, index=False, engine="pyarrow")
    print(f"Saved {len(games)} games into Parquet: {parquet_filename}")
    return True


def save_mlb_events(game_events, filename: str = "MyDatabase"):
    """
    Save game events to a Parquet file (.parquet).

    Parameters
    ----------
    game_events : list of tuples
        Each tuple represents one row of game data
        (inning, halfInning, event, description, est, home_team, visiting_team,
         home_score, away_score, outs, people_on_base, captivatingIndex).
    filename : str
        Base filename (no extension needed, .parquet is added automatically).
    """
    parquet_filename = (
        filename
        if filename.endswith("_game_events.parquet")
        else filename + "_game_events.parquet"
    )

    # Convert to DataFrame for easy export
    df = pd.DataFrame(
        game_events,
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
        ],
    )

    # Add an autoincrementing event_id column
    df.index.name = "event_id"
    df.reset_index(inplace=True)

    # Replace commas in string columns with "..."
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.replace(",", "...")

    df.to_parquet(parquet_filename, index=False, engine="pyarrow")
    print(f"Saved {len(game_events)} events into Parquet: {parquet_filename}")
    return True
