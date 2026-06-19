"""Verify the configured team metadata against MLB Stats API and Reddit.

Hand-triggered diagnostic (see .github/workflows/verify.yml). For every club in
``SUBREDDIT_INFO`` it checks, end to end:

  1. the abbreviation resolves to a Stats API team id (catches wrong keys),
  2. the subreddit exists on Reddit,
  3. a recent game in the lookback window can be found, and its game thread is
     retrievable (via the configured bot, or the subreddit-title scan).

It also prints the canonical Stats API abbreviation list so mismatches (e.g.
``AZ`` vs ``ARI``, ``ATH`` vs ``OAK``) are obvious.

Usage::

    python pipeline/verify_teams.py --days 7
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta

import statsapi

from mlb_sentiment.info import (
    SUBREDDIT_INFO,
    get_team_info,
    get_team_name_from_team_acronym,
)
from mlb_sentiment.config import load_reddit_client
from mlb_sentiment.fetch.reddit import fetch_reddit_posts

FINISHED = ("final", "game over", "completed early")


def canonical_teams():
    """Return {abbreviation: (id, name)} for all MLB clubs per Stats API."""
    teams = statsapi.get("teams", {"sportId": 1}).get("teams", [])
    out = {}
    for t in teams:
        abbr = t.get("abbreviation")
        if abbr:
            out[abbr] = (t.get("id"), t.get("name"))
    return out


def recent_game_dates(team_id, days, limit=3):
    """Most recent finished-game dates (MM/DD/YYYY) within the window."""
    end = datetime.now()
    start = end - timedelta(days=days)
    sched = statsapi.schedule(
        team=team_id,
        start_date=start.strftime("%m/%d/%Y"),
        end_date=end.strftime("%m/%d/%Y"),
    )
    finished = [g for g in sched if g.get("status", "").lower() in FINISHED] or sched
    finished.sort(key=lambda g: g["game_date"], reverse=True)
    dates = []
    for g in finished:
        d = datetime.strptime(g["game_date"], "%Y-%m-%d").strftime("%m/%d/%Y")
        if d not in dates:
            dates.append(d)
        if len(dates) >= limit:
            break
    return dates


def verify_team(team, reddit, canon, days):
    meta = SUBREDDIT_INFO[team]
    bot = meta.get("game_thread_user")
    row = {
        "team": team,
        "mode": f"bot:{bot}" if bot else "scan",
        "abbrev_ok": team in canon,
        "statsapi_name": canon.get(team, (None, None))[1],
        "team_id": None,
        "subreddit_ok": False,
        "game_date": None,
        "posts": None,
        "comments": None,
        "note": "",
    }

    # 1. abbreviation -> team id
    try:
        row["team_id"] = get_team_info(team, "team_id")
        if not row["statsapi_name"]:
            row["statsapi_name"] = get_team_name_from_team_acronym(team)
    except Exception as e:  # noqa: BLE001 - diagnostic, capture everything
        row["note"] = f"abbrev: {e}"
        return row

    # 2. subreddit reachable
    try:
        sub = meta["subreddit"].split("/r/")[1].strip("/")
        _ = reddit.subreddit(sub).id
        row["subreddit_ok"] = True
    except Exception as e:  # noqa: BLE001
        row["note"] = f"subreddit: {e}"

    # 3. recent game thread retrievable
    try:
        dates = recent_game_dates(row["team_id"], days)
        if not dates:
            row["note"] = (row["note"] + "; no game in window").strip("; ")
            return row
        for d in dates:
            posts = fetch_reddit_posts(team, date=d)
            if posts:
                row["game_date"] = d
                row["posts"] = len(posts)
                row["comments"] = sum(p.get("num_comments", 0) for p in posts)
                break
        else:
            row["game_date"] = dates[0]
            row["posts"] = 0
            row["note"] = (
                row["note"] + f"; 0 threads found across {len(dates)} recent game(s)"
            ).strip("; ")
    except Exception as e:  # noqa: BLE001
        row["note"] = (row["note"] + f"; posts: {e}").strip("; ")

    return row


def _status(row):
    if not row["abbrev_ok"]:
        return "❌ abbrev"
    if not row["subreddit_ok"]:
        return "❌ subreddit"
    if row["posts"] is None:
        return "➖ no game"
    if row["posts"] == 0:
        return "⚠️ no thread"
    return "✅ ok"


def render(rows, canon, days):
    lines = []
    lines.append(f"# Team verification (last {days} days)\n")

    lines.append("## Results\n")
    lines.append(
        "| Team | Status | Stats API name | id | subreddit | mode | game | posts | comments |"
    )
    lines.append("|---|---|---|---|:--:|---|---|--:|--:|")
    for r in rows:
        lines.append(
            f"| {r['team']} | {_status(r)} | {r['statsapi_name'] or '—'} | "
            f"{r['team_id'] or '—'} | {'✓' if r['subreddit_ok'] else '✗'} | "
            f"{r['mode']} | {r['game_date'] or '—'} | "
            f"{'—' if r['posts'] is None else r['posts']} | "
            f"{'—' if r['comments'] is None else r['comments']} |"
        )

    # Caveats
    bad_abbr = [r for r in rows if not r["abbrev_ok"]]
    bad_sub = [r for r in rows if r["abbrev_ok"] and not r["subreddit_ok"]]
    no_thread = [r for r in rows if r["posts"] == 0]
    no_game = [
        r for r in rows if r["abbrev_ok"] and r["subreddit_ok"] and r["posts"] is None
    ]

    lines.append("\n## ⚠️ Caveats\n")
    if bad_abbr:
        lines.append(
            "**Abbreviation not found in Stats API** (fix the key in SUBREDDIT_INFO):"
        )
        for r in bad_abbr:
            lines.append(f"- `{r['team']}` — {r['note']}")
    if bad_sub:
        lines.append("**Subreddit unreachable:**")
        for r in bad_sub:
            lines.append(f"- `{r['team']}` — {r['note']}")
    if no_thread:
        lines.append(
            "**Played recently but no game thread found** (check bot name / subreddit / title format):"
        )
        for r in no_thread:
            lines.append(f"- `{r['team']}` ({r['mode']}) — {r['note']}")
    if no_game:
        lines.append(
            "**No game in window (inconclusive):** "
            + ", ".join(r["team"] for r in no_game)
        )
    if not (bad_abbr or bad_sub or no_thread):
        lines.append(
            "None — every team with a recent game resolved and returned a thread. 🎉"
        )

    # Canonical reference
    lines.append("\n## Canonical Stats API abbreviations\n")
    lines.append("| abbr | id | name | configured? |")
    lines.append("|---|---|---|:--:|")
    for abbr in sorted(canon):
        tid, name = canon[abbr]
        lines.append(
            f"| {abbr} | {tid} | {name} | {'✓' if abbr in SUBREDDIT_INFO else ''} |"
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7, help="Lookback window in days")
    args = parser.parse_args()

    canon = canonical_teams()
    reddit = load_reddit_client()

    rows = []
    for team in sorted(SUBREDDIT_INFO):
        print(f"Verifying {team} ...", flush=True)
        rows.append(verify_team(team, reddit, canon, args.days))

    report = render(rows, canon, args.days)
    print("\n" + report)

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as fh:
            fh.write(report + "\n")

    # Non-zero exit if any configured team is definitively broken.
    broken = [r for r in rows if not r["abbrev_ok"] or not r["subreddit_ok"]]
    if broken:
        raise SystemExit(f"{len(broken)} team(s) have broken key info — see report.")


if __name__ == "__main__":
    main()
