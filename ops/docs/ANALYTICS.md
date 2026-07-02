# Analytics

The lecturer analytics dashboard reads a **local reporting store** (DuckDB) built
from periodic **Parquet snapshots** of this system's own backend Postgres.

- The refresh job connects to Postgres, exports the relevant tables to Parquet,
  and (re)builds a DuckDB database for report reads.
- Browser requests only hit the backend API. Report endpoints read DuckDB; they
  do not run analytical queries against Postgres.
- **Snapshots are taken from this system's own Postgres** — there is no separate
  analytics instance and no SSH source-tunnel. (This differs from the two-machine
  setup on `release/2026.10`, where the source was another host reached over a
  tunnel.)

## Runtime configuration

All variables live in `.env` (see `ops/environments/.env.common.template`). Sane
defaults mean you normally only need to set `ANALYTICS_HOST_ROOT`:

```text
ANALYTICS_ROOT=/srv/computor/analytics          # path inside the API container
ANALYTICS_HOST_ROOT=/srv/computor/analytics      # host bind mount
ANALYTICS_CONTAINER_UID=1000                      # API image runs as uid/gid 1000
ANALYTICS_CONTAINER_GID=1000
ANALYTICS_SOURCE_NAME=green                        # snapshot label only
ANALYTICS_EXPORT_CHUNK_SIZE=100000
ANALYTICS_SOURCE_DATABASE_URL=                     # blank → the backend's own DB
```

`ANALYTICS_SOURCE_DATABASE_URL` is **left blank by default**; the backend then
snapshots its own Postgres (built from `POSTGRES_*`). The export always runs in a
read-only transaction (`default_transaction_read_only=on` + `BEGIN READ ONLY`),
so reusing the backend role cannot write. Set it only to override with a
dedicated read-only role, e.g.
`postgresql+psycopg2://ro_user:pw@postgres:5437/computor`.

`analytics-permissions` (a one-shot init service in `docker-compose.prod.yaml`)
creates `raw/`, `duckdb/`, and `jobs/` under `ANALYTICS_HOST_ROOT` and chowns
them to `ANALYTICS_CONTAINER_UID:GID` before the API starts.

## Building a snapshot

Two ways to run a refresh:

1. **From the dashboard** — a lecturer (or admin) clicks *Update data* on a
   course's analytics page. This calls `POST /analytics/courses/{id}/refresh`,
   which runs the export in the background and reports job status.
2. **CLI / cron** — run the one-shot entrypoint inside the API container:

   ```bash
   docker compose run --rm --no-deps uvicorn \
     python -m computor_backend.scripts.analytics_refresh
   ```

   It reads `ANALYTICS_REFRESH_COURSE_ID` (and the optional
   `ANALYTICS_REFRESH_*` cutoff/table settings) from the environment.

## Storage layout

```text
/srv/computor/analytics/
  raw/source=<source>/run=<run_id>/table=<table>/*.parquet
  duckdb/analytics.duckdb
  jobs/*.json
```

The refresh writes a full snapshot for the selected tables and replaces the
DuckDB tables from that snapshot. Job metadata records row counts and source
high-water marks.

## Access boundary

Analytics access is denied by default. Course read endpoints require a staff role
(`_tutor`+) on that course; refresh requires lecturer-level access (`_lecturer`+).
Administrators bypass the course filter.
