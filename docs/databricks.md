# Deploying mlb-sentiment to Azure Databricks

This document outlines a pragmatic path to running this project on Azure using Databricks and ADLS Gen2 (Delta Lake). It focuses on minimal changes required to run the existing CLI/workflow as a scheduled Databricks job or an interactive notebook.

## High-level architecture

- Azure Storage (ADLS Gen2) for durable data (Delta tables).
- Azure Databricks workspace to run PySpark jobs and house the library.
- Azure Key Vault (optional) or Databricks Secrets to store Reddit credentials and storage/service principal secrets.
- Optional: GitHub Actions to build a wheel and upload it to Databricks.

## Key resources to create

1. Resource group
2. Storage account with Hierarchical Namespace (ADLS Gen2)
3. Databricks workspace (managed)
4. Service Principal (app registration) with storage Blob Data Contributor on the ADLS container
5. Databricks secret scope with service principal credential and Reddit API creds

## How the code integrates with Databricks

- The repository includes a small adapter at `mlb_sentiment.database.adapter` that writes game events to Delta using Spark when `USE_DELTA=true`.
- On Databricks, set the environment variable `USE_DELTA=true` for the job, and set `GAME_TABLE_PATH` to the target Delta path (e.g. `dbfs:/mnt/mlb/games` or `abfss://container@account.dfs.core.windows.net/mlb/games`).
- Secrets are stored in a Databricks secret scope and made available to the job as environment variables via cluster init scripts or by reading them within the notebook using the Databricks secrets API.

## Build & publish wheel (local)

1. Create a wheel:

```bash
# from repo root
python -m build -w
# or with poetry/other toolchain if preferred
```

2. Upload wheel to DBFS or attach as a workspace library with the Databricks UI or CLI:

- Databricks CLI example (once configured):

```bash
databricks fs cp dist/mlb_sentiment-0.1.0-py3-none-any.whl dbfs:/FileStore/libs/
```

Then in the cluster libraries, install from `dbfs:/FileStore/libs/your-whl.whl`.

## Secrets and credentials

Store the following in a secret scope:

- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_USER_AGENT`
- `SERVICE_PRINCIPAL_CLIENT_ID`
- `SERVICE_PRINCIPAL_CLIENT_SECRET`
- `STORAGE_ACCOUNT_NAME`
- `STORAGE_ACCOUNT_KEY` (or use OAuth with service principal and OAuth2 configs)

In notebooks, fetch secrets like:

```python
import os
from pyspark.dbutils import DBUtils

dbutils = DBUtils(spark)
os.environ['REDDIT_CLIENT_ID'] = dbutils.secrets.get(scope='mlb', key='REDDIT_CLIENT_ID')
# ...etc
```

## Mount ADLS Gen2 (optional)

You can mount ADLS to DBFS using a service principal; prefer using workspace mounting or ABFS(s) URIs directly from Spark with OAuth2 credentials.

## Example Databricks job (REST payload)

Set `USE_DELTA=true` in job settings (or set in notebook). Sample job spec writes games to Delta and runs analysis.

```json
{
  "name": "mlb-sentiment-job",
  "new_cluster": {
    "spark_version": "13.1.x-scala2.12",
    "node_type_id": "Standard_DS3_v2",
    "num_workers": 2
  },
  "libraries": [
    {"whl": "dbfs:/FileStore/libs/mlb_sentiment-0.1.0-py3-none-any.whl"}
  ],
  "notebook_task": {
    "notebook_path": "/Repos/your/repo/mlb_sentiment/notebooks/run_analysis",
    "base_parameters": {}
  }
}
```

## Notebook example (pseudocode)

```python
# Set up secrets
import os
from mlb_sentiment.config import load_reddit_client

os.environ['USE_DELTA'] = 'true'
os.environ['GAME_TABLE_PATH'] = 'dbfs:/mnt/mlb/games'

# load secrets via dbutils.secrets.get(...) and set REST of env

# Run fetch & save
from mlb_sentiment.fetch.mlb import fetch_mlb_events
from mlb_sentiment.database.mlb import save_game_to_db

events = fetch_mlb_events('BOS', date='07/04/2025')
save_game_to_db(events)

# Run analysis
from mlb_sentiment.models.analysis import run_sentiment_analysis
run_sentiment_analysis()
```

## CI/CD

- Use GitHub Actions to build the wheel and call Databricks REST API to upload the wheel and update job definitions. See Databricks GitHub Actions for examples.

## Notes and caveats

- Databricks runtimes include Delta and PySpark. Locally, the adapter will still import pyspark only when `USE_DELTA` is enabled and Spark is available.
- Network egress and permissions: ensure the workspace has network access to the storage account, or use a VNet injection.

## Next steps

- Create a small migration notebook to read existing SQLite DB and upsert into Delta.
- Add a small smoke-test job to verify end-to-end behavior.
