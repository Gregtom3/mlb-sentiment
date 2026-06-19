"""Generate a realistic synthetic week of data for local development and demos.

Live fetching requires Reddit credentials and MLB Stats API egress that only
exist inside the GitHub Action. This module fabricates a week of games for a
single team using the *exact* Parquet schema produced by ``mlb_sentiment`` so
the rest of the pipeline (DuckDB build + static site) can be exercised offline.

The fabricated sentiment is intentionally correlated with the score so the
charts tell a coherent story: fans turn positive when their team scores and
sour when they fall behind.

Run with::

    python pipeline/sample_data.py            # writes data/NYM/*.parquet
"""

from __future__ import annotations

import os
import random
from datetime import datetime, timedelta

import pandas as pd

# Mets team id prefix used by mlb_sentiment to namespace game ids.
TEAM_ID = 121
TEAM = "NYM"
TEAM_NAME = "New York Mets"

# (opponent, mets_are_home, mets_runs, opp_runs)
SCHEDULE = [
    ("ATL", True, 6, 2, "06/12/2026"),
    ("ATL", True, 3, 4, "06/13/2026"),
    ("PHI", False, 5, 5, "06/14/2026"),  # extra-innings-ish tie kept simple -> Mets win
    ("PHI", False, 1, 7, "06/15/2026"),
    # 06/16 off day
    ("LAD", True, 8, 3, "06/17/2026"),
    ("LAD", True, 2, 5, "06/18/2026"),
]

AUTHORS = [
    "metsmagic86",
    "amazinfan",
    "lfgm_always",
    "flushingfaithful",
    "applesAreUp",
    "citifieldcryer",
    "diaztrumpets",
    "lindormvp",
    "polarbear_pete",
    "kodaisamurai",
    "sevenline_express",
    "buckmeyer",
    "grimacewatch",
    "orangeandblue",
    "thinkblueno",
]

POSITIVE_LINES = [
    "LETS GO METS!!! what a swing",
    "that ball is OUTTA HERE, incredible",
    "Lindor doing Lindor things, MVP",
    "this is the team we knew they could be",
    "clutch hit when we needed it most",
    "Diaz slamming the door, trumpets blaring",
    "best game I've watched all year honestly",
    "the bats are ALIVE tonight baby",
    "huge insurance run, breathe easy now",
    "pete the polar bear with a moonshot",
]
NEUTRAL_LINES = [
    "runner on first, one out",
    "full count here",
    "pitching change incoming",
    "anyone have the radar gun reading",
    "decent at bat, worked the count",
    "ok here we go bottom of the 6th",
    "weather looks fine at Citi tonight",
    "lineup card looks normal today",
]
NEGATIVE_LINES = [
    "are you KIDDING me with that error",
    "bullpen blowing it AGAIN, im done",
    "that was a brutal called strike three",
    "this lineup cant buy a hit rn",
    "same old Mets, heartbreaking",
    "why would you bunt there, awful call",
    "another runner left in scoring position ugh",
    "cant watch this anymore, turning it off",
]

EVENTS_SCORING = ["Home Run", "Single", "Double", "Triple", "Sac Fly"]
EVENTS_OUT = ["Strikeout", "Groundout", "Flyout", "Lineout", "Pop Out", "Double Play"]
EVENTS_ON = ["Walk", "Single", "Hit By Pitch"]


