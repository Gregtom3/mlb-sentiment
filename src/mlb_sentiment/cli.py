import click
import os
from mlb_sentiment.fetch.reddit import fetch_team_game_threads
from mlb_sentiment.database.reddit import save_posts
from mlb_sentiment.fetch.mlb import fetch_mlb_events
from mlb_sentiment.database.mlb import save_game_events

# from mlb_sentiment.models.analysis import run_sentiment_analysis
from mlb_sentiment.config import load_azure_client
from mlb_sentiment.utility import upload_to_azure_blob
import tempfile, json
from tqdm import tqdm


@click.group()
def cli():
    """A CLI for fetching and analyzing MLB game threads."""
    pass


@cli.command()
@click.option(
    "--team-acronym",
    required=True,
    help="The team acronym (e.g., NYY for New York Yankees).",
)
@click.option(
    "--date", default=None, help="The date of the posts to fetch (MM/DD/YYYY)."
)
@click.option("--start-date", default=None, help="Start date for range (MM/DD/YYYY).")
@click.option("--end-date", default=None, help="End date for range (MM/DD/YYYY).")
@click.option(
    "--comments-limit", default=5, help="The maximum number of comments to save."
)
@click.option(
    "--filename",
    default="MyDatabase.csv",
    show_default=True,
    help="The SQLite database filename to save data to.",
)
@click.option(
    "--azure", is_flag=True, help="Upload to Azure Blob Storage instead of local DB."
)
def upload_reddit(
    team_acronym, date, start_date, end_date, comments_limit, filename, azure
):
    """Fetches and saves MLB game threads for a given team, by date or date range."""
    # Infer mode from file extension
    mode = "csv" if filename.endswith(".csv") else "db"
    if date:
        posts = fetch_team_game_threads(team_acronym, date=date)
    elif start_date and end_date:
        posts = fetch_team_game_threads(
            team_acronym, start_date=start_date, end_date=end_date
        )
    else:
        click.echo(
            "You must provide either --date or both --start-date and --end-date."
        )
        return

    save_posts(posts, limit=comments_limit, filename=filename, mode=mode)
    if azure:
        blob_name = f"reddit_{team_acronym}_{date or start_date}_{end_date or ''}.{mode}".replace(
            "/", "-"
        )
        upload_to_azure_blob(filename, blob_name)
        click.echo(f"\t Blob name: {blob_name}")


@cli.command()
@click.option(
    "--team-acronym",
    required=True,
    help="The team acronym (e.g., NYY for New York Yankees).",
)
@click.option("--date", default=None, help="The date of the game (MM/DD/YYYY).")
@click.option("--start-date", default=None, help="Start date for range (MM/DD/YYYY).")
@click.option("--end-date", default=None, help="End date for range (MM/DD/YYYY).")
@click.option(
    "--azure", is_flag=True, help="Upload to Azure Blob Storage instead of local DB."
)
@click.option(
    "--filename",
    default="MyDatabase.csv",
    show_default=True,
    help="The SQLite database filename to save data to.",
)
def upload_mlb(team_acronym, date, start_date, end_date, filename, azure):
    """Fetches and saves MLB events for a given team and date or date range."""
    # Infer mode from file extension
    mode = "csv" if filename.endswith(".csv") else "db"
    if date:
        game_events = fetch_mlb_events(team_acronym, date=date)
    elif start_date and end_date:
        game_events = fetch_mlb_events(
            team_acronym, start_date=start_date, end_date=end_date
        )
    else:
        click.echo(
            "You must provide either --date or both --start-date and --end-date."
        )
        return
    # Save events to the database
    save_game_events(game_events, filename=filename, mode=mode)
    if azure:
        blob_name = (
            f"mlb_{team_acronym}_{date or start_date}_{end_date or ''}.{mode}".replace(
                "/", "-"
            )
        )
        upload_to_azure_blob(filename, blob_name)
        click.echo(f"\t Blob name: {blob_name}")


@cli.command()
def analyze():
    """Analyzes the sentiment of the saved game threads."""
    # run_sentiment_analysis()
    click.echo("Sentiment analysis completed.")


# Remove the as_csv parameter from the function
def correct_filename_extension(filename):
    if filename.endswith(".csv"):
        if filename.endswith(".db.csv"):
            filename = filename.replace(".db", "")
    elif not filename.endswith(".db"):
        filename += ".db"
        if filename.endswith(".csv.db"):
            filename = filename.replace(".csv", "")
    return filename


if __name__ == "__main__":
    cli()
