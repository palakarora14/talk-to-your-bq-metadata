## Development

## Requirements

- Docker
- Python 3.13+ + [uv](https://github.com/astral-sh/uv)
- [Vault CLI](https://developer.hashicorp.com/vault/install) — for `auto/run-local`
  - macOS: `brew tap hashicorp/tap && brew install hashicorp/tap/vault`
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) — for Vault AWS auth
  - macOS: `brew install awscli`
- AWS credentials configured (`aws configure` or an active SSO session) with access to the `datacat-metastore-bigquery-reader-dev-roleset`

Directory Structure:

```text
.
|-- pyproject.toml       Project dependencies and Python tool configuration
|-- docker-compose.yml   Container orchestration for the UI + vector DB services
|-- Dockerfile.ui        UI container image
|-- auto/                Auto scripts (start/stop/restart UI, run ingestion)
|-- bin/                 Vendored lint binaries (hadolint, shellcheck)
|-- dev/                 Run development tasks outside a container
|-- docs/
|   |-- ui/              Poster, Figma architecture, and demo videos
|-- src/
|   |-- client/          BigQuery client
|   |-- config/          Constants, GCP credentials/permissions
|   |-- hackday_45_talk_to_your_data/
|       |-- api/         FastAPI app (chat endpoint, session handling)
|       |-- chains/      RAG chains and reranker
|       |-- library/     Shared helpers (env, logging, serializer)
|       |-- ui/          Streamlit app
|       |-- main.py      CLI entrypoint
|       |-- vector_store.py   ChromaDB read/write helpers
|-- chroma_db/            Local ChromaDB store (gitignored)
|-- tests/
    |-- hackday_45_talk_to_your_data/   pytest unit tests
```

## How the system works

The project has two phases:

1. **Ingestion** — scrape BigQuery metadata and store it in ChromaDB (vector DB). Run once, or on a schedule.
2. **Query** — the Streamlit UI sends user questions to a FastAPI backend, which retrieves relevant chunks from ChromaDB and asks Claude to synthesise an answer.

See [README.md](README.md) for the full architecture diagram and demo videos.

---

### Environment variables — `.env`

Copy `.env.example` to `.env` and fill in your values:
```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `PORTKEY_API_KEY` | Yes (for LLM) | Portkey API key for Claude synthesis |
| `GCP_PROJECT` | No | GCP project ID (default: `rea-gcp-dp-dev`) |
| `GOOGLE_APPLICATION_CREDENTIALS` | No | Path to ADC JSON (defaults to gcloud ADC) |

The `start-ui-app` and `restart-ui-app` scripts load `.env` automatically.

---

### Running locally - `auto/run-local`

This script fetches GCP credentials and runs the CLI (`main` or `ingest` commands). It tries Vault auth first; if that fails it falls back to gcloud Application Default Credentials (ADC).

**Step 1 — Install Vault CLI** (optional, only needed for roleset-based auth)
```bash
brew tap hashicorp/tap && brew install hashicorp/tap/vault
```

**Step 2 — Install gcloud**
```bash
brew install --cask google-cloud-sdk
```

**Step 3 — Fix gcloud Python** (macOS with Python 3.14 has a libexpat incompatibility)

Add to `~/.zshrc`:
```bash
export CLOUDSDK_PYTHON=$(which python3.13)
export PATH="/opt/homebrew/share/google-cloud-sdk/bin:$PATH"
```
Then reload:
```bash
source ~/.zshrc
```

**Step 4 — Authenticate with your REA Google account**
```bash
gcloud auth application-default login
```

**Step 5 — Run ingestion**
```bash
./auto/run-local
```

With no arguments, `auto/run-local` defaults to the `ingest` subcommand. This fetches BigQuery asset catalog metadata, query history, and quota metrics from `rea-gcp-dp-dev` and upserts them into 3 local ChromaDB collections under `./chroma_db/`. See [Ingesting BigQuery metadata into ChromaDB](#ingesting-bigquery-metadata-into-chromadb) below for details.

To control the query history window:
```bash
./auto/run-local ingest --days 30
```

You can also run the `main` command directly for a quick credentials/access smoke test:
```bash
./auto/run-local main hello
```

> _Todo_: `auto/run` - to be updated later for running in a containerized environment

---

### Ingesting BigQuery metadata into ChromaDB

`ingest` populates 3 ChromaDB collections from BigQuery, stored locally under `./chroma_db/` (gitignored):

| Collection | Source | Notes |
|---|---|---|
| `bq_asset_catalog` | `BigQueryClient.fetch_bq_asset_catalog_metadata()` | Tables/columns from `INFORMATION_SCHEMA` |
| `bq_query_history` | `BigQueryClient.fetch_bq_query_history(days=...)` | Respects `--days` |
| `bq_quota_metrics` | `BigQueryClient.fetch_bq_quota_metrics()` | Fixed 7-day window (not affected by `--days`) |

Embeddings are generated locally via `sentence-transformers` (`all-MiniLM-L6-v2`) — no `OPENAI_API_KEY` or external API calls required for ingestion.

```bash
./auto/run-local ingest --days 7
```

To re-run against a clean local Chroma store, delete `./chroma_db/` first (ChromaDB rejects mismatched embedding functions on existing collections).

---

### Running the UI — `auto/start-ui-app`

The Streamlit chat UI runs inside Docker (via `Dockerfile.ui`). GCP credentials are forwarded automatically from your host.

**Prerequisites:** complete Steps 1–4 above (gcloud ADC login), and have Docker running.

**Step 1 — (Optional) Set your Portkey API key**

The app uses a RAG pipeline: every query first retrieves relevant BigQuery metadata chunks from Chroma, then passes them to Claude as context to synthesise a natural-language answer. Without an API key the LLM synthesis step is skipped and the raw retrieved chunks are returned directly instead.
```bash
export PORTKEY_API_KEY=my-portkey-api-key
```

**Step 2 — Start the UI**
```bash
./auto/start-ui-app
```

The script will:
- Build the `Dockerfile.ui` image (cached after the first run)
- Mount your ADC credentials into the container read-only
- Expose the app on **http://localhost:8501**

**Step 3 — Open the app**

Navigate to [http://localhost:8501](http://localhost:8501) in your browser.

Use the sidebar to filter by time range and dataset. The four quick-prompt buttons cover the most common queries (costliest queries, unpartitioned tables, frequent datasets, asset listing).

Press `Ctrl+C` in the terminal to stop the container.

---

### Stopping the UI — `auto/stop-ui-app`

```bash
./auto/stop-ui-app
```

Stops and removes the `api` and `ui` containers.

---

### Restarting the UI — `auto/restart-ui-app`

```bash
./auto/restart-ui-app
```

Tears down the running containers, rebuilds the image, and starts fresh. Equivalent to running `stop-ui-app` then `start-ui-app`. GCP credentials are forwarded automatically from your host (same as `start-ui-app`).

---

#### Other Steps-

**Creating the virtual environment:**

`uv sync`

**Installing a package:**

`uv add <package>`

**Installing a dev package:**

`uv add --group dev <package>`

Uninstalling is the same, but replace `add` with `remove`

**Running `dev` scripts**

In order to run the dev scripts, you want to be in the correct python virtual environment

You can do this by running it with `uv run` like so

`uv run dev/lint-python`

Alternatively, you can activate the virtual environment in the shell and then run the commands regularly

```shell
source .venv/bin/activate

dev/lint-python
```
