import pytest
from mlb_sentiment.fetch import fetch_user_posts

def test_fetch_user_posts_nym():
    """
    Test the fetch_user_posts function for the "NYM" team acronym.
    """
    team_acronym = "NYM"
    limit = 5

    # Call the function
    posts = fetch_user_posts(team_acronym, limit=limit)

    # Assertions
    assert isinstance(posts, list), "The result should be a list."
    assert len(posts) <= limit, f"The result should contain at most {limit} posts."

    for post in posts:
        assert "title" in post, "Each post should have a 'title'."
        assert "url" in post, "Each post should have a 'url'."
        assert "created_est" in post, "Each post should have a 'created_est' timestamp."
        assert "score" in post, "Each post should have a 'score'."
        assert "subreddit" in post, "Each post should have a 'subreddit'."