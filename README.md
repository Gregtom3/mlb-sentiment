# mlb-sentiment

[![Python CI](https://github.com/Gregtom3/mlb-sentiment/actions/workflows/ci.yml/badge.svg)](https://github.com/Gregtom3/mlb-sentiment/actions/workflows/ci.yml)

Quantifying how different MLB fan bases respond to in-game events.

`mlb-sentiment` pairs play-by-play data from the MLB Stats API with the comment
streams of team subreddit game threads, scores each comment for sentiment, and
publishes an interactive **static dashboard** — no database, no cloud services,
no running server.

## Architecture

The whole thing is a batch pipeline that ends in flat files served from a CDN.
Because the data only changes once a day, there is no need for a live backend.

```
            (GitHub Action, nightly)
Reddit game threads ─┐
                     ├─► fetch + sentiment scoring ─► Parquet (data/<TEAM>/)
MLB Stats API ───────┘                                     │
                                                           ▼
                                  DuckDB reads the Parquet, computes aggregates
                                                           │
                                                           ▼
                                            JSON payloads (site/data/*.json)
                                                           │
                                                           ▼
                              static dashboard (HTML/CSS + hand-rolled SVG charts)
                                                           │
                                                           ▼
                                        GitHub Pages  ($0, CDN-fast, no server)
```

- **Fetch** (`mlb_sentiment` package / CLI): pull a team's game-thread post(s)
  and comments, plus the game's events and final score, and label each comment
  `positive` / `neutral` / `negative`.
- **Build** (`pipeline/build_site_data.py`): DuckDB reads the accumulated
  Parquet and emits one compact JSON file per team.
- **Serve** (`site/`): a dependency-free single-page dashboard reads those JSON
  files. The charts are plain SVG drawn in vanilla JS — no charting CDN.

## Project layout

```
src/mlb_sentiment/        Installable package (the `mlb-sentiment` CLI)
├── cli.py                `upload` command — fetch + score + write Parquet
├── config.py             Reddit (PRAW) client
├── info.py               Team metadata, subreddit map, statsapi lookups
├── utility.py            Timezone helpers
├── fetch/                Pull data from Reddit (reddit.py) and MLB (mlb.py)
├── database/             Serialize fetched data to Parquet
└── models/process.py     Pluggable sentiment models

pipeline/                 Data build (replaces the old Azure Synapse jobs)
├── build_site_data.py    DuckDB: Parquet -> site/data/*.json
└── sample_data.py        Generate a realistic week of demo data offline

site/                     Static dashboard (deployed to GitHub Pages)
├── index.html
├── css/style.css
├── js/charts.js          Tiny SVG charting toolkit (no dependencies)
└── js/app.js             Loads JSON, renders the page

data/<TEAM>/              Committed Parquet datasets that feed the build
tests/                    pytest suite (incl. a hermetic pipeline test)
```

## Installation

```bash
pip install -e .            # core package + CLI (pandas, duckdb, praw, …)
pip install -e .[models]    # adds the sentiment models (VADER, transformers)
pip install -r requirements.txt   # CPU build of torch (for transformer models)
pip install -e .[dev]       # tooling: pytest, black, flake8, mypy (+ models)
```

Requires Python ≥ 3.8.10.

## Configuration

Only Reddit credentials are needed (loaded from a local `.env` via
`python-dotenv`, or from GitHub Actions secrets):

| Variable | Used for |
| --- | --- |
| `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` | Reddit (PRAW) client |

There is no Azure, Synapse, or database configuration — that has been retired.

## CLI usage

```bash
# Fetch + score yesterday's Mets game thread into data/NYM/
mlb-sentiment upload \
    --team-acronym NYM \
    --yesterday \
    --comments-limit 0 \
    --sentiment-model twitter-roberta-base-sentiment
```

Options (`mlb-sentiment upload --help` for the full list):

- `--team-acronym` – team to fetch, e.g. `NYM` (required)
- `--date MM/DD/YYYY` / `--yesterday` – which day to fetch
- `--comments-limit N` – cap comments per sort order (`0` = all)
- `--sentiment-model` – `null`, `vader`, `distilbert-base-uncased-finetuned-sst-2-english`, or `twitter-roberta-base-sentiment`
- `--data-dir` – output root (default `data/`)

Output goes to `data/<TEAM>/<TEAM>_<YYYY-MM-DD>_{games,game_events,comments,posts}.parquet`.

## Build & view the dashboard locally

```bash
# 1. (optional) generate a synthetic week of Mets data for a quick demo
python pipeline/sample_data.py

# 2. build the JSON payloads from whatever is in data/
python pipeline/build_site_data.py        # -> site/data/*.json

# 3. serve the static site
python -m http.server -d site 8000        # then open http://localhost:8000
```

## Deployment

`.github/workflows/deploy.yml` rebuilds the JSON from the committed Parquet and
publishes `site/` to **GitHub Pages** on every push to `main` that touches
`data/`, `site/`, or `pipeline/`. Enable Pages once via *Settings → Pages →
Source: GitHub Actions*.

## Automation

`.github/workflows/scheduled.yml` runs daily at 6 a.m. Eastern: it fetches the
previous day's data for each tracked team, writes Parquet under `data/`, and
commits it back to `main`. That commit triggers the deploy workflow, so the
published dashboard stays current with no manual steps.

## Development

```bash
black .                            # formatting
flake8 .                           # linting
python pipeline/sample_data.py     # hermetic fixtures
pytest tests/test_pipeline.py      # pipeline tests (no network needed)
pytest                             # full suite (Reddit tests need credentials)
```

`.github/workflows/ci.yml` runs the lint, format, and pipeline checks on every
push and pull request to `main`.
