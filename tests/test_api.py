from mlb_sentiment import config
import praw

def test_reddit_connection():
    reddit = config.load_reddit_client()
    assert reddit is not None
    assert isinstance(reddit, praw.Reddit)
    assert reddit.read_only is True

def test_fetch_submission():
    reddit = config.load_reddit_client()
    submission = reddit.submission(url="https://www.reddit.com/r/NewYorkMets/comments/1nb31aw/post_game_thread_the_mets_fell_to_the_reds_by_a/")
    assert submission is not None
    assert isinstance(submission, praw.models.Submission)
    assert isinstance(submission.title, str)
