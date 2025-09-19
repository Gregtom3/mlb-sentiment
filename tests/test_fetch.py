import pytest
from mlb_sentiment.fetch.reddit import fetch_team_game_threads
from mlb_sentiment.fetch.mlb import fetch_mlb_events


def test_fetch_team_game_threads_nym():
    """
    Test the fetch_team_game_threads function for the "NYM" team acronym.
    """
    team_acronym = "NYM"

    # Call the function
    posts = fetch_team_game_threads(team_acronym, date="09/14/2025")

    # Assertions
    assert isinstance(posts, list), "The result should be a list."

    for post in posts:
        assert (
            "GAME THREAD" in post["title"].upper()
        ), "Each post title should contain 'GAME THREAD'."
        assert "title" in post, "Each post should have a 'title'."
        assert "url" in post, "Each post should have a 'url'."
        assert "created_est" in post, "Each post should have a 'created_est' timestamp."
        assert "score" in post, "Each post should have a 'score'."
        assert "subreddit" in post, "Each post should have a 'subreddit'."
        assert "num_comments" in post, "Each post should have 'num_comments'."


def test_fetch_team_game_threads_nym_range():
    """
    Test the fetch_team_game_threads function for a range of dates for the "NYM" team acronym.
    """
    team_acronym = "NYM"
    start_date = "09/12/2025"
    end_date = "09/14/2025"
    posts = fetch_team_game_threads(
        team_acronym, start_date=start_date, end_date=end_date
    )

    assert isinstance(posts, list), "The result should be a list."
    for post in posts:
        assert (
            "GAME THREAD" in post["title"].upper()
        ), "Each post title should contain 'GAME THREAD'."
        assert "title" in post, "Each post should have a 'title'."
        assert "url" in post, "Each post should have a 'url'."
        assert "created_est" in post, "Each post should have a 'created_est' timestamp."
        assert "score" in post, "Each post should have a 'score'."
        assert "subreddit" in post, "Each post should have a 'subreddit'."
        assert "num_comments" in post, "Each post should have 'num_comments'."


def test_fetch_mlb_events():
    team_acronym = "NYM"
    date = "09/14/2025"
    events = fetch_mlb_events(team_acronym, date=date)
    assert isinstance(events, list), "The result should be a list."
    for event in events:
        print(event)
        assert isinstance(event, tuple), "Each event should be a tuple."
        # Now returning additional columns: home_score, visiting_score, outs
        assert len(event) == 11, "Each event should have 11 elements."
        (
            inning,
            halfInning,
            event_type,
            description,
            est,
            home_team,
            visiting_team,
            home_score,
            visiting_score,
            outs,
            captivatingIndex,
        ) = event
        assert (
            isinstance(inning, int) or inning is None
        ), "Inning should be an integer or None."
        assert (
            isinstance(halfInning, str) or halfInning is None
        ), "HalfInning should be a string or None."
        assert isinstance(event_type, str), "Event should be a string."
        assert isinstance(description, str), "Description should be a string."
        assert isinstance(est, str), "EST should be a string."
        assert isinstance(home_team, str), "Home team should be a string."
        assert isinstance(visiting_team, str), "Visiting team should be a string."
        assert isinstance(home_score, int), "Home score should be an integer."
        assert isinstance(visiting_score, int), "Visiting score should be an integer."
        assert isinstance(outs, int), "Outs should be an integer."
        assert (
            isinstance(captivatingIndex, int) or captivatingIndex is None
        ), "CaptivatingIndex should be an integer or None."
