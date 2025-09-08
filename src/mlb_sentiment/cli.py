import click
from mlb_sentiment.api import fetch_and_save_team_game_threads

@click.group()
def cli():
    """A CLI for fetching and analyzing MLB game threads."""
    pass

@cli.command()
@click.argument("team_acronym", type=str)
@click.option("--posts-limit", default=10, help="The maximum number of posts to fetch.")
@click.option("--comments-limit", default=5, help="The maximum number of comments to save.")
def fetch(team_acronym, posts_limit, comments_limit):
    """Fetches and saves MLB game threads for a given team."""
    fetch_and_save_team_game_threads(
        team_acronym=team_acronym,
        limit=posts_limit,
        comments_limit=comments_limit,
    )
    click.echo(f"Successfully fetched and saved game threads for {team_acronym}.")

@cli.command()
def analyze():
    """Analyzes the sentiment of the saved game threads."""
    click.echo("Analysis functionality not yet implemented.")

if __name__ == "__main__":
    cli()