import subprocess
import sys


def test_cli_fetch():
    """
    Tests that the CLI fetch runs without errors.
    """
    command = [
        "mlb-sentiment",
        "fetch",
        "NYM",
        "--posts-limit",
        "1",
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
    command = [
        "mlb-sentiment",
        "analyze",
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0
