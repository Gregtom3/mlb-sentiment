import click
from mlb_sentiment.fetch.reddit import fetch_team_game_threads
from mlb_sentiment.database.reddit import save_post_to_db
from mlb_sentiment.models.analysis import run_sentiment_analysis
from tqdm import tqdm


@click.group()
def cli():
    """A CLI for fetching and analyzing MLB game threads."""
    pass


@cli.command()
@click.argument("team_acronym", type=str)
@click.option(
    "--post-date", default=None, help="The date of the posts to fetch (MM/DD/YYYY)."
)
@click.option("--start-date", default=None, help="Start date for range (MM/DD/YYYY).")
@click.option("--end-date", default=None, help="End date for range (MM/DD/YYYY).")
@click.option(
    "--comments-limit", default=5, help="The maximum number of comments to save."
)
def fetch(team_acronym, post_date, start_date, end_date, comments_limit):
    """Fetches and saves MLB game threads for a given team, by date or date range."""
    if post_date:
        posts = fetch_team_game_threads(team_acronym, date=post_date)
    elif start_date and end_date:
        posts = fetch_team_game_threads(
            team_acronym, start_date=start_date, end_date=end_date
        )
    else:
        click.echo(
            "You must provide either --post-date or both --start-date and --end-date."
        )
        return
    for post in tqdm(posts, desc="Saving posts to DB"):
        save_post_to_db(post, limit=comments_limit)
    click.echo(f"Successfully fetched and saved game threads for {team_acronym}.")


@cli.command()
def analyze():
    """Analyzes the sentiment of the saved game threads."""
    run_sentiment_analysis()
    click.echo("Sentiment analysis completed.")


if __name__ == "__main__":
    cli()
