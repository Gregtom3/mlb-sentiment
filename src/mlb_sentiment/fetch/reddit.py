import asyncpraw
import asyncio
from mlb_sentiment import info
from mlb_sentiment import config
from mlb_sentiment import utility


async def fetch_team_game_threads(
    team_acronym, date=None, start_date=None, end_date=None
):
    """
    Async: Fetch game thread posts made by the specified team's game thread user for a specific date (MM/DD/YYYY)
    or for a date range (start_date to end_date, both MM/DD/YYYY).
    """
    MAX_LOOKUP = 1000
    reddit = asyncpraw.Reddit(
        client_id=config.REDDIT_CLIENT_ID,
        client_secret=config.REDDIT_CLIENT_SECRET,
        user_agent=config.REDDIT_USER_AGENT,
    )
    user = await reddit.redditor(info.TEAM_INFO[team_acronym]["game_thread_user"])
    from datetime import datetime

    posts = []
    if start_date and end_date:
        start_dt = datetime.strptime(start_date, "%m/%d/%Y")
        end_dt = datetime.strptime(end_date, "%m/%d/%Y")
    else:
        start_dt = end_dt = None
    async for submission in user.submissions.new(limit=MAX_LOOKUP):
        if (
            "GAME THREAD" in submission.title.upper()
            and "PREGAME" not in submission.title.upper()
            and "POST" not in submission.title.upper()
        ):
            created_est_str = utility.utc_to_est(submission.created_utc)
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
                    }
                )
    await reddit.close()
    return posts


async def fetch_post_comments(post_url, limit=5):
    """
    Async: Fetch a limited number of top-level comments for a given Reddit post.
    """
    reddit = asyncpraw.Reddit(
        client_id=config.REDDIT_CLIENT_ID,
        client_secret=config.REDDIT_CLIENT_SECRET,
        user_agent=config.REDDIT_USER_AGENT,
    )
    submission = await reddit.submission(url=post_url)
    submission.comment_sort = "old"
    await submission.comments.replace_more(limit=0)
    comments = []
    count = 0
    async for comment in submission.comments:
        if count >= limit:
            break
        comments.append(
            {
                "author": str(comment.author),
                "text": comment.body,
                "created_utc": comment.created_utc,
            }
        )
        count += 1
    await reddit.close()
    return comments


async def main():
    team_acronym = "NYM"
    date = "09/14/2025"
    posts = await fetch_team_game_threads(team_acronym, date=date)
    for post in posts:
        print(post)


if __name__ == "__main__":
    asyncio.run(main())
