from mlb_sentiment import info
from mlb_sentiment import config
from mlb_sentiment import utility


def fetch_reddit_posts(team_acronym, date=None, start_date=None, end_date=None):
    """
    Fetch game thread posts made by the specified team's game thread user for a specific date (MM/DD/YYYY)
    or for a date range (start_date to end_date, both MM/DD/YYYY).

    Args:
        team_acronym (str): Acronym of the MLB team (e.g., "NYM" for New York Mets).
        date (str, optional): Date in MM/DD/YYYY format to filter posts.
        start_date (str, optional): Start date in MM/DD/YYYY format for range filtering.
        end_date (str, optional): End date in MM/DD/YYYY format for range filtering.

    Returns:
        list: A list of dictionaries containing game thread post details for the specified date or range.
    """

    MAX_LOOKUP = 1000

    # Load Reddit client from info.py
    reddit = config.load_reddit_client()

    # Get the user object
    user = reddit.redditor(info.get_team_info(team_acronym, "game_thread_user"))

    from datetime import datetime

    posts = []
    # Parse date range if provided
    if start_date and end_date:
        start_dt = datetime.strptime(start_date, "%m/%d/%Y")
        end_dt = datetime.strptime(end_date, "%m/%d/%Y")
    else:
        start_dt = end_dt = None

    # Collect posts
    for submission in user.submissions.new(limit=MAX_LOOKUP):
        if (
            "GAME THREAD" in submission.title.upper()
            and "PREGAME" not in submission.title.upper()
            and "POST" not in submission.title.upper()
        ):
            created_est_str = utility.utc_to_est(submission.created_utc)  # returns str
            created_est_dt = datetime.strptime(created_est_str, "%Y-%m-%d %H:%M:%S")
            post_date_str = created_est_dt.strftime("%m/%d/%Y")
            post_dt = datetime.strptime(post_date_str, "%m/%d/%Y")
            match = False
            if date:
                match = post_date_str == date
            elif start_dt and end_dt:
                match = start_dt <= post_dt <= end_dt
            if match:
                posts.append(
                    {
                        "title": submission.title,
                        "url": submission.url,
                        "created_est": created_est_str,
                        "score": submission.score,
                        "subreddit": str(submission.subreddit),
                        "team_acronym": team_acronym,
                        "num_comments": submission.num_comments,
                        "created_est_dt": created_est_dt,
                        # game_id will be added later
                    }
                )
            if start_dt and end_dt and post_dt < start_dt:
                break
            if date and post_date_str < date:
                break

    # Sort posts chronologically
    posts.sort(key=lambda p: p["created_est_dt"])

    # Get game_ids for the date/range
    from mlb_sentiment.fetch.mlb import fetch_game_ids

    if date:
        game_ids = fetch_game_ids(team_acronym, date=date)
    elif start_date and end_date:
        game_ids = fetch_game_ids(
            team_acronym, start_date=start_date, end_date=end_date
        )
    else:
        game_ids = []

    # Assign game_id to each post (chronologically)
    for i, post in enumerate(posts):
        post["game_id"] = game_ids[i] if i < len(game_ids) else None
        del post["created_est_dt"]  # Remove temp field

    return posts


def fetch_reddit_comments(posts, limit=5):
    """
    Fetch a limited number of top-level comments for a given Reddit post.

    Args:
        posts (list): A list of post dictionaries as returned by fetch_reddit_posts.
        limit (int): The maximum number of top-level comments to fetch.

    Returns:
        list: A list of dictionaries containing comment details.
    """
    reddit = config.load_reddit_client()
    comments = []
    for post in posts:
        post_url = post["url"]
        game_id = post.get("game_id")
        submission = reddit.submission(url=post_url)
        submission.comment_sort = "old"
        submission.comments.replace_more(limit=0)

        for comment in submission.comments.list()[:limit]:
            comments.append(
                {
                    "author": str(comment.author),
                    "text": comment.body,
                    "created_utc": comment.created_utc,
                    "game_id": game_id,
                }
            )
    return comments
