"""Build the static site's JSON payloads from Parquet using DuckDB.

This replaces the old Azure Synapse + ``aggregate_*`` scripts. For every team
folder under ``data/`` it reads the accumulated Parquet files, computes the
aggregations the dashboard needs, and writes one compact JSON file per team to
``site/data/`` along with a ``manifest.json`` listing the available teams.

Usage::

    python pipeline/build_site_data.py                 # data/ -> site/data/
    python pipeline/build_site_data.py --data data --out site/data
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from datetime import datetime, timezone

import duckdb
import numpy as np
import pandas as pd

# Reuse the canonical team metadata from the package when statsapi is reachable;
# fall back to a small local map so the build never depends on network access.
TEAM_NAMES = {
    "NYM": "New York Mets",
    "ATL": "Atlanta Braves",
    "SEA": "Seattle Mariners",
    "NYY": "New York Yankees",
    "LAD": "Los Angeles Dodgers",
    "TOR": "Toronto Blue Jays",
}

WINDOW_MIN = 4  # comment-binning window for the per-game sentiment line


def _signed_comments(con: duckdb.DuckDBPyConnection, team_dir: str) -> pd.DataFrame:
    """Load comments and apply the dashboard's score-sign convention in SQL."""
    pattern = os.path.join(team_dir, "*comments*.parquet").replace("'", "''")
    df = con.execute(f"""
        SELECT
            CAST(game_id AS BIGINT) AS game_id,
            author,
            text,
            created_est,
            sentiment,
            CASE
                WHEN sentiment = 'neutral'  THEN 0.0
                WHEN sentiment = 'negative' THEN -abs(sentiment_score)
                ELSE sentiment_score
            END AS sentiment_score
        FROM read_parquet('{pattern}')
        ORDER BY created_est
        """).fetchdf()
    df["created_est"] = pd.to_datetime(df["created_est"])
    return df


def _read(con: duckdb.DuckDBPyConnection, team_dir: str, kind: str) -> pd.DataFrame:
    pattern = os.path.join(team_dir, f"*{kind}*.parquet").replace("'", "''")
    return con.execute(f"SELECT * FROM read_parquet('{pattern}')").fetchdf()


