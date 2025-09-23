import os
from dotenv import load_dotenv
import praw

load_dotenv()

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")


def load_reddit_client():
    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )


def load_azure_client():
    """
    Loads Azure Blob Storage configuration from .env and/or GitHub secrets.
    Returns:
        dict: { 'container': str, 'connection_string': str }
    """
    # Load from .env
    container = os.getenv("AZURE_BLOB_CONTAINER")
    connection_string = os.getenv("AZURE_BLOB_CONNECTION_STRING")
    # Optionally, load from GitHub secrets if available
    # For local dev, .env is primary
    if not container or not connection_string:
        raise RuntimeError(
            "Azure Blob Storage configuration missing in .env or secrets."
        )
    return {"container": container, "connection_string": connection_string}


def load_synapse_client():
    """
    Loads Azure Synapse configuration from .env and/or GitHub secrets.
    Returns:
        dict: { 'server': str, 'database': str, 'username': str, 'password': str }
    """
    server = os.getenv("SYNAPSE_SERVER")
    database = os.getenv("SYNAPSE_DATABASE")
    username = os.getenv("SYNAPSE_USERNAME")
    password = os.getenv("SYNAPSE_PASSWORD")
    if not server or not database or not username or not password:
        raise RuntimeError("Azure Synapse configuration missing in .env or secrets.")
    return {
        "server": server,
        "database": database,
        "username": username,
        "password": password,
    }
