import subprocess


def main():
    # Install dependencies (cluster bootstrap)
    subprocess.run(["pip", "install", "-r", "requirements.txt"], check=True)
    subprocess.run(["pip", "install", "-e", "."], check=True)

    # Run your CLI
    subprocess.run(
        [
            "mlb-sentiment",
            "upload-mlb",
            "--team-acronym",
            "NYM",
            "--date",
            "09/14/2025",
        ],
        check=True,
    )

    # (Optional) Move MyDatabase.db into DBFS mount
    # import shutil
    # shutil.move("MyDatabase.db", "/dbfs/mnt/mlb-data/MyDatabase.db")


if __name__ == "__main__":
    main()
