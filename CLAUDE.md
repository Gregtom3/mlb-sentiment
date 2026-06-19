# CLAUDE.md

Project guidance for working in this repo.

## What this is

`mlb-sentiment` measures how MLB fan bases react to in-game events. It pairs
MLB Stats API play-by-play with team subreddit game-thread comments, scores each
comment for sentiment, and publishes a static dashboard. **No backend, no
database, no cloud services** — it's a batch pipeline ending in flat files on
GitHub Pages.

```
CLI fetch ─► Parquet (data/<TEAM>/) ─► DuckDB build ─► JSON (site/data/) ─► static site ─► GitHub Pages
```

## Architecture

- `src/mlb_sentiment/` — installable package + `mlb-sentiment` CLI
  - `cli.py` — `upload` command: fetch + score + write Parquet to `data/<TEAM>/`
  - `fetch/reddit.py`, `fetch/mlb.py` — pull from Reddit (PRAW) and Stats API
  - `database/` — serialize to Parquet
  - `models/process.py` — pluggable sentiment models (vader / HF transformers).
    **Imports are lazy** so importing the fetch pipeline doesn't pull in torch.
  - `info.py` — `SUBREDDIT_INFO` is the single source of truth for teams
- `pipeline/build_site_data.py` — DuckDB: `data/**` → `site/data/<TEAM>.json` + `manifest.json`
- `pipeline/verify_teams.py` — hand-triggered diagnostic (see Verify Team Info workflow)
- `pipeline/sample_data.py` — synthetic data for offline dev (never committed)
- `site/` — dependency-free dashboard: vanilla-JS SVG charts (`js/charts.js`),
  app logic (`js/app.js`), scoreboard theme (`css/style.css`). Fonts via Google
  Fonts; **no charting CDN** (charts are hand-drawn SVG).

## Common commands

```bash
pip install -e .[dev]                 # package + tooling (+ sentiment models)
python pipeline/sample_data.py        # generate synthetic data into data/NYM/
python pipeline/build_site_data.py    # data/** -> site/data/*.json
python -m http.server -d site 8000    # preview the dashboard locally
black .  &&  flake8 .                  # format + lint (CI gate)
pytest tests/test_pipeline.py         # hermetic pipeline test (no network)
pytest                                # full suite (Reddit tests need credentials)
```

## Workflows (.github/workflows)

- `ci.yml` — lint, format, hermetic pipeline test, full pytest (on push/PR to main)
- `scheduled.yml` — **Daily Data Refresh**, cron `0 10 * * *` (~6am Eastern in
  season). Fetches recent days for every team in `PROCESSED_TEAMS`, commits
  Parquet to `main`. `workflow_dispatch` accepts a `days` input (default 1) to
  backfill N days.
- `deploy.yml` — **Deploy Dashboard**: rebuilds JSON and publishes `site/` to
  Pages. Triggered by pushes to `data/`/`site/`/`pipeline/`, and by a
  `workflow_run` on Daily Data Refresh completion (a `GITHUB_TOKEN` push can't
  trigger other workflows, so the chain relies on that `workflow_run`).
- `verify.yml` — **Verify Team Info**: checks every team's abbreviation,
  subreddit, and game-thread retrieval; writes a report to the job summary.

## Data storage (decision: leave as-is)

Raw Parquet is **committed to the `main` branch** under `data/<TEAM>/`. It is the
source of truth; `site/data/*.json` is a gitignored build artifact rebuilt on
every deploy. Synthetic sample data (`data/**/sample_*.parquet`) is gitignored
and must never be committed (it would pollute real team data in the build).

**Known tradeoff (accepted):** daily commits of binary Parquet grow git history
unbounded (~a few MB/day ≈ ~0.5–1 GB per season; git never reclaims deleted
history). Fine for now. **When the repo approaches ~1 GB**, migrate raw Parquet
off git history — preferred options, in order:
1. Store raw Parquet as **GitHub Release assets** (outside git history, replaceable).
2. **Retention window**: keep ~60–90 days of raw Parquet, roll older data into a
   compact committed aggregate (the dashboard only needs top/bottom-N comments
   long-term, not every comment), then drop the raw.

Until then, no action needed.

## Conventions / gotchas

- `SUBREDDIT_INFO` keys are **Stats API abbreviations** (Arizona is `AZ`, not
  `ARI`; White Sox `CWS`; Washington `WSH`). The Athletics (`ATH`) are
  intentionally omitted — no subreddit reliably posts their game threads.
- `game_thread_user` is **optional**: set it to a team's game-thread bot for a
  precise pull; omit it to fall back to scanning the subreddit by title. Fetch
  tries the bot first, then the scan.
- Run **Verify Team Info** after changing any team's subreddit/bot — it confirms
  the subreddit exists and a recent game thread is retrievable, and dumps recent
  post authors/titles for anything that fails.
- Charts must stay dependency-free SVG (works offline, no CSP issues). Don't add
  a charting CDN.
- `black` runs in CI; keep edits formatted. Avoid triple-quoted-string
  reformatting churn from newer black versions.

## "Biggest Moments" — assumptions & limits

`_biggest_moments` (build_site_data) flags plays with the largest crowd mood
swing (mean sentiment in the `window_min` after a play minus the window before).
It is **association, not proven causation**, and inherits these limits — keep
them in mind before "improving" it:

- It cannot separate a play from other things happening in the same window
  (another play, a call, a broadcast moment). Reactions also lag the live feed
  (stream delay) and build during an at-bat, so the before/after split is fuzzy.
- It rests entirely on the sentiment model, which misreads sarcasm and baseball
  slang ("filthy slider" = praise) — a swing's *sign* can be wrong.
- Mitigations already in place: in-game comments only (no pre/post-game leak);
  candidates = scoring **or** dramatic event types **or** captivatingIndex≥70;
  `min_side` comments per window + a minimum swing; ranking by a
  sample-size-shrunk swing so thin windows can't top the list; a `confidence`
  flag + comment count surfaced in the UI (low-sample cards are faded). Low-
  volume teams legitimately produce few/no moments — that's correct, not a bug.
