import pytest
from mlb_sentiment.fetch.reddit import fetch_team_game_threads


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
