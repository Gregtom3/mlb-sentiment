import os
from typing import List, Tuple


def spark_available():
    try:
        # In Databricks or a PySpark environment this should succeed
        import pyspark  # noqa: F401
        return True
    except Exception:
        return False


def get_spark_session():
    """Return an existing SparkSession or create one.

    On Databricks, a Spark session is already available as `spark` in notebooks.
    When running as a library on a cluster, SparkSession.builder.getOrCreate()
    will work. This function intentionally avoids importing databricks-specific
    helpers so it can be used in unit tests locally.
    """
    try:
        from pyspark.sql import SparkSession

        return SparkSession.builder.getOrCreate()
    except Exception as e:
        raise RuntimeError("Spark is not available in this environment") from e


def save_game_to_delta(game: List[Tuple], path: str = None):
    """Save a list of game event tuples to a Delta table/path using Spark.

    Args:
        game: Iterable of tuples matching (inning, halfInning, event, description, est, home_team, visiting_team)
        path: Delta table path or DBFS mount (e.g. 'dbfs:/mnt/mlb/games' or '/mnt/mlb/games').
              If not provided, this will look for the GAME_TABLE_PATH env var and
              otherwise default to 'dbfs:/mlb/games'.

    Notes:
        - On Azure Databricks, prefer writing to an ADLS Gen2 path (abfss://...) or a mounted
          DBFS path. Manage credentials using a secret scope or an instance profile.
        - This function requires the cluster to have the Delta Lake package available
          (Databricks runtimes include Delta by default).
    """
    if not path:
        path = os.environ.get("GAME_TABLE_PATH", "dbfs:/mlb/games")

    spark = get_spark_session()

    # Define schema columns to match the existing sqlite schema
    columns = [
        "inning",
        "halfInning",
        "event",
        "description",
        "est",
        "home_team",
        "visiting_team",
    ]

    # Create DataFrame from the list of tuples. If game is empty, ensure we create
    # an empty dataframe with the right schema to allow table creation on first write.
    if game:
        df = spark.createDataFrame(game, schema=columns)
    else:
        from pyspark.sql.types import StructType, StructField, StringType, IntegerType

        schema = StructType(
            [
                StructField("inning", IntegerType(), True),
                StructField("halfInning", StringType(), True),
                StructField("event", StringType(), True),
                StructField("description", StringType(), True),
                StructField("est", StringType(), True),
                StructField("home_team", StringType(), True),
                StructField("visiting_team", StringType(), True),
            ]
        )
        df = spark.createDataFrame([], schema=schema)

    # Write as Delta. Use 'append' so repeated runs add new events; rely on
    # upstream deduplication if necessary.
    df.write.format("delta").mode("append").save(path)

    return True
