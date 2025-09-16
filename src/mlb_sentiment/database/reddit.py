from pyspark.sql import SparkSession
from pyspark.sql.functions import lit
from mlb_sentiment.fetch.reddit import fetch_post_comments
from mlb_sentiment import utility

# Create Spark session
spark = SparkSession.builder.getOrCreate()


def save_post_to_delta(post, limit=5):
    """
    Save a Reddit post and its top-level comments to Delta tables.

    Args:
        post (dict): Output from fetch_team_game_threads.
        limit (int): Max number of top-level comments to save.
    """
    # Convert post to a one-row DataFrame
    post_df = spark.createDataFrame(
        [
            {
                "team_acronym": post["team_acronym"].upper(),
                "post_title": post["title"],
                "post_url": post["url"],
                "created_est": post["created_est"],
            }
        ]
    )

    # Create posts Delta table if not exists
    spark.sql(
        """
        CREATE TABLE IF NOT EXISTS mlb_sentiment_posts (
            team_acronym STRING,
            post_title STRING,
            post_url STRING,
            created_est STRING
        )
        USING DELTA
    """
    )

    # Insert (avoiding duplicates using MERGE)
    post_df.createOrReplaceTempView("new_post")
    spark.sql(
        """
        MERGE INTO mlb_sentiment_posts AS target
        USING new_post AS source
        ON target.post_url = source.post_url
        WHEN NOT MATCHED THEN
          INSERT *
    """
    )

    # Get post_id (Delta doesn't have autoincrement IDs by default — simulate via surrogate keys if needed)
    # Here we assume post_url is unique key
    post_id_df = spark.sql(
        f"""
        SELECT monotonically_increasing_id() AS post_id, post_url
        FROM mlb_sentiment_posts
        WHERE post_url = '{post["url"]}'
    """
    ).limit(1)

    post_id_row = post_id_df.collect()[0]
    post_id = post_id_row["post_id"]

    # Fetch comments
    comments = fetch_post_comments(post["url"], limit=limit)
    comment_rows = [
        {
            "post_url": post["url"],
            "author": c["author"],
            "text": c["text"],
            "created_est": utility.utc_to_est(c["created_utc"]),
        }
        for c in comments
    ]

    if not comment_rows:
        return

    comments_df = spark.createDataFrame(comment_rows)

    # Create comments Delta table
    spark.sql(
        """
        CREATE TABLE IF NOT EXISTS mlb_sentiment_comments (
            post_url STRING,
            author STRING,
            text STRING,
            created_est STRING
        )
        USING DELTA
    """
    )

    # Deduplicate comments based on author + created_est
    comments_df.createOrReplaceTempView("new_comments")
    spark.sql(
        """
        MERGE INTO mlb_sentiment_comments AS target
        USING new_comments AS source
        ON target.post_url = source.post_url
           AND target.author = source.author
           AND target.created_est = source.created_est
        WHEN NOT MATCHED THEN INSERT *
    """
    )


def create_sentiment_results_table():
    """
    Create the Delta table for storing sentiment results.
    """
    spark.sql(
        """
        CREATE TABLE IF NOT EXISTS mlb_sentiment_results (
            post_url STRING,
            author STRING,
            model_type STRING,
            emotion STRING,
            score DOUBLE
        )
        USING DELTA
    """
    )


def save_sentiment_result(post_url, author, model_type, emotion, score):
    """
    Save a sentiment analysis result to Delta table.

    Args:
        post_url (str): URL of the post this comment belongs to.
        author (str): Comment author.
        model_type (str): Type of sentiment model.
        emotion (str): Detected emotion.
        score (float): Sentiment score.
    """
    result_df = spark.createDataFrame(
        [
            {
                "post_url": post_url,
                "author": author,
                "model_type": model_type,
                "emotion": emotion,
                "score": score,
            }
        ]
    )

    result_df.createOrReplaceTempView("new_sentiment_result")

    spark.sql(
        """
        MERGE INTO mlb_sentiment_results AS target
        USING new_sentiment_result AS source
        ON target.post_url = source.post_url
           AND target.author = source.author
           AND target.model_type = source.model_type
        WHEN NOT MATCHED THEN INSERT *
    """
    )
