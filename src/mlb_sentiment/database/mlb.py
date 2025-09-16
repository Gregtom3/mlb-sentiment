from pyspark.sql import SparkSession

# Create Spark session
spark = SparkSession.builder.getOrCreate()


def save_game_to_delta(game):
    """
    Save MLB game events to Delta table.

    Args:
        game (list of tuples): Each tuple contains (inning, halfInning, event, description, est, home_team, visiting_team)
    """
    # Convert game data to DataFrame
    columns = [
        "inning",
        "halfInning",
        "event",
        "description",
        "est",
        "home_team",
        "visiting_team",
    ]
    game_df = spark.createDataFrame(game, columns)

    # Create Delta table if not exists
    spark.sql(
        """
        CREATE TABLE IF NOT EXISTS mlb_sentiment_games (
            inning INT,
            halfInning STRING,
            event STRING,
            description STRING,
            est STRING,
            home_team STRING,
            visiting_team STRING
        )
        USING DELTA
    """
    )

    # Deduplicate and insert using MERGE
    game_df.createOrReplaceTempView("new_games")
    spark.sql(
        """
        MERGE INTO mlb_sentiment_games AS target
        USING new_games AS source
        ON target.inning = source.inning
           AND target.halfInning = source.halfInning
           AND target.event = source.event
           AND target.est = source.est
           AND target.home_team = source.home_team
           AND target.visiting_team = source.visiting_team
        WHEN NOT MATCHED THEN
          INSERT *
    """
    )
    print(f"Saved {game_df.count()} game events to Delta table.")
    return True
