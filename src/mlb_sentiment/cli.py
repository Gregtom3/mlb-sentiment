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
@click.option(
    "--comments-limit",
    default=5,
    show_default=True,
    help="Max number of Reddit comments to save.",
)
@click.option(
    "--filename", default="MyDatabase.csv", show_default=True, help="Output filename."
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
        [
            "vader",
            "distilbert-base-uncased-finetuned-sst-2-english",
            "twitter-roberta-base-sentiment",
            "null",
        ]
    ),
    help="Sentiment analysis model to use for Reddit comments.",
)
def upload(
    team_acronym,
    date,
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
        date = (datetime.now() - timedelta(days=1)).strftime("%m/%d/%Y")

    # --------------------------
    # Pretty options summary
    # --------------------------
    click.echo("=" * 60)
    click.echo(" MLB Sentiment Data Uploader ".center(60, "="))
    click.echo("=" * 60)
    click.echo(f"{'Team:':20} {team_acronym}")
    if date:
        click.echo(f"{'Date:':20} {date}")
    if comments_limit > 0:
        click.echo(f"{'Comments Limit:':20} {comments_limit}")
    else:
        click.echo(f"{'Comments Limit:':20} {comments_limit} (ALL)")
    click.echo(f"{'Output File:':20} {filename}")
    click.echo(f"{'Azure Upload:':20} {'Yes' if azure else 'No'}")
    if azure:
        click.echo(f"{'Keep Local Copy:':20} {'Yes' if keep_local else 'No'}")
    click.echo(f"{'Sentiment Model:':20} {sentiment_model}")
    click.echo("=" * 60 + "\n")
    # --------------------------
    # Fetch Reddit posts
    # --------------------------
    if date:
        games = fetch_mlb_games(team_acronym, date=date)
        if not games:
            click.echo(f"No MLB games found for {team_acronym} on {date}. Exiting.")
            return
        game_events = fetch_mlb_events(team_acronym, date=date)
        posts = fetch_reddit_posts(team_acronym, date=date)
        if not posts:
            click.echo(f"No Reddit posts found for {team_acronym} on {date}. Exiting.")
            return
        comments = fetch_reddit_comments(
            posts,
            limit=comments_limit,
            sentiment_model=get_model_from_string(sentiment_model),
        )
    else:
        click.echo("You must provide --date (or use --yesterday).")
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
        year = datetime.strptime(date, "%m/%d/%Y").year
        reddit_blob = create_blob_name("reddit", team_acronym, date)
        upload_to_azure_blob(
            filename + "_comments.csv",
            reddit_blob,
            subdirectory=f"passiveDatabase/comments/{team_acronym}/year={year}",
            remove_local=not keep_local,
        )
        upload_to_azure_blob(
            filename + "_posts.csv",
            reddit_blob,
            subdirectory=f"passiveDatabase/posts/{team_acronym}/year={year}",
            remove_local=not keep_local,
        )
        click.echo(
            f"\t Reddit blob names: "
            f"{reddit_blob.replace('.csv', '_comments.csv')}, "
            f"{reddit_blob.replace('.csv', '_posts.csv')}"
        )

        # MLB
        mlb_blob = create_blob_name("mlb", team_acronym, date)
        upload_to_azure_blob(
            filename + "_games.csv",
            mlb_blob,
            subdirectory=f"passiveDatabase/games/{team_acronym}/year={year}",
            remove_local=not keep_local,
        )
        upload_to_azure_blob(
            filename + "_game_events.csv",
            mlb_blob,
            subdirectory=f"passiveDatabase/gameEvents/{team_acronym}/year={year}",
            remove_local=not keep_local,
        )
        click.echo(f"\t MLB blob name: {mlb_blob}")


# --------------------------
# Helpers
# --------------------------
def create_blob_name(prefix, team_acronym, game_date):
    blob_name = f"{prefix}_{team_acronym}_date={game_date}.csv".replace("/", "-")
    if blob_name.endswith("_.csv"):
        blob_name = blob_name.replace("_.csv", ".csv")
    return blob_name


if __name__ == "__main__":
    cli()
