# Analytics

Analytics runs on a separate reporting store. The backend refresh job reads a
source database with a read-only SQL user, writes raw Parquet snapshots, and
builds a DuckDB database for report reads.

Browser requests only hit the backend API. Report endpoints read DuckDB. They
do not connect to the source database.

## Local System Test

Run the full local cycle from the repository root:

```bash
bash scripts/analytics-local/run-system-test.sh
```

The command starts isolated source and analytics stacks, seeds the source,
checks that the analytics SQL role cannot write, refreshes the analytics store,
checks Parquet and DuckDB output, and removes the local data root.

## Runtime Configuration

Set these variables on the analytics host:

```text
ANALYTICS_ROOT=/srv/computor/analytics
ANALYTICS_HOST_ROOT=/srv/computor/analytics
ANALYTICS_SOURCE_NAME=green
ANALYTICS_SOURCE_DATABASE_URL=
ANALYTICS_EXPORT_CHUNK_SIZE=100000
```

`ANALYTICS_SOURCE_DATABASE_URL` must use a read-only source database account.
Keep it server-side. Do not expose it to frontend builds, generated clients, or
browser-visible configuration.

`ANALYTICS_ROOT` is the path inside the backend container. `ANALYTICS_HOST_ROOT`
is the host bind mount. In a single-host deployment they can point to the same
directory.

## Storage Layout

```text
/srv/computor/analytics/
  raw/source=<source>/run=<run_id>/table=<table>/*.parquet
  duckdb/analytics.duckdb
  jobs/*.json
```

The refresh job writes a full snapshot for the selected tables and replaces the
DuckDB tables from that snapshot. Job metadata records row counts and source
high-water marks. Incremental import can use those marks later, but the current
path is full-snapshot refresh.

## Access Boundary

Analytics access is denied by default. Course read endpoints require a staff
role on that course. Refresh endpoints require lecturer-level course access.
Administrators bypass the course filter.
