import pytest
from mlb_sentiment.info import SUBREDDIT_INFO, get_team_info
from mlb_sentiment.config import load_reddit_client


def test_subreddit_info():
    """Verify that all teams in SUBREDDIT_INFO have valid subreddit and game_thread_user."""
    for team_acronym, info in SUBREDDIT_INFO.items():
        subreddit = get_team_info(team_acronym, "subreddit")
        game_thread_user = get_team_info(team_acronym, "game_thread_user")
        assert subreddit.startswith("https://www.reddit.com/r/")
        assert isinstance(game_thread_user, str) and len(game_thread_user) > 0

    # Verify user and subreddit exist on Reddit
    reddit = load_reddit_client()
    for team_acronym, info in SUBREDDIT_INFO.items():
        game_thread_user = info["game_thread_user"]
        subreddit_url = info["subreddit"]
        user = reddit.redditor(game_thread_user)
        _ = user.id  # Trigger fetch to verify user exists
        subreddit_name = subreddit_url.split("/r/")[1].strip("/")
        subreddit = reddit.subreddit(subreddit_name)
        _ = subreddit.id  # Trigger fetch to verify subreddit exists
