# Local analytics harness

This harness runs two isolated local Computor data instances for analytics
development.

- Source instance: mimics green production as a read-only SQL source.
- Blue instance: reserved for analytics import, API, and system tests.

The scripts use separate Docker Compose project names. Containers, networks,
ports, and data roots stay isolated from the normal development stack.

## Commands

```bash
bash scripts/analytics-local/setup.sh
bash scripts/analytics-local/seed.sh
bash scripts/analytics-local/test.sh
bash scripts/analytics-local/teardown.sh
```

Run the complete setup, seed, test, and teardown cycle with:

```bash
bash scripts/analytics-local/run-system-test.sh
```

Default local ports:

| Instance | Postgres | Redis | MinIO API | MinIO Console |
| --- | ---: | ---: | ---: | ---: |
| source | 55432 | 56379 | 59000 | 59001 |
| blue | 55433 | 56380 | 59002 | 59003 |

Default data root:

```text
/tmp/computor-analytics-local
```

Override `ANALYTICS_LOCAL_DATA_ROOT` to use a different path. Teardown deletes
custom roots only when `COMPUTOR_ANALYTICS_LOCAL_CONFIRM_DELETE=1` is set.

The source seed creates a read-only user for analytics imports:

```text
user: analytics_reader
password: analytics_reader_secret
```

These credentials are local test credentials only.

`test.sh` checks the read-only source role, exports the seeded source snapshot
through the analytics service, writes Parquet and DuckDB files under the local
blue data root, and validates the summary, student list, timeline, and report
read models.
