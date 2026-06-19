from mlb_sentiment.info import SUBREDDIT_INFO, get_team_info
from mlb_sentiment.config import load_reddit_client


def test_subreddit_info_shape():
    """Every team needs a valid subreddit URL; the bot user is optional."""
    for team_acronym in SUBREDDIT_INFO:
        subreddit = get_team_info(team_acronym, "subreddit")
        assert subreddit.startswith("https://www.reddit.com/r/")
        user = get_team_info(team_acronym, "game_thread_user")
        assert user is None or (isinstance(user, str) and len(user) > 0)


def test_subreddit_and_users_exist_on_reddit():
    """Each subreddit (and any configured bot) must resolve on Reddit."""
    reddit = load_reddit_client()
    for team_acronym, meta in SUBREDDIT_INFO.items():
        subreddit_name = meta["subreddit"].split("/r/")[1].strip("/")
        _ = reddit.subreddit(subreddit_name).id  # raises if missing
        user = meta.get("game_thread_user")
        if user:
            _ = reddit.redditor(user).id  # raises if missing
