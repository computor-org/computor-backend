#!/usr/bin/env python3
"""One-off backfill of grades taxed by skipped tests (#232).

The old formula was ``passed / max(total, 1)``, so every skipped test — test
types a language does not implement, unsupported qualifications — silently
cost the student a point. The new formula excludes skips from the
denominator: ``passed / max(total - skipped, 1)``, with an all-skipped run
graded 0.0 (inconclusive, not a pass).

This recomputes ``result_value`` for stored results whose summary carries
``skipped > 0``, in both places it lives: the MinIO blob
(``results/{result_id}/result.json``) and the ``result.result`` column in
postgres. ``grade`` (manual grading) is never touched.

Usage (from the repo root, .env exported or sourced):

    set -a; source .env; set +a
    .venv/bin/python scripts/utilities/backfill_skip_result_values.py [--apply]

Without ``--apply`` it only reports what it would change. Targets the MAIN
postgres (5437), never the Coder one.
"""

import argparse
import io
import json
import os
import sys

import psycopg2
from minio import Minio

RESULTS_BUCKET = "results"


def make_minio() -> Minio:
    endpoint = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
    if endpoint.startswith("minio:"):
        endpoint = f"localhost:{os.environ.get('MINIO_API_PORT', '9000')}"
    return Minio(
        endpoint,
        access_key=os.environ["MINIO_ROOT_USER"],
        secret_key=os.environ["MINIO_ROOT_PASSWORD"],
        secure=os.environ.get("MINIO_SECURE", "false").lower() == "true",
    )


def make_db():
    host = os.environ.get("POSTGRES_HOST", "localhost")
    if host in ("postgres", "docker-postgres-1"):
        host = "localhost"
    return psycopg2.connect(
        host=host,
        port=int(os.environ.get("POSTGRES_PORT", "5437")),
        dbname=os.environ.get("POSTGRES_DB", "computor"),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def counts(blob: dict):
    s = blob.get("summary", blob)
    return (
        s.get("passed", 0),
        s.get("total", 0),
        s.get("skipped", 0),
    )


def new_result_value(passed: int, total: int, skipped: int) -> float:
    # Mirrors compute_result_value in computor_backend.tasks.temporal_base.
    if total > 0 and skipped >= total:
        return 0.0
    return passed / max(total - skipped, 1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true",
                        help="rewrite blobs and update result.result (default: dry run)")
    args = parser.parse_args()

    client = make_minio()
    if not client.bucket_exists(RESULTS_BUCKET):
        print(f"bucket {RESULTS_BUCKET!r} does not exist — nothing to backfill")
        return 0

    conn = make_db()
    seen = affected = rewritten = errors = 0
    try:
        for obj in client.list_objects(RESULTS_BUCKET, recursive=True):
            if not obj.object_name.endswith("/result.json"):
                continue
            seen += 1
            result_id = obj.object_name.split("/", 1)[0]
            try:
                response = client.get_object(RESULTS_BUCKET, obj.object_name)
                try:
                    blob = json.loads(response.read())
                finally:
                    response.close()
                    response.release_conn()
            except Exception as exc:  # noqa: BLE001 — keep walking, report at the end
                print(f"ERROR reading {obj.object_name}: {exc}", file=sys.stderr)
                errors += 1
                continue

            passed, total, skipped = counts(blob)
            if skipped <= 0:
                continue
            old = blob.get("result_value")
            new = new_result_value(passed, total, skipped)
            if old is not None and abs(old - new) < 1e-9:
                continue

            affected += 1
            print(f"{result_id}: passed={passed} total={total} skipped={skipped} "
                  f"result_value {old} -> {new:.6g}")
            if not args.apply:
                continue

            blob["result_value"] = new
            data = json.dumps(blob, indent=2).encode("utf-8")
            try:
                client.put_object(
                    RESULTS_BUCKET,
                    obj.object_name,
                    io.BytesIO(data),
                    length=len(data),
                    content_type="application/json",
                )
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE result SET result = %s, updated_at = now() "
                        "WHERE id = %s",
                        (new, result_id),
                    )
                conn.commit()
                rewritten += 1
            except Exception as exc:  # noqa: BLE001
                conn.rollback()
                print(f"ERROR rewriting {result_id}: {exc}", file=sys.stderr)
                errors += 1
    finally:
        conn.close()

    mode = "applied" if args.apply else "dry run"
    print(f"\n{mode}: {seen} results scanned, {affected} taxed by skips, "
          f"{rewritten} rewritten, {errors} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