def _est(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def build_team(team: str = TEAM, seed: int = 7):
    rng = random.Random(seed)
    games, events, comments, posts = [], [], [], []
    wins = losses = 0
    comment_id = 1
    event_id = 0
    post_id = 1

    for opp, home, mets_runs, opp_runs, game_date in SCHEDULE:
        if mets_runs == opp_runs:
            mets_runs += 1  # break ties in the Mets' favor

        home_team, away_team = (team, opp) if home else (opp, team)
        home_score, away_score = (
            (mets_runs, opp_runs) if home else (opp_runs, mets_runs)
        )
        mets_won = mets_runs > opp_runs
        wins += int(mets_won)
        losses += int(not mets_won)

        game_id = int(f"{TEAM_ID}{rng.randint(700000, 799999)}")
        first_pitch = datetime.strptime(game_date + " 19:10:00", "%m/%d/%Y %H:%M:%S")

        games.append(
            {
                "game_id": game_id,
                "game_date": game_date,
                "game_start_time_est": first_pitch.strftime("%H:%M:%S"),
                "home_team": home_team,
                "away_team": away_team,
                "home_score": home_score,
                "away_score": away_score,
                "wins": wins,
                "losses": losses,
            }
        )

        posts.append(
            {
                "id": post_id,
                "game_id": game_id,
                "team_acronym": team,
                "post_title": f"Game Thread: {away_team} @ {home_team} - {game_date}",
                "post_url": f"https://www.reddit.com/r/NewYorkMets/comments/sample{post_id}/",
                "created_est": _est(first_pitch - timedelta(minutes=20)),
            }
        )
        post_id += 1

        # --- Walk the game inning by inning, distributing runs across innings.
        mets_left = mets_runs
        opp_left = opp_runs
        run_home = run_away = 0
        scoring_moments = []  # (time, mets_scored) for reaction bursts
        t = first_pitch
        for inning in range(1, 10):
            for half in ("top", "bottom"):
                batting_is_mets = (half == "bottom") == home
                runs_this_half = 0
                if inning >= 9 and half == "bottom" and home and mets_won:
                    pass  # walk-off handling kept simple
                # Randomly score some of the remaining runs.
                pool = mets_left if batting_is_mets else opp_left
                if pool > 0 and rng.random() < 0.45:
                    runs_this_half = rng.randint(1, min(pool, 3))
                    if batting_is_mets:
                        mets_left -= runs_this_half
                    else:
                        opp_left -= runs_this_half

                n_plays = rng.randint(3, 6)
                for _ in range(n_plays):
                    t += timedelta(minutes=rng.randint(2, 5))
                    scored = runs_this_half > 0 and rng.random() < 0.5
                    cap = rng.randint(0, 60)
                    if scored:
                        runs_this_half -= 1
                        if batting_is_mets and home:
                            run_home += 1
                        elif batting_is_mets and not home:
                            run_away += 1
                        elif not batting_is_mets and home:
                            run_away += 1
                        else:
                            run_home += 1
                        event = rng.choice(EVENTS_SCORING)
                        cap = rng.randint(78, 99)  # scoring plays are dramatic
                        scoring_moments.append((t, batting_is_mets))
                    else:
                        event = rng.choice(EVENTS_OUT + EVENTS_ON)
                    events.append(
                        {
                            "event_id": event_id,
                            "game_id": game_id,
                            "inning": inning,
                            "halfInning": half,
                            "event": event,
                            "description": f"{event} in the {half} of the {inning}.",
                            "est": _est(t),
                            "home_team": home_team,
                            "visiting_team": away_team,
                            "home_score": run_home,
                            "away_score": run_away,
                            "outs": rng.randint(0, 2),
                            "people_on_base": rng.randint(0, 3),
                            "captivatingIndex": cap,
                        }
                    )
                    event_id += 1

        game_end = t + timedelta(minutes=10)

        # --- Comments: sentiment tracks the Mets' run differential over time.
        n_comments = rng.randint(60, 140)
        span = (game_end - first_pitch).total_seconds()
        # Precompute a timeline of Mets lead from events.
        ev_for_game = [e for e in events if e["game_id"] == game_id]
        for _ in range(n_comments):
            offset = rng.random() * span
            ts = first_pitch + timedelta(seconds=offset)
            # Mets lead at this moment.
            lead = 0
            for e in ev_for_game:
                if datetime.strptime(e["est"], "%Y-%m-%d %H:%M:%S") <= ts:
                    lead = (e["home_score"] - e["away_score"]) * (1 if home else -1)
                else:
                    break
            # Bias sentiment by current lead, with noise.
            roll = rng.random() + lead * 0.08
            if roll > 0.62:
                label, score, line = (
                    "positive",
                    round(rng.uniform(0.55, 0.99), 4),
                    rng.choice(POSITIVE_LINES),
                )
            elif roll < 0.42:
                label, score, line = (
                    "negative",
                    round(rng.uniform(0.55, 0.99), 4),
                    rng.choice(NEGATIVE_LINES),
                )
            else:
                label, score, line = (
                    "neutral",
                    round(rng.uniform(0.30, 0.60), 4),
                    rng.choice(NEUTRAL_LINES),
                )
            comments.append(
                {
                    "id": comment_id,
                    "game_id": game_id,
                    "author": rng.choice(AUTHORS),
                    "text": line,
                    "created_est": _est(ts),
                    "sentiment": label,
                    "sentiment_score": score,
                }
            )
            comment_id += 1

        # Reaction bursts: a flurry of strong comments right after each run,
        # so the crowd visibly swings (drives the "Biggest Moments" feature).
        for st, mets_scored in scoring_moments:
            for _ in range(rng.randint(5, 9)):
                ts = st + timedelta(seconds=rng.randint(10, 300))
                if mets_scored:
                    label, line = "positive", rng.choice(POSITIVE_LINES)
                else:
                    label, line = "negative", rng.choice(NEGATIVE_LINES)
                comments.append(
                    {
                        "id": comment_id,
                        "game_id": game_id,
                        "author": rng.choice(AUTHORS),
                        "text": line,
                        "created_est": _est(ts),
                        "sentiment": label,
                        "sentiment_score": round(rng.uniform(0.8, 0.99), 4),
                    }
                )
                comment_id += 1

    comments.sort(key=lambda c: c["created_est"])
    return (
        pd.DataFrame(games),
        pd.DataFrame(events),
        pd.DataFrame(comments),
        pd.DataFrame(posts),
    )


def main(out_root: str = "data", team: str = TEAM):
    games_df, events_df, comments_df, posts_df = build_team(team)
    out_dir = os.path.join(out_root, team)
    os.makedirs(out_dir, exist_ok=True)
    games_df.to_parquet(os.path.join(out_dir, "sample_games.parquet"), index=False)
    events_df.to_parquet(
        os.path.join(out_dir, "sample_game_events.parquet"), index=False
    )
    comments_df.to_parquet(
        os.path.join(out_dir, "sample_comments.parquet"), index=False
    )
    posts_df.to_parquet(os.path.join(out_dir, "sample_posts.parquet"), index=False)
    print(
        f"Wrote sample data for {team} to {out_dir}/ "
        f"({len(games_df)} games, {len(events_df)} events, {len(comments_df)} comments)"
    )


if __name__ == "__main__":
    main()