def _regression(x: np.ndarray, y: np.ndarray):
    """Return (slope, intercept, r2) or (None, None, None) if undefined."""
    if len(x) < 2:
        return None, None, None
    m, b = np.polyfit(x, y, 1)
    y_pred = m * x + b
    ss_res = float(np.sum((y - y_pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return float(m), float(b), float(r2)


def _outcome(row, team):
    if pd.isna(row["home_score"]) or pd.isna(row["away_score"]):
        return "Unknown", None
    if row["home_team"] == team:
        diff = row["home_score"] - row["away_score"]
    elif row["away_team"] == team:
        diff = row["away_score"] - row["home_score"]
    else:
        return "Other", None
    return ("Win" if diff > 0 else "Loss" if diff < 0 else "Tie"), int(diff)


def _sentiment_ts(comments: pd.DataFrame) -> list:
    """Binned + smoothed sentiment line for one game."""
    if comments.empty:
        return []
    ts = (
        comments.set_index("created_est")
        .resample(f"{WINDOW_MIN}min")["sentiment_score"]
        .mean()
        .reset_index()
    )
    ts["smooth"] = ts["sentiment_score"].rolling(3, min_periods=1, center=True).mean()
    ts = ts.dropna(subset=["sentiment_score"])
    return [
        {"t": t.strftime("%Y-%m-%d %H:%M:%S"), "score": round(float(s), 4)}
        for t, s in zip(ts["created_est"], ts["smooth"])
    ]


def _run_diff_ts(events: pd.DataFrame, team_is_home: bool) -> list:
    if events.empty:
        return []
    ev = events.copy()
    ev["est"] = pd.to_datetime(ev["est"])
    ev = ev.sort_values("est")
    home = pd.to_numeric(ev["home_score"], errors="coerce").fillna(0)
    away = pd.to_numeric(ev["away_score"], errors="coerce").fillna(0)
    diff = (home - away) if team_is_home else (away - home)
    out, last = [], None
    for t, d in zip(ev["est"], diff.astype(int)):
        if d != last:  # only emit when the lead changes -> compact series
            out.append({"t": t.strftime("%Y-%m-%d %H:%M:%S"), "diff": int(d)})
            last = d
    if out:
        out.append(
            {
                "t": ev["est"].iloc[-1].strftime("%Y-%m-%d %H:%M:%S"),
                "diff": int(diff.iloc[-1]),
            }
        )
    return out


def _distribution(comments: pd.DataFrame) -> dict:
    scores = comments["sentiment_score"].dropna().to_numpy()
    if scores.size == 0:
        return {"centers": [], "positive": [], "negative": []}
    bins = np.histogram_bin_edges(scores, bins=40)
    centers = ((bins[:-1] + bins[1:]) / 2).round(4)
    pos = comments.loc[comments["sentiment"] == "positive", "sentiment_score"]
    neg = comments.loc[comments["sentiment"] == "negative", "sentiment_score"]
    pos_counts, _ = np.histogram(pos.to_numpy(), bins=bins)
    neg_counts, _ = np.histogram(neg.to_numpy(), bins=bins)
    return {
        "centers": centers.tolist(),
        "positive": pos_counts.tolist(),
        "negative": neg_counts.tolist(),
    }


def _inning_sentiment(comments: pd.DataFrame, events: pd.DataFrame) -> list:
    if comments.empty or events.empty:
        return []
    ev = events.copy()
    ev["est"] = pd.to_datetime(ev["est"])
    bounds = (
        ev.groupby(["game_id", "inning"])["est"]
        .max()
        .reset_index()
        .sort_values(["game_id", "est"])
    )
    bounds["start"] = bounds.groupby("game_id")["est"].shift(1)
    bounds["start"] = bounds["start"].fillna(
        ev.groupby("game_id")["est"].transform("min")
    )
    merged = comments.merge(bounds, on="game_id", how="inner")
    mask = (merged["created_est"] >= merged["start"]) & (
        merged["created_est"] < merged["est"]
    )
    merged = merged[mask]
    if merged.empty:
        return []
    agg = merged.groupby("inning")["sentiment_score"].mean().reset_index()
    return [
        {"inning": int(i), "avg_sentiment": round(float(s), 4)}
        for i, s in zip(agg["inning"], agg["sentiment_score"])
    ]


def _event_pie(events: pd.DataFrame, team: str, top_n: int = 8) -> dict:
    """Count batting events for the team vs the opponent."""
    if events.empty:
        return {"team": [], "opponent": []}
    ev = events.copy()
    # Batting team = home on bottom half, away on top half.
    ev["batting"] = np.where(
        ev["halfInning"].str.lower().str.startswith("bottom"),
        ev["home_team"],
        ev["visiting_team"],
    )
    team_counts = ev.loc[ev["batting"] == team, "event"].value_counts().head(top_n)
    opp_counts = ev.loc[ev["batting"] != team, "event"].value_counts().head(top_n)
    fmt = lambda s: [{"event": k, "count": int(v)} for k, v in s.items()]
    return {"team": fmt(team_counts), "opponent": fmt(opp_counts)}


def _top_commenters(comments: pd.DataFrame) -> dict:
    c = comments[comments["author"] != "None"]
    active = c["author"].value_counts().head(10)
    pos = c.loc[c["sentiment"] == "positive", "author"].value_counts().head(5)
    neg = c.loc[c["sentiment"] == "negative", "author"].value_counts().head(5)
    pos_ex = (
        c[c["sentiment"] == "positive"]
        .sort_values("sentiment_score", ascending=False)
        .head(6)[["author", "sentiment_score", "text", "created_est"]]
    )
    neg_ex = (
        c[c["sentiment"] == "negative"]
        .sort_values("sentiment_score")
        .head(6)[["author", "sentiment_score", "text", "created_est"]]
    )
    ex = lambda df: [
        {
            "author": r["author"],
            "score": round(float(r["sentiment_score"]), 3),
            "text": r["text"],
            "date": pd.to_datetime(r["created_est"]).strftime("%m/%d/%Y"),
        }
        for _, r in df.iterrows()
    ]
    pairs = lambda s: [{"author": k, "count": int(v)} for k, v in s.items()]
    return {
        "active": pairs(active),
        "positive": pairs(pos),
        "negative": pairs(neg),
        "positive_examples": ex(pos_ex),
        "negative_examples": ex(neg_ex),
    }


def build_team(con, team: str, team_dir: str) -> dict:
    comments = _signed_comments(con, team_dir)
    games = _read(con, team_dir, "games")
    events = _read(con, team_dir, "game_events")

    games["game_id"] = games["game_id"].astype("int64")
    events["game_id"] = events["game_id"].astype("int64")
    games["game_date"] = pd.to_datetime(games["game_date"])
    games = games.sort_values("game_date").reset_index(drop=True)

    # Per-game average sentiment.
    game_avg = (
        comments.groupby("game_id")["sentiment_score"]
        .mean()
        .reset_index()
        .rename(columns={"sentiment_score": "avg_sentiment"})
    )
    games = games.merge(game_avg, on="game_id", how="left")

    game_rows, scatter, per_game = [], [], {}
    for _, g in games.iterrows():
        outcome, run_diff = _outcome(g, team)
        gid = int(g["game_id"])
        team_is_home = g["home_team"] == team
        avg = (
            None
            if pd.isna(g.get("avg_sentiment"))
            else round(float(g["avg_sentiment"]), 4)
        )
        game_rows.append(
            {
                "game_id": gid,
                "game_date": g["game_date"].strftime("%Y-%m-%d"),
                "home_team": g["home_team"],
                "away_team": g["away_team"],
                "home_score": int(g["home_score"]),
                "away_score": int(g["away_score"]),
                "wins": int(g["wins"]),
                "losses": int(g["losses"]),
                "outcome": outcome,
                "run_diff": run_diff,
                "avg_sentiment": avg,
            }
        )
        if avg is not None and run_diff is not None:
            scatter.append(
                {
                    "run_diff": run_diff,
                    "avg_sentiment": avg,
                    "game_id": gid,
                    "date": g["game_date"].strftime("%Y-%m-%d"),
                }
            )

        gc = comments[comments["game_id"] == gid]
        ge = events[events["game_id"] == gid]
        top = gc.sort_values(
            "sentiment_score", key=lambda s: s.abs(), ascending=False
        ).head(25)[["author", "sentiment_score", "text", "created_est"]]
        per_game[str(gid)] = {
            "team_is_home": bool(team_is_home),
            "sentiment_ts": _sentiment_ts(gc),
            "run_diff_ts": _run_diff_ts(ge, team_is_home),
            "comments": [
                {
                    "author": r["author"],
                    "score": round(float(r["sentiment_score"]), 3),
                    "text": r["text"],
                    "t": pd.to_datetime(r["created_est"]).strftime("%H:%M"),
                }
                for _, r in top.iterrows()
            ],
        }

    # Win/loss averages + global regression (sentiment vs run differential).
    decided = [
        r
        for r in game_rows
        if r["outcome"] in ("Win", "Loss") and r["avg_sentiment"] is not None
    ]
    win_vals = [r["avg_sentiment"] for r in decided if r["outcome"] == "Win"]
    loss_vals = [r["avg_sentiment"] for r in decided if r["outcome"] == "Loss"]
    x = np.array([r["run_diff"] for r in scatter], dtype=float)
    y = np.array([r["avg_sentiment"] for r in scatter], dtype=float)
    m, b, r2 = _regression(x, y)

    return {
        "team": team,
        "team_name": TEAM_NAMES.get(team, team),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "totals": {
            "total_comments": int(len(comments)),
            "total_games": int(games["game_id"].nunique()),
            "total_events": int(len(events)),
        },
        "summary": {
            "win_avg_sentiment": (
                round(float(np.mean(win_vals)), 4) if win_vals else None
            ),
            "loss_avg_sentiment": (
                round(float(np.mean(loss_vals)), 4) if loss_vals else None
            ),
            "slope": round(m, 4) if m is not None else None,
            "intercept": round(b, 4) if b is not None else None,
            "r2": round(r2, 4) if r2 is not None else None,
        },
        "games": game_rows,
        "per_game": per_game,
        "distribution": _distribution(comments),
        "inning_sentiment": _inning_sentiment(comments, events),
        "scatter": scatter,
        "regression": {"slope": m, "intercept": b, "r2": r2},
        "event_pie": _event_pie(events, team),
        "commenters": _top_commenters(comments),
    }


def discover_teams(data_root: str) -> list:
    teams = []
    for entry in sorted(os.listdir(data_root)):
        team_dir = os.path.join(data_root, entry)
        if os.path.isdir(team_dir) and glob.glob(os.path.join(team_dir, "*.parquet")):
            teams.append(entry)
    return teams


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data", default="data", help="Root folder of per-team Parquet"
    )
    parser.add_argument("--out", default="site/data", help="Output folder for JSON")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    con = duckdb.connect()
    teams = discover_teams(args.data)
    if not teams:
        raise SystemExit(f"No team data found under {args.data}/")

    manifest = []
    for team in teams:
        payload = build_team(con, team, os.path.join(args.data, team))
        with open(os.path.join(args.out, f"{team}.json"), "w") as fh:
            json.dump(payload, fh, separators=(",", ":"))
        manifest.append(
            {
                "team": team,
                "team_name": payload["team_name"],
                "total_comments": payload["totals"]["total_comments"],
                "total_games": payload["totals"]["total_games"],
            }
        )
        print(
            f"  built {team}: {payload['totals']['total_comments']} comments, "
            f"{payload['totals']['total_games']} games"
        )

    with open(os.path.join(args.out, "manifest.json"), "w") as fh:
        json.dump(
            {
                "teams": manifest,
                "generated_at": datetime.now(timezone.utc).strftime(
                    "%Y-%m-%d %H:%M UTC"
                ),
            },
            fh,
            indent=2,
        )
    print(f"Wrote {len(teams)} team file(s) + manifest.json to {args.out}/")


if __name__ == "__main__":
    main()
