import subprocess
import sys


def test_cli_fetch():
    """
    Tests that the CLI fetch runs without errors.
    """
    command = [
        "mlb-sentiment",
        "upload-reddit",
        "--team-acronym",
        "NYM",
        "--date",
        "09/14/2025",
        "--comments-limit",
        "1",
    ]
    result = subprocess.run(command, capture_output=True, text=True)

    assert result.returncode == 0
    assert "Successfully fetched and saved game threads for NYM." in result.stdout


def test_cli_analyze():
    """
    Tests that the CLI analyze runs without errors.
    """
    command = ["mlb-sentiment", "analyze"]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0


def test_cli_upload_reddit_yesterday():
    """
    Tests that the CLI upload-reddit with --yesterday flag runs without errors.
    """
    command = [
        "mlb-sentiment",
        "upload-reddit",
        "--team-acronym",
        "NYM",
        "--yesterday",
        "--comments-limit",
        "1",
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0


def test_cli_upload_mlb_yesterday():
    """
    Tests that the CLI upload-mlb with --yesterday flag runs without errors.
    """
    command = [
        "mlb-sentiment",
        "upload-mlb",
        "--team-acronym",
        "NYM",
        "--yesterday",
        "--filename",
        "MyDatabase.csv",
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0
