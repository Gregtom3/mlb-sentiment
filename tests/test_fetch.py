import pytest
from mlb_sentiment.fetch.reddit import fetch_reddit_comments, fetch_reddit_posts
from mlb_sentiment.fetch.mlb import fetch_mlb_events, fetch_mlb_games


def test_fetch_reddit_posts_sample():
    team_acronym = "NYM"
    date = "09/14/2025"
    posts = fetch_reddit_posts(team_acronym, date=date)
    assert isinstance(posts, list)
    if posts:
        assert "title" in posts[0]
        assert "game_id" in posts[0]


def test_fetch_reddit_comments_sample():
    team_acronym = "NYM"
    date = "09/14/2025"
    posts = fetch_reddit_posts(team_acronym, date=date)
    comments = fetch_reddit_comments(posts, limit=2)
    assert isinstance(comments, list)
    if comments:
        assert "author" in comments[0]
        assert "game_id" in comments[0]


def test_fetch_mlb_events_sample():
    team_acronym = "NYM"
    date = "09/14/2025"
    events = fetch_mlb_events(team_acronym, date=date)
    assert isinstance(events, list)
    if events:
        assert len(events[0]) > 0


def test_fetch_mlb_games_sample():
    team_acronym = "NYM"
    date = "09/14/2025"
    games = fetch_mlb_games(team_acronym, date=date)
    assert isinstance(games, list)
    if games:
        assert len(games[0]) > 0
