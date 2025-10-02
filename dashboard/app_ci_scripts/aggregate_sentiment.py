from mlb_sentiment.config import load_synapse_engine
from lightweight_dataloader import safe_read_sql
from mlb_sentiment.utility import upload_to_azure_blob
from mlb_sentiment.info import PROCESSED_TEAMS
import pandas as pd
import numpy as np
import time


def aggregate_sentiment(
    comments_df: pd.DataFrame,
    games_df: pd.DataFrame,
    team_acronym: str,
):
    """
    Compute average sentiment when the team wins and when they lose,
    plus regression slope/intercept/R² of sentiment vs. run differential.

    Parameters
    ----------
    comments_df : pd.DataFrame
        Must contain ['game_id','sentiment_score'].
    games_df : pd.DataFrame
        Must contain ['game_id','game_date','home_team','away_team','home_score','away_score'].
    team_acronym : str
        Team acronym to determine wins/losses.

    Returns
    -------
    tuple
        (win_avg, loss_avg, m, b, r2)
    """

    if comments_df is None or comments_df.empty:
        raise ValueError("comments_df is required and cannot be empty.")
    if games_df is None or games_df.empty:
        raise ValueError("games_df is required and cannot be empty.")

    # --- Prep data
    comments_df = comments_df.copy()
    games_df = games_df.copy()

    # Average sentiment per game
    game_sent = (
        comments_df.groupby("game_id")["sentiment_score"]
        .mean()
        .reset_index()
        .rename(columns={"sentiment_score": "avg_sentiment"})
    )

    merged = pd.merge(
        games_df,
        game_sent,
        on="game_id",
        how="inner",
    )

    # Determine win/loss
    def outcome(row):
        if pd.isna(row["home_score"]) or pd.isna(row["away_score"]):
            return "Unknown"
        if row["home_team"] == team_acronym:
            return "Win" if row["home_score"] > row["away_score"] else "Loss"
        elif row["away_team"] == team_acronym:
            return "Win" if row["away_score"] > row["home_score"] else "Loss"
        return "Other"

    merged["Outcome"] = merged.apply(outcome, axis=1)
    merged = merged[merged["Outcome"].isin(["Win", "Loss"])]

    if merged.empty:
        return np.nan, np.nan, np.nan, np.nan, np.nan

    # --- Compute averages
    win_avg = merged.loc[merged["Outcome"] == "Win", "avg_sentiment"].mean()
    loss_avg = merged.loc[merged["Outcome"] == "Loss", "avg_sentiment"].mean()

    # --- Compute regression of avg_sentiment vs. run differential
    # Run differential from perspective of team_acronym
    run_diff = []
    for _, row in merged.iterrows():
        if row["home_team"] == team_acronym:
            run_diff.append(row["home_score"] - row["away_score"])
        elif row["away_team"] == team_acronym:
            run_diff.append(row["away_score"] - row["home_score"])
        else:
            run_diff.append(np.nan)

    merged["run_diff"] = run_diff
    merged = merged.dropna(subset=["run_diff", "avg_sentiment"])

    if len(merged) >= 2:
        x = merged["run_diff"].to_numpy()
        y = merged["avg_sentiment"].to_numpy()
        m, b = np.polyfit(x, y, 1)
        y_pred = m * x + b
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    else:
        m, b, r2 = np.nan, np.nan, np.nan

    # --- Print results
    print(f"Team: {team_acronym}")
    print(f"  Avg Sentiment when Winning: {win_avg:.4f}")
    print(f"  Avg Sentiment when Losing: {loss_avg:.4f}")
    print(f"  Regression: y = {m:.4f}x + {b:.4f}, R² = {r2:.4f}")

    return win_avg, loss_avg, m, b, r2


if __name__ == "__main__":
    engine = load_synapse_engine()
    valid_team_acronyms = PROCESSED_TEAMS

    summary_df = pd.DataFrame(
        columns=[
            "team_acronym",
            "num_comments",
            "win_avg_sentiment",
            "loss_avg_sentiment",
            "slope_m",
            "intercept_b",
            "r2",
        ]
    )

    for team_acronym in valid_team_acronyms:
        t = time.time()
        comments_df = safe_read_sql(
            f"SELECT game_id, sentiment, sentiment_score, created_est FROM dbo.commentsTruncated_{team_acronym}",
            engine,
        )
        comments_df.loc[comments_df["sentiment"] == "neutral", "sentiment_score"] = 0.0
        comments_df.loc[comments_df["sentiment"] == "negative", "sentiment_score"] = (
            comments_df.loc[
                comments_df["sentiment"] == "negative", "sentiment_score"
            ].apply(lambda x: -abs(x))
        )
        print(
            f"Loaded {team_acronym} comments in {time.time() - t:.2f} seconds. Rows: {len(comments_df)}"
        )

        t = time.time()
        games_df = safe_read_sql(
            f"SELECT game_id, game_date, home_team, away_team, home_score, away_score FROM dbo.games_{team_acronym}",
            engine,
        )
        print(
            f"Loaded {team_acronym} games in {time.time() - t:.2f} seconds. Rows: {len(games_df)}"
        )

        win_avg, loss_avg, m, b, r2 = aggregate_sentiment(
            comments_df, games_df, team_acronym=team_acronym
        )

        summary_df = pd.concat(
            [
                summary_df,
                pd.DataFrame(
                    {
                        "team_acronym": [team_acronym],
                        "num_comments": [len(comments_df)],
                        "win_avg_sentiment": [win_avg],
                        "loss_avg_sentiment": [loss_avg],
                        "slope_m": [m],
                        "intercept_b": [b],
                        "r2": [r2],
                    }
                ),
            ],
            ignore_index=True,
        )

    print("\nSummary of Sentiment Metrics:")
    print(summary_df)

    # Write locally then upload
    local_path = "database_sentiment_avg.parquet"
    summary_df.to_parquet(local_path, index=False)

    upload_to_azure_blob(
        file_path=local_path,
        blob_name="database_sentiment_avg.parquet",
        subdirectory="activeDatabase/summary",
        remove_local=True,
    )

    print("Uploaded summary to Azure Blob Storage.")
