import click
import os
from datetime import datetime, timedelta

from mlb_sentiment.fetch.reddit import fetch_team_game_threads
from mlb_sentiment.database.reddit import save_posts
from mlb_sentiment.fetch.mlb import fetch_mlb_events
from mlb_sentiment.database.mlb import save_game_events
from mlb_sentiment.utility import upload_to_azure_blob


@click.group()
def cli():
    """A CLI for fetching and analyzing MLB data (Reddit + MLB API)."""
    pass


@cli.command()
@click.option(
    "--team-acronym",
    required=True,
    help="The team acronym (e.g., NYY for New York Yankees).",
)
@click.option("--date", default=None, help="The date to fetch (MM/DD/YYYY).")
@click.option("--start-date", default=None, help="Start date for range (MM/DD/YYYY).")
@click.option("--end-date", default=None, help="End date for range (MM/DD/YYYY).")
@click.option(
    "--comments-limit",
    default=5,
    show_default=True,
    help="Max number of Reddit comments to save.",
)
@click.option(
    "--filename",
    default="MyDatabase.csv",
    show_default=True,
    help="Output filename (extension determines mode: .csv or .db).",
)
@click.option(
    "--azure",
    is_flag=True,
    help="Upload results to Azure Blob Storage instead of only local.",
)
@click.option(
    "--keep-local", is_flag=True, help="Keep local file after uploading to Azure."
)
@click.option(
    "--yesterday",
    is_flag=True,
    help="Shortcut: set --date to one day before current date.",
)
def upload(
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
    """
    Fetch and save BOTH Reddit game threads and MLB events for a given team/date or range.
    """
    # Handle yesterday flag
    if yesterday:
        date = (datetime.now() - timedelta(days=1)).strftime("%m/%d/%Y")
    save_date = datetime.now().strftime("%Y-%m-%d")

    # Infer mode
    mode = "csv" if filename.endswith(".csv") else "db"

    # --------------------------
    # Fetch Reddit posts
    # --------------------------
    if date:
        posts = fetch_team_game_threads(team_acronym, date=date)
        game_events = fetch_mlb_events(team_acronym, date=date)
    elif start_date and end_date:
        posts = fetch_team_game_threads(
            team_acronym, start_date=start_date, end_date=end_date
        )
        game_events = fetch_mlb_events(
            team_acronym, start_date=start_date, end_date=end_date
        )
    else:
        click.echo(
            "You must provide either --date or both --start-date and --end-date."
        )
        return

    # Save locally
    save_posts(posts, limit=comments_limit, filename=filename, mode=mode)
    save_game_events(game_events, filename=filename, mode=mode)

    # --------------------------
    # Optional Azure upload
    # --------------------------
    if azure:
        if mode != "csv":
            raise ValueError("Azure upload is only supported for CSV mode.")

        # Reddit
        reddit_blob = create_blob_name("reddit", team_acronym, mode, save_date)
        upload_to_azure_blob(
            filename + "_comments.csv",
            reddit_blob,
            subdirectory="passiveDatabase/comments",
            remove_local=not keep_local,
        )
        upload_to_azure_blob(
            filename + "_posts.csv",
            reddit_blob,
            subdirectory="passiveDatabase/posts",
            remove_local=not keep_local,
        )
        click.echo(
            f"\t Reddit blob names: "
            f"{reddit_blob.replace('.csv', '_comments.csv')}, "
            f"{reddit_blob.replace('.csv', '_posts.csv')}"
        )

        # MLB
        mlb_blob = create_blob_name("mlb", team_acronym, mode, save_date)
        upload_to_azure_blob(
            filename,
            mlb_blob,
            subdirectory="passiveDatabase/mlb",
            remove_local=not keep_local,
        )
        click.echo(f"\t MLB blob name: {mlb_blob}")


@cli.command()
def analyze():
    """Analyzes the sentiment of the saved game threads."""
    click.echo("Sentiment analysis completed.")


# --------------------------
# Helpers
# --------------------------
def create_blob_name(prefix, team_acronym, extension, save_date):
    blob_name = f"{prefix}_{team_acronym}_saved={save_date}.{extension}".replace(
        "/", "-"
    )
    if blob_name.endswith("_.csv"):
        blob_name = blob_name.replace("_.csv", ".csv")
    elif blob_name.endswith("_.db"):
        blob_name = blob_name.replace("_.db", ".db")
    return blob_name


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
