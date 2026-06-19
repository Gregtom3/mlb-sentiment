# mlb-sentiment

[![Python CI](https://github.com/Gregtom3/mlb-sentiment/actions/workflows/ci.yml/badge.svg)](https://github.com/Gregtom3/mlb-sentiment/actions/workflows/ci.yml)

Quantifying how different MLB fan bases respond to in-game events.

`mlb-sentiment` pairs play-by-play data from the MLB Stats API with the comment
streams of team subreddit game threads, scores each comment for sentiment, and
visualizes the relationship between what happens on the field and how fans react
in a Streamlit dashboard.

## How it works

```
Reddit game threads ─┐
                     ├─► fetch ─► sentiment scoring ─► Parquet ─► Azure Blob ─► Synapse ─► Streamlit dashboard
MLB Stats API ───────┘
```

1. **Fetch** – For a given team and date, pull the subreddit game-thread post(s)
   and their comments, plus the game's events and final score from the MLB Stats
   API.
2. **Score** – Each comment is labelled `positive` / `neutral` / `negative` with
   a configurable model (see [Sentiment models](#sentiment-models)).
3. **Store** – Results are written to Parquet and (optionally) uploaded to Azure
   Blob Storage, where they are surfaced to Azure Synapse as external tables.
4. **Visualize** – `dashboard/app.py` is a Streamlit app that reads from Synapse
   and renders per-game and per-team sentiment widgets.

## Project layout

```
src/mlb_sentiment/        Installable package (the `mlb-sentiment` CLI)
├── cli.py                `upload` command — orchestrates fetch + save + upload
├── config.py             Reddit / Azure Blob / Synapse client construction
├── info.py               Team metadata, subreddit map, statsapi lookups
├── utility.py            Timezone helpers + Azure Blob upload
├── fetch/                Pull data from Reddit (reddit.py) and MLB (mlb.py)
├── database/             Serialize fetched data to Parquet
└── models/process.py     Pluggable sentiment models

dashboard/                Streamlit dashboard
├── app.py                Entry point / layout
├── dataloader.py         Cached Synapse queries
├── compute.py            Shared sentiment time-series helper
├── widgets/              Individual chart widgets
└── app_ci_scripts/       Aggregation jobs run on a schedule

tests/                    pytest suite (hits live Reddit / MLB APIs)
```

## Installation

```bash
pip install -e .          # core package + CLI
pip install -e .[dev]     # adds the sentiment-model dependencies (VADER, transformers)
pip install -r requirements.txt   # CPU build of torch (needed for transformer models)
```

Requires Python ≥ 3.8.10.

## Configuration

Credentials are read from environment variables (a local `.env` file is loaded
automatically via `python-dotenv`):

| Variable | Used for |
| --- | --- |
| `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` | Reddit (PRAW) client |
| `AZURE_BLOB_CONNECTION_STRING`, `AZURE_BLOB_CONTAINER` | Uploading Parquet to Azure Blob |
| `SYNAPSE_SERVER`, `SYNAPSE_DATABASE`, `SYNAPSE_USERNAME`, `SYNAPSE_PASSWORD` | Dashboard's Synapse connection |

## CLI usage

```bash
# Fetch + score yesterday's Yankees game thread and upload to Azure
mlb-sentiment upload \
    --team-acronym NYY \
    --yesterday \
    --azure \
    --comments-limit 0 \
    --sentiment-model twitter-roberta-base-sentiment
```

Key options (`mlb-sentiment upload --help` for the full list):

- `--team-acronym` – team to fetch, e.g. `NYM` (required)
- `--date MM/DD/YYYY` / `--yesterday` – which day to fetch
- `--comments-limit N` – cap comments per sort order (`0` = all)
- `--sentiment-model` – `null`, `vader`, `distilbert-base-uncased-finetuned-sst-2-english`, or `twitter-roberta-base-sentiment`
- `--azure` / `--keep-local` – upload to Azure Blob and optionally keep the local copy

### Sentiment models

| Model | Notes |
| --- | --- |
| `null` | No scoring; everything labelled neutral (fast default) |
| `vader` | Rule-based VADER compound score |
| `distilbert-base-uncased-finetuned-sst-2-english` | Hugging Face DistilBERT |
| `twitter-roberta-base-sentiment` | Hugging Face RoBERTa fine-tuned on tweets |

Teams currently covered by the subreddit map live in `SUBREDDIT_INFO`
(`src/mlb_sentiment/info.py`); teams with processed data are listed in
`PROCESSED_TEAMS`.

## Dashboard

```bash
streamlit run dashboard/app.py
```

Or via Docker (bundles the SQL Server ODBC driver needed by Synapse):

```bash
docker build -t mlb-sentiment .
docker run -p 8501:8501 --env-file .env mlb-sentiment
```

## Automation

`.github/workflows/scheduled.yml` runs daily at 6 a.m. Eastern: it uploads the
previous day's data for each processed team and then recomputes the global and
per-team aggregates consumed by the dashboard.

## Development

```bash
black .          # formatting
flake8 .         # linting
pytest           # tests (require Reddit credentials; some hit live APIs)
```

`.github/workflows/ci.yml` runs the same checks on every push and pull request
to `main`.
