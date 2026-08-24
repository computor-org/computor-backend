# scripts/bench/ — SQL benchmarks

Two scripts that together answer "did that query change actually help?".

Everything runs against a **separate `computor_bench` database** in the same
Postgres server as the dev stack. The dev `computor` database is never written
to, and `seed_bench_db.py` refuses to drop anything not named like a bench
database.

## Run it

```bash
set -a; source .env; set +a          # both scripts need the Postgres credentials
./computor.sh up                     # Postgres must be running

python scripts/bench/seed_bench_db.py            # ~30s, ~490k rows
python scripts/bench/bench_queries.py            # timings
```

## Seeding

`seed_bench_db.py` drops and recreates `computor_bench`, runs
`alembic upgrade head` for the schema (so the benchmark reflects the migrations
as committed, including the reference rows the initial migration seeds), then
bulk-loads a synthetic course world.

At the default scale: 3 courses × 500 students × 60 assignments →
90k submission groups, 90k artifacts, 180k results, 22k grades, 11k messages.

```bash
python scripts/bench/seed_bench_db.py --scale 2       # twice the students and assignments
python scripts/bench/seed_bench_db.py --keep-schema   # reseed data, skip drop + migrate
```

Primary keys are `md5('<stable key>')::uuid`, so a table can reference another
without reading ids back and two runs at the same scale produce identical data.
Student 0 is deliberately enrolled in *every* course: the student dashboard
query runs without a course filter, so the cross-course case is the one worth
measuring.

## Measuring

`bench_queries.py` calls the real functions the API calls — not a hand-written
approximation of their SQL — with caching disabled, so both the emitted query
and the ORM materialisation are in the number.

```bash
python scripts/bench/bench_queries.py --list            # what is available
python scripts/bench/bench_queries.py -k dashboard      # a subset
python scripts/bench/bench_queries.py --explain         # EXPLAIN (ANALYZE, BUFFERS)
```

The `queries` column is the statement count for one run. It is reported
separately from wall-clock on purpose: a loop of 600 fast queries looks
tolerable over a local socket and is ruinous over a real network, so N+1
regressions show up there long before they show up in milliseconds.

### Before / after

```bash
python scripts/bench/bench_queries.py --json before.json
# ... change something ...
python scripts/bench/bench_queries.py --json after.json --baseline before.json
```

The `vs base` column is the p50 change. Reseed between runs only if the change
touches the schema — and if you do, reseed for *both* sides of the comparison.

## Caveats

Synthetic distributions are not production distributions. The data here is
uniform: every student has the same number of submissions, grades cycle through
the four statuses in order, and nothing is skewed. That is good enough to catch
a sequential scan, a missing index or an N+1 loop, and not good enough to
predict absolute production latency. Treat the numbers as relative.
