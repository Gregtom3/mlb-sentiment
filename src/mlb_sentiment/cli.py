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
from datetime import datetime, timedelta


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
@click.option(
    "--keep-local", is_flag=True, help="Keep local file after uploading to Azure."
)
@click.option(
    "--yesterday", is_flag=True, help="Set the date to one day before the current date."
)
def upload_reddit(
    team_acronym,
    date,
    start_date,
    end_date,
    comments_limit,
    filename,
    azure,
    keep_local,
    yesterday,
):
    """Fetches and saves MLB game threads for a given team, by date or date range."""
    if yesterday:
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    save_date = datetime.now().strftime("%Y-%m-%d")
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
        blob_name = create_blob_name("reddit", team_acronym, mode, save_date)
        if mode == "csv":
            upload_to_azure_blob(
                filename + "_comments.csv",
                subdirectory="passiveDatabase/comments",
                remove_local=not keep_local,
            )
            upload_to_azure_blob(
                filename + "_posts.csv",
                subdirectory="passiveDatabase/posts",
                remove_local=not keep_local,
            )
            click.echo(
                f"\t Blob names: {blob_name.replace('.csv', '_comments.csv')}, {blob_name.replace('.csv', '_posts.csv')}"
            )
        else:
            raise ValueError("Azure upload is only supported for CSV mode.")


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
@click.option(
    "--keep-local", is_flag=True, help="Keep local file after uploading to Azure."
)
@click.option(
    "--yesterday", is_flag=True, help="Set the date to one day before the current date."
)
def upload_mlb(
    team_acronym, date, start_date, end_date, filename, azure, keep_local, yesterday
):
    """Fetches and saves MLB events for a given team and date or date range."""
    if yesterday:
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    save_date = datetime.now().strftime("%Y-%m-%d")
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
        blob_name = create_blob_name("mlb", team_acronym, mode, save_date)
        upload_to_azure_blob(
            filename,
            blob_name,
            subdirectory="passiveDatabase/mlb",
            remove_local=not keep_local,
        )
        click.echo(f"\t Blob name: {blob_name}")


@cli.command()
def analyze():
    """Analyzes the sentiment of the saved game threads."""
    # run_sentiment_analysis()
    click.echo("Sentiment analysis completed.")


# Create blob name
def create_blob_name(prefix, team_acronym, extension, save_date):
    blob_name = f"{prefix}_{team_acronym}_saved={save_date}.{extension}".replace(
        "/", "-"
    )
    # Test if blob_name ends with something weird like "myBlob_.csv" and remove the _
    if blob_name.endswith("_.csv"):
        blob_name = blob_name.replace("_.csv", ".csv")
    elif blob_name.endswith("_.db"):
        blob_name = blob_name.replace("_.db", ".db")
    return blob_name


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
