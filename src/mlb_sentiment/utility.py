from mlb_sentiment.config import load_azure_client
from datetime import datetime, timezone
from azure.storage.blob import BlobServiceClient
import pytz
import os
import json


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


def iso_to_utc(iso):
    """
    Convert an ISO 8601 timestamp to UTC.
    Args:
        iso (str): The ISO 8601 timestamp (e.g., "2023-10-01T15:30:00Z").
    Returns:
        str: The converted time in UTC as an ISO 8601 formatted string.
    """
    if not iso:
        return ""
    if iso.endswith("Z"):
        iso = iso[:-1] + "+00:00"
    return datetime.fromisoformat(iso).astimezone(timezone.utc).isoformat()


def iso_to_est(iso):
    """
    Convert an ISO 8601 timestamp to EST (Eastern Standard Time).
    Args:
        iso (str): The ISO 8601 timestamp (e.g., "2023-10-01T15:30:00Z").
    Returns:
        str: The converted time in EST as a formatted string (e.g., "YYYY-MM-DD HH:MM:SS").
    """
    if not iso:
        return ""
    if iso.endswith("Z"):
        iso = iso[:-1] + "+00:00"
    return utc_to_est(datetime.fromisoformat(iso).timestamp())


def upload_to_azure_blob(
    file_path, blob_name, subdirectory="passiveDatabase", remove_local=False
):
    """
    Uploads a file to Azure Blob Storage.
    Args:
        file_path (str): Path to the local file to upload.
        blob_name (str): Name for the blob in Azure.
        subdirectory (str): Subdirectory in the container to upload the blob to.
        remove_local (bool): Whether to remove the local file after upload.
    Raises:
        ValueError: If subdirectory is not 'passiveDatabase' or 'activeDatabase'.
    """
    assert subdirectory in ["passiveDatabase", "activeDatabase"], "Invalid subdirectory"
    subdirectory += f"/saved={datetime.now().strftime('%Y-%m-%d')}"
    azure_config = load_azure_client()
    blob_service_client = BlobServiceClient.from_connection_string(
        azure_config["connection_string"]
    )
    blob_client = blob_service_client.get_blob_client(
        container=azure_config["container"], blob=f"{subdirectory}/{blob_name}"
    )
    with open(file_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)
    print(
        f"Uploaded {file_path} to Azure Blob Storage as {blob_name} in container {azure_config['container']}/{subdirectory}."
    )
    if remove_local:
        os.remove(file_path)
        print(f"Removed local file: {file_path}")
