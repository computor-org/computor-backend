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
ANALYTICS_CONTAINER_UID=1000
ANALYTICS_CONTAINER_GID=1000
ANALYTICS_SOURCE_NAME=green
ANALYTICS_SOURCE_DATABASE_URL=
ANALYTICS_EXPORT_CHUNK_SIZE=100000
ANALYTICS_REFRESH_COURSE_ID=
```

`ANALYTICS_SOURCE_DATABASE_URL` must use a read-only source database account.
Keep it server-side. Do not expose it to frontend builds, generated clients, or
browser-visible configuration.

`ANALYTICS_ROOT` is the path inside the backend container. `ANALYTICS_HOST_ROOT`
is the host bind mount. In a single-host deployment they can point to the same
directory.

`analytics-permissions` prepares `ANALYTICS_HOST_ROOT` before the backend starts.
It creates `raw`, `duckdb`, and `jobs`, then assigns them to
`ANALYTICS_CONTAINER_UID:ANALYTICS_CONTAINER_GID`. The production API image runs
as UID/GID `1000`.

## Production Refresh

Run the checked-in wrapper on the analytics host:

```bash
bash scripts/analytics-prod/refresh.sh
```

The wrapper reads `.env`, verifies compose configuration, runs the
`analytics-permissions` service, and starts a short-lived backend container for
`computor_backend.scripts.analytics_refresh`. The source database URL stays in
the service environment from `.env`; it is not passed as a command argument. The
backend service writes the same job JSON and DuckDB/Parquet files as the API
refresh endpoint.

Set `ANALYTICS_REFRESH_COURSE_ID` in `.env` before running it. Optional refresh
settings are also env-only:

```text
ANALYTICS_REFRESH_SOURCE_NAME=green
ANALYTICS_REFRESH_RUN_ID=
ANALYTICS_REFRESH_SUBMISSION_CUTOFF=
ANALYTICS_REFRESH_GRADING_CUTOFF=
ANALYTICS_REFRESH_TABLES=
```

If the source database is only reachable through SSH, set the tunnel variables
in `.env` and keep the database password in `ANALYTICS_SOURCE_DATABASE_URL`:

```text
ANALYTICS_SOURCE_TUNNEL_ENABLED=true
ANALYTICS_SOURCE_TUNNEL_SSH_TARGET=
ANALYTICS_SOURCE_TUNNEL_BIND=
ANALYTICS_SOURCE_TUNNEL_LOCAL_PORT=15432
ANALYTICS_SOURCE_TUNNEL_REMOTE_HOST=127.0.0.1
ANALYTICS_SOURCE_TUNNEL_REMOTE_PORT=5432
ANALYTICS_SOURCE_TUNNEL_GSSAPI=true
ANALYTICS_SOURCE_TUNNEL_IDENTITY_FILE=
```

For a persistent tunnel, install
`ops/systemd/computor-analytics-source-tunnel.service` and put host-specific
values in `/etc/computor/analytics-source-tunnel.env`. That file must define
`COMPUTOR_DEPLOY_DIR` and the same `ANALYTICS_SOURCE_TUNNEL_*` variables. The
systemd unit loads that file after `.env`, so host-local values override blank
template entries.

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
