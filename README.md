# Last.fm Data Pipeline

A small end-to-end ETL pipeline that pulls listening history (scrobbles) from the Last.fm API, cleans and validates it, and loads it into PostgreSQL.

The pipeline is containerized with Docker and orchestrated with Docker Compose, and is designed for incremental ingestion, persistent storage, data quality, and analytics.

## Overview

The pipeline runs in four stages:

```text
Extract → Transform → Validate → Load
```

1. **Extract** - Pulls recent or full scrobble history from the Last.fm API and saves the raw response as JSON.

2. **Transform** - Flattens and cleans the raw JSON into a tabular CSV.

3. **Validate** - Checks each row for missing fields or invalid timestamps, splitting records into valid and rejected sets.

4. **Load** - Loads valid scrobbles into PostgreSQL and skips duplicates.

Each run is incremental by default: it starts from the latest scrobble already stored in the database. This allows the pipeline to run repeatedly and build a permanent archive while avoiding duplicate records.

## Tech Stack

| Technology | Role / Use Case |
|---|---|
| **Python** | Extraction, transformation, validation, orchestration |
| **SQL** | Database schema and queries |
| **PostgreSQL** | Relational database and data storage |
| **Docker** | Containerization and reproducible runtime environment |
| **Docker Compose** | Multi-container orchestration |
| **Pandas** | Data transformation and validation |
| **Last.fm API** | Data source |
| **pytest** | Testing |
| **python-dotenv** | Configuration and secrets |
| **Git** | Version control |

## Project Structure

```text
.
├── Dockerfile              # Pipeline container definition
├── docker-entrypoint.py    # Fixes ./data ownership, then drops root → appuser
├── docker-compose.yml      # PostgreSQL + pipeline services
├── .dockerignore           # Files excluded from Docker build context
├── requirements.in         # Direct Python dependencies
├── requirements.txt        # Pinned dependency lockfile
├── requirements-dev.txt    # Development and testing dependencies
│
├── src/
│   ├── auth.py             # One-time flow to obtain a Last.fm session key
│   ├── config.py           # Paths, directories, and logging setup
│   ├── lastfm.py           # Last.fm request-signing helper
│   ├── extract.py          # Last.fm API → raw JSON
│   ├── transform.py        # Raw JSON → cleaned CSV
│   ├── validate.py         # Cleaned CSV → valid / rejected CSVs
│   ├── load.py             # Valid CSV → PostgreSQL
│   └── pipeline.py         # Orchestrates all stages
│
├── sql/
│   ├── 01-timezone.sh     # Sets the PostgreSQL database timezone on initialization
│   ├── 02-schema.sql      # scrobbles table definition
│   └── views.sql           # Analytics views (top artists, tracks, daily/hourly/monthly)
│
├── scripts/
│   ├── docker-setup.sh     # Sets up Docker infrastructure
│   ├── local-setup.sh      # Sets up PostgreSQL for local execution
│   └── setup_timezone.py   # Detects/selects timezone and saves it to .env
│
├── data/
│   ├── raw/                # Raw API responses (JSON)
│   ├── processed/          # Transformed & validated CSVs
│   ├── quarantine/         # Rejected rows with reasons
│   └── logs/               # Pipeline run logs
│
└── tests/
    ├── test_lastfm.py      # Request-signing tests
    ├── test_validate.py    # Validation logic tests
    ├── test_transform.py   # Transform / cleaning logic tests
    ├── test_extract.py     # Extract stage tests 
    └── test_load.py        # Load stage tests
```

## Setup

Both execution paths require a Last.fm API account and a .env file with the required configuration. Then choose **Docker** or **Manual / local** execution.

### 1. Create a Last.fm API account

Go to the [Last.fm API account page](https://www.last.fm/api/account/create), log in to your Last.fm account, and create an API account to obtain your **API key** and **API secret**.

### 2. Configure environment variables

Create a `.env` file in the project root:

```env
# Last.fm API credentials
LASTFM_API_KEY=your_api_key
LASTFM_API_SECRET=your_api_secret
LASTFM_USERNAME=your_lastfm_username

# Filled in automatically after running the auth flow
LASTFM_SESSION_KEY=

# Filled in automatically by scripts/setup_timezone.py
DB_TIMEZONE=

# PostgreSQL connection
DB_NAME=lastfm
DB_USER=your_user
DB_PASSWORD=your_password

# Only needed for manual/local runs - Docker Compose overrides these
DB_HOST=localhost
DB_PORT=5432
```

### 3. Authenticate with Last.fm

Install the project dependencies and run the one-time authentication flow:

```bash
pip install -r requirements.txt
python -m src.auth
```

The command will print a URL. Open the URL in your browser, authorize the application, then return to the terminal and press Enter.

The session key is saved automatically to `.env` as `LASTFM_SESSION_KEY`.

---

## Docker

Requires **Docker Desktop** on macOS/Windows or **Docker Engine + the Docker Compose plugin** on Linux.

On macOS or Windows, install Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop/) and make sure it is running before continuing. Otherwise, `docker compose` commands will fail to connect to the Docker daemon.

