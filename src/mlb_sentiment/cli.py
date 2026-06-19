import os
import click
from datetime import datetime, timedelta

from mlb_sentiment.fetch.reddit import fetch_reddit_posts, fetch_reddit_comments
from mlb_sentiment.database.reddit import save_reddit_posts, save_reddit_comments
from mlb_sentiment.fetch.mlb import fetch_mlb_events, fetch_mlb_games
from mlb_sentiment.database.mlb import save_mlb_events, save_mlb_games
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
    help="Max number of Reddit comments to save (0 = all).",
)
@click.option(
    "--yesterday",
    is_flag=True,
    help="Shortcut: set --date to one day before current date.",
)
@click.option(
    "--data-dir",
    default="data",
    show_default=True,
    help="Root directory for per-team Parquet output.",
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
    yesterday,
    data_dir,
    sentiment_model,
):
    """
    Fetch Reddit game threads and MLB events for a team/date and write Parquet
    to ``<data-dir>/<TEAM>/``. The static-site build (``pipeline/build_site_data``)
    reads these files; no external storage is required.
    """
    if yesterday:
        date = (datetime.now() - timedelta(days=1)).strftime("%m/%d/%Y")
    if not date:
        click.echo("You must provide --date (or use --yesterday).")
        return

    out_dir = os.path.join(data_dir, team_acronym)
    os.makedirs(out_dir, exist_ok=True)
    date_tag = datetime.strptime(date, "%m/%d/%Y").strftime("%Y-%m-%d")
    base = os.path.join(out_dir, f"{team_acronym}_{date_tag}")

    # --------------------------
    # Options summary
    # --------------------------
    limit_display = (
        f"{comments_limit}" if comments_limit > 0 else f"{comments_limit} (ALL)"
    )
    click.echo("=" * 60)
    click.echo(" MLB Sentiment Data Fetcher ".center(60, "="))
    click.echo("=" * 60)
    click.echo(f"{'Team:':20} {team_acronym}")
    click.echo(f"{'Date:':20} {date}")
    click.echo(f"{'Comments Limit:':20} {limit_display}")
    click.echo(f"{'Output Prefix:':20} {base}")
    click.echo(f"{'Sentiment Model:':20} {sentiment_model}")
    click.echo("=" * 60 + "\n")

    # --------------------------
    # Fetch
    # --------------------------
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

    # --------------------------
    # Save Parquet
    # --------------------------
    save_reddit_posts(posts, filename=base)
    save_reddit_comments(comments, filename=base)
    save_mlb_events(game_events, filename=base)
    save_mlb_games(games, filename=base)
    click.echo(f"\nWrote Parquet for {team_acronym} {date_tag} to {out_dir}/")


if __name__ == "__main__":
    cli()
