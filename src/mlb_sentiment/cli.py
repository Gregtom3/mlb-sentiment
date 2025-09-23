import click
import os
from datetime import datetime, timedelta

from mlb_sentiment.fetch.reddit import fetch_reddit_posts, fetch_reddit_comments
from mlb_sentiment.database.reddit import save_reddit_posts, save_reddit_comments
from mlb_sentiment.fetch.mlb import fetch_mlb_events, fetch_mlb_games
from mlb_sentiment.database.mlb import save_mlb_events, save_mlb_games
from mlb_sentiment.utility import upload_to_azure_blob
from mlb_sentiment.models.process import get_model_from_string


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
    help="Output filename.",
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
@click.option(
    "--sentiment-model",
    default="null",
    show_default=True,
    type=click.Choice(
        ["vader", "distilbert-base-uncased-finetuned-sst-2-english", "null"]
    ),
    help="Sentiment analysis model to use for Reddit comments.",
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
    sentiment_model,
):
    """
    Fetch and save BOTH Reddit game threads and MLB events for a given team/date or range.
    """
    # Handle yesterday flag
    if yesterday:
        date = (datetime.now() - timedelta(days=1)).strftime("")
    save_date = datetime.now().strftime("%m/%d/%Y")

    # --------------------------
    # Pretty options summary
    # --------------------------
    click.echo("=" * 60)
    click.echo(" MLB Sentiment Data Uploader ".center(60, "="))
    click.echo("=" * 60)
    click.echo(f"{'Team:':20} {team_acronym}")
    if date:
        click.echo(f"{'Date:':20} {date}")
    if start_date and end_date:
        click.echo(f"{'Date Range:':20} {start_date} → {end_date}")
    click.echo(f"{'Comments Limit:':20} {comments_limit}")
    click.echo(f"{'Output File:':20} {filename}")
    click.echo(f"{'Azure Upload:':20} {'Yes' if azure else 'No'}")
    if azure:
        click.echo(f"{'Keep Local Copy:':20} {'Yes' if keep_local else 'No'}")
    click.echo(f"{'Sentiment Model:':20} {sentiment_model}")
    click.echo(f"{'Save Date:':20} {save_date}")
    click.echo("=" * 60 + "\n")
    # --------------------------
    # Fetch Reddit posts
    # --------------------------
    if date:
        posts = fetch_reddit_posts(team_acronym, date=date)
        comments = fetch_reddit_comments(posts, limit=comments_limit)
        games = fetch_mlb_games(team_acronym, date=date)
        game_events = fetch_mlb_events(team_acronym, date=date)

    elif start_date and end_date:
        posts = fetch_reddit_posts(
            team_acronym,
            start_date=start_date,
            end_date=end_date,
            sentiment_model=get_model_from_string(sentiment_model),
        )
        games = fetch_mlb_games(team_acronym, start_date=start_date, end_date=end_date)
        game_events = fetch_mlb_events(
            team_acronym, start_date=start_date, end_date=end_date
        )
        comments = fetch_reddit_comments(posts, limit=comments_limit)

    else:
        click.echo(
            "You must provide either --date or both --start-date and --end-date."
        )
        return

    # Save locally
    save_reddit_posts(posts, limit=comments_limit, filename=filename)
    save_reddit_comments(comments, limit=comments_limit, filename=filename)
    save_mlb_events(game_events, filename=filename)
    save_mlb_games(games, filename=filename)
    # --------------------------
    # Optional Azure upload
    # --------------------------
    if azure:
        # Reddit
        reddit_blob = create_blob_name("reddit", team_acronym, save_date)
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
        mlb_blob = create_blob_name("mlb", team_acronym, save_date)
        upload_to_azure_blob(
            filename + "_games.csv",
            mlb_blob,
            subdirectory="passiveDatabase/games",
            remove_local=not keep_local,
        )
        upload_to_azure_blob(
            filename + "_game_events.csv",
            mlb_blob,
            subdirectory="passiveDatabase/gameEvents",
            remove_local=not keep_local,
        )
        click.echo(f"\t MLB blob name: {mlb_blob}")


# --------------------------
# Helpers
# --------------------------
def create_blob_name(prefix, team_acronym, save_date):
    blob_name = f"{prefix}_{team_acronym}_saved={save_date}.csv".replace("/", "-")
    if blob_name.endswith("_.csv"):
        blob_name = blob_name.replace("_.csv", ".csv")
    return blob_name


if __name__ == "__main__":
    cli()
