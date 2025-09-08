from mlb_sentiment import info
from mlb_sentiment import config
from mlb_sentiment import utility


def fetch_team_game_threads(team_acronym, limit=10):
    """
    Fetch recent game thread posts made by the specified team's game thread user.

    Args:
        team_acronym (str): Acronym of the MLB team (e.g., "NYM" for New York Mets).
        limit (int): The maximum number of posts to fetch.

    Returns:
        list: A list of dictionaries containing game thread post details.
    """

    MAX_LIMIT = 10000

    # Load Reddit client from info.py
    reddit = config.load_reddit_client()

    # Get the user object
    user = reddit.redditor(info.TEAM_INFO[team_acronym]["game_thread_user"])

    posts = []
    for submission in user.submissions.new(limit=MAX_LIMIT):
        if (
            "GAME THREAD" in submission.title.upper()
            and "PREGAME" not in submission.title.upper()
            and "POST" not in submission.title.upper()
        ):
            posts.append(
                {
                    "title": submission.title,
                    "url": submission.url,
                    "created_est": utility.utc_to_est(submission.created_utc),
                    "score": submission.score,
                    "subreddit": str(submission.subreddit),
                    "num_comments": submission.num_comments,
                }
            )
        if len(posts) >= limit:
            break
    return posts


if __name__ == "__main__":
    team_acronym = "NYM"
    posts = fetch_team_game_threads(team_acronym, limit=10)
    for i, post in enumerate(posts, start=1):
        print(f"Post {i}:")
        print(f"  Title: {post['title']}")
        print(f"  URL: {post['url']}")
        print(f"  Subreddit: {post['subreddit']}")
        print(f"  Created (EST): {post['created_est']}")
        print(f"  Score: {post['score']}")
        print(f"  Number of Comments: {post['num_comments']}")
        print()
