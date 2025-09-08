from mlb_sentiment.fetch.reddit import fetch_team_game_threads
from mlb_sentiment.db import save_post_to_db
from mlb_sentiment.models.dataloader import load_comments_text
from mlb_sentiment.models.analysis import calculate_mean_comment_length


def fetch_and_save_team_game_threads(team_acronym, limit=10, comments_limit=5):
    """
    Fetches team game threads and saves them to the database.

    Args:
        team_acronym (str): Acronym of the MLB team (e.g., "NYM" for New York Mets).
        limit (int): The maximum number of posts to fetch.
        comments_limit (int): The maximum number of top-level comments to save for each post.
    """
    posts = fetch_team_game_threads(team_acronym, limit=limit)
    for post in posts:
        save_post_to_db(post, limit=comments_limit)


def analyze_comment_length():
    """
    Analyzes the average length of comments in the database.

    Returns:
        float: The average length of comments, or 0 if no comments are found.
    """
    comments = load_comments_text()
    return calculate_mean_comment_length(comments)
