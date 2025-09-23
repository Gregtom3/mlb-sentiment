import subprocess
import sys


def test_cli_fetch():
    """
    Tests that the CLI fetch runs without errors.
    """
    command = [
        "mlb-sentiment",
        "upload",
        "--team-acronym",
        "NYM",
        "--date",
        "09/14/2025",
        "--comments-limit",
        "1",
    ]
    result = subprocess.run(command, capture_output=True, text=True)

    assert result.returncode == 0
