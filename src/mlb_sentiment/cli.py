import click
from mlb_sentiment.fetch.reddit import fetch_team_game_threads
from mlb_sentiment.db import save_post_to_db
from mlb_sentiment.models.analysis import run_sentiment_analysis


@click.group()
def cli():
    """A CLI for fetching and analyzing MLB game threads."""
    pass


@cli.command()
@click.argument("team_acronym", type=str)
@click.option("--posts-limit", default=10, help="The maximum number of posts to fetch.")
@click.option(
    "--comments-limit", default=5, help="The maximum number of comments to save."
)
def fetch(team_acronym, posts_limit, comments_limit):
    """Fetches and saves MLB game threads for a given team."""
    posts = fetch_team_game_threads(team_acronym, limit=limit)
    for post in posts:
        save_post_to_db(post, limit=comments_limit)
    click.echo(f"Successfully fetched and saved game threads for {team_acronym}.")


@cli.command()
def analyze():
    """Analyzes the sentiment of the saved game threads."""
    run_sentiment_analysis()
    click.echo("Sentiment analysis completed.")


if __name__ == "__main__":
    cli()
