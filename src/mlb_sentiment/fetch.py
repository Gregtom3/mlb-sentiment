from mlb_sentiment import info
from mlb_sentiment import config
from mlb_sentiment import utility

def fetch_user_posts(team_acronym, limit=10):
    """
    Fetch recent posts made by the specified team's game thread user.

    Args:
        team_acronym (str): Acronym of the MLB team (e.g., "NYM" for New York Mets).
        limit (int): The maximum number of posts to fetch.

    Returns:
        list: A list of dictionaries containing post details.
    """
    # Load Reddit client from info.py
    reddit = config.load_reddit_client()

    # Get the user object
    user = reddit.redditor(info.TEAM_INFO[team_acronym]["game_thread_user"])

    # Fetch the user's posts
    posts = []
    for submission in user.submissions.new(limit=limit):
        posts.append({
            "title": submission.title,
            "url": submission.url,
            "created_est": utility.utc_to_est(submission.created_utc),
            "score": submission.score,
            "subreddit": str(submission.subreddit)
        })

    return posts


if __name__ == "__main__":
    team_acronym = "NYM"  # Example: New York Mets
    posts = fetch_user_posts(team_acronym, limit=5)
    for i, post in enumerate(posts, start=1):
        print(f"Post {i}:")
        print(f"  Title: {post['title']}")
        print(f"  URL: {post['url']}")
        print(f"  Subreddit: {post['subreddit']}")
        print(f"  Created (EST): {post['created_est']}")
        print(f"  Score: {post['score']}")
        print()