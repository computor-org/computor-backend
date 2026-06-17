#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib.sh"

wait_for_postgres source compose_source
wait_for_postgres blue compose_blue

official_submissions="$(
    psql_source_reader -tAc \
        "select count(*) from submission_artifact where submit = true;"
)"
grades="$(
    psql_source_reader -tAc \
        "select count(*) from submission_grade;"
)"
late_official="$(
    psql_source_reader -tAc \
        "select count(*) from submission_artifact where submit = true and uploaded_at > timestamptz '2026-06-18 22:01:00+00';"
)"

if [[ "$official_submissions" != "5" ]]; then
    echo "Expected 5 official submissions, got ${official_submissions}" >&2
    exit 1
fi

if [[ "$grades" != "3" ]]; then
    echo "Expected 3 grades, got ${grades}" >&2
    exit 1
fi

if [[ "$late_official" != "2" ]]; then
    echo "Expected 2 late official submissions, got ${late_official}" >&2
    exit 1
fi

if psql_source_reader -c \
    "insert into course (id, title) values ('99999999-9999-4999-9999-999999999999', 'forbidden');" \
    >/tmp/computor-analytics-local-readonly-check.out 2>&1; then
    cat /tmp/computor-analytics-local-readonly-check.out >&2
    echo "analytics reader unexpectedly wrote to source database" >&2
    exit 1
fi

echo "Analytics local harness smoke test passed"