### First run

Run the Docker setup script:

```bash
./scripts/docker-setup.sh
```

The setup script:

1. Detects your timezone or asks you to select one.
2. Saves `DB_TIMEZONE` to `.env`.
3. Builds the pipeline image.
4. Starts PostgreSQL in the background and waits until it is healthy.

The pipeline is not run during setup.


### File ownership on Linux

The pipeline container starts as root, fixes ownership of /app/data to match the bind-mounted ./data directory, then drops privileges to appuser before running the actual command. This avoids UID-mismatch permission errors on Linux, where bind mounts preserve host UIDs. No action is needed — this happens automatically on every run.

### Incremental runs

Run the pipeline to fetch new scrobbles:

```bash
docker compose run --rm pipeline
```

### Full history

Fetch and store the entire listening history:

```bash
docker compose run --rm pipeline python -m src.pipeline --full-history
```

### Check the database

#### View total number of scrobbles

```bash
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT COUNT(*) FROM scrobbles;"'
```

#### Show the 50 most recent scrobbles

```bash
docker compose exec db sh -c 'psql -P pager=off -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT artist, track, album, timestamp FROM scrobbles ORDER BY timestamp DESC LIMIT 50;"'
```

The pager=off option prints all 50 rows directly in the terminal instead of opening a pager for scrolling through the output.

### Stop the services

```bash
docker compose down
```

This removes the containers and network but preserves the PostgreSQL data volume.

The local `./data` directory is mounted into the pipeline container, so generated JSON, CSV, quarantine, and log files remain on the host.

### Run individual stages

Individual stages can also be executed inside the pipeline container:

```bash
docker compose run --rm pipeline python -m src.extract                 # newest page only
docker compose run --rm pipeline python -m src.extract --incremental   # fetch since last stored scrobble
docker compose run --rm pipeline python -m src.extract --full-history  # fetch entire history
docker compose run --rm pipeline python -m src.transform
docker compose run --rm pipeline python -m src.validate
docker compose run --rm pipeline python -m src.load
```

---

## Running Locally

**Requirements:** Python 3.14+ and a running PostgreSQL instance.

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up PostgreSQL

Run the local setup script:

```bash
./scripts/local-setup.sh
```

### 3. Run the pipeline

Run the incremental pipeline:

```bash
python -m src.pipeline
```

Fetch and store the entire listening history:

```bash
python -m src.pipeline --full-history
```

### Run individual stages

```bash
python -m src.extract                 # newest page only, no DB required
python -m src.extract --incremental   # fetch since last stored scrobble (DB required)
python -m src.extract --full-history  # fetch entire history
python -m src.transform
python -m src.validate
python -m src.load
```

---

## Data Quality

The `validate` stage checks every row for:

- Missing artist or track
- Invalid or unparseable timestamps
- Future timestamps

Rows that fail validation are written to:

```text
data/quarantine/rejected_scrobbles.csv
```

with a `rejection_reason` column.

Valid rows proceed to the load stage.

## Testing

For development and testing, install the dev dependencies:
 
```bash
pip install -r requirements-dev.txt
```

Run the test suite with verbose output:
 
```bash
pytest -v
```
 
The `-v` flag displays each test individually with its result.
 
The test suite covers request signing, transformation, validation, extraction, and loading.

## Status

### Implemented

- Last.fm API authentication
- Incremental ingestion
- Full-history ingestion
- Data validation
- Idempotent loading
- PostgreSQL persistence
- Docker Compose setup
- Separate Docker infrastructure setup and pipeline execution
- PostgreSQL database timezone configuration
- Automatic timezone detection and manual timezone selection
- Database health checks
- Structured logging
- Automated tests for pipeline stages
- Pinned dependency management
- SQL analytics views (top artists, top tracks, daily/hourly/monthly listening)

### Planned

- Pipeline scheduling with cron/Airflow
- More analytics and reporting

## License

This project is licensed under the [MIT License](LICENSE).