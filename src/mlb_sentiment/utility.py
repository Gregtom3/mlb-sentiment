from datetime import datetime
import pytz

def utc_to_est(utc_timestamp):
    """
    Convert a UTC timestamp to EST (Eastern Standard Time).

    Args:
        utc_timestamp (float): The UTC timestamp (e.g., from Reddit's `created_utc`).

    Returns:
        str: The converted time in EST as a formatted string (e.g., "YYYY-MM-DD HH:MM:SS").
    """
    # Define UTC and EST timezones
    utc_zone = pytz.utc
    est_zone = pytz.timezone("US/Eastern")

    # Convert the UTC timestamp to a datetime object
    utc_time = datetime.fromtimestamp(utc_timestamp, utc_zone)

    # Convert UTC time to EST
    est_time = utc_time.astimezone(est_zone)

    # Return the formatted EST time
    return est_time.strftime("%Y-%m-%d %H:%M:%S")

def est_time_delta(est_time1, est_time2):
    """
    Calculate the delta (difference) in seconds between two EST timestamps.

    Args:
        est_time1 (str): The first EST timestamp in the format "YYYY-MM-DD HH:MM:SS".
        est_time2 (str): The second EST timestamp in the format "YYYY-MM-DD HH:MM:SS".

    Returns:
        int: The difference in seconds between the two timestamps.
    """
    # Define the EST timezone
    est_zone = pytz.timezone("US/Eastern")

    # Parse the timestamps into datetime objects
    time1 = datetime.strptime(est_time1, "%Y-%m-%d %H:%M:%S").replace(tzinfo=est_zone)
    time2 = datetime.strptime(est_time2, "%Y-%m-%d %H:%M:%S").replace(tzinfo=est_zone)

    # Calculate the difference in seconds
    delta = (time2 - time1).total_seconds()

    return int(delta)