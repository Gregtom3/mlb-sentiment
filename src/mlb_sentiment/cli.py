import argparse
from mlb_sentiment.api import fetch_and_save_team_game_threads


def main():
    parser = argparse.ArgumentParser(
        description="A CLI for fetching and saving MLB game threads."
    )
    parser.add_argument(
        "team_acronym", type=str, help="The acronym of the MLB team (e.g., 'NYM')."
    )
    parser.add_argument(
        "--limit", type=int, default=10, help="The maximum number of posts to fetch."
    )
    parser.add_argument(
        "--comments-limit",
        type=int,
        default=5,
        help="The maximum number of comments to save.",
    )

    args = parser.parse_args()

    fetch_and_save_team_game_threads(
        team_acronym=args.team_acronym,
        limit=args.limit,
        comments_limit=args.comments_limit,
    )
    print(f"Successfully fetched and saved game threads for {args.team_acronym}.")


if __name__ == "__main__":
    main()
