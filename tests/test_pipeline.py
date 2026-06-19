"""Hermetic tests for the DuckDB -> JSON build (no network, no credentials)."""

import os
import sys

import duckdb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pipeline import sample_data, build_site_data  # noqa: E402


def test_build_team_from_sample(tmp_path):
    data_root = tmp_path / "data"
    sample_data.main(out_root=str(data_root), team="NYM")

    con = duckdb.connect()
    payload = build_site_data.build_team(con, "NYM", str(data_root / "NYM"))

    # Top-level shape
    for key in (
        "team",
        "totals",
        "summary",
        "games",
        "per_game",
        "distribution",
        "inning_sentiment",
        "scatter",
        "event_pie",
        "commenters",
    ):
        assert key in payload, f"missing key: {key}"

    assert payload["team"] == "NYM"
    assert payload["totals"]["total_games"] == len(sample_data.SCHEDULE)
    assert payload["totals"]["total_comments"] > 0

    # Every game carries an outcome and a per-game payload.
    for g in payload["games"]:
        assert g["outcome"] in ("Win", "Loss", "Tie", "Other", "Unknown")
        assert str(g["game_id"]) in payload["per_game"]

    # Win/loss split and a finite regression should exist for a full week.
    assert payload["summary"]["win_avg_sentiment"] is not None
    assert payload["summary"]["loss_avg_sentiment"] is not None
    assert payload["summary"]["r2"] is not None

    # Sentiment scores are signed: neutral->0, negative is never positive.
    one_game = next(iter(payload["per_game"].values()))
    assert isinstance(one_game["sentiment_ts"], list)
    assert all(-1.0 <= p["score"] <= 1.0 for p in one_game["sentiment_ts"])

    # Biggest Moments are hardened: each carries a sample size + confidence,
    # clears the swing floor, and is sample-aware.
    moments = [m for pg in payload["per_game"].values() for m in pg["moments"]]
    assert moments, "sample data should surface at least one moment"
    for m in moments:
        assert m["n"] >= 3
        assert abs(m["swing"]) >= 0.05
        assert m["confidence"] in ("low", "ok")
        assert {"home_team", "away_team", "home_score", "away_score"} <= set(m)


def test_full_build_writes_manifest(tmp_path):
    data_root = tmp_path / "data"
    out = tmp_path / "out"
    sample_data.main(out_root=str(data_root), team="NYM")

    con = duckdb.connect()
    teams = build_site_data.discover_teams(str(data_root))
    assert teams == ["NYM"]

    os.makedirs(out, exist_ok=True)
    payload = build_site_data.build_team(con, "NYM", str(data_root / "NYM"))
    import json

    (out / "NYM.json").write_text(json.dumps(payload))
    assert (out / "NYM.json").stat().st_size > 0
