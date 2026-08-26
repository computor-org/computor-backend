#!/usr/bin/env python3
"""One-off scrub of absolute paths from stored test results (#239).

Historic tester reports carried the worker-container paths of ``test.yaml``
and the generated spec file (which contains the reference solution) in
``result_json.properties``. New results no longer do; this rewrites the old
ones. ``result_json`` lives in MinIO (``results/{result_id}/result.json``),
not in postgres, so the scrub walks the bucket rather than running SQL.

Only ``properties`` entries whose value is a string starting with ``/`` are
removed — nothing else in the blob is touched.

Usage (from the repo root, .env exported or sourced):

    set -a; source .env; set +a
    .venv/bin/python scripts/utilities/scrub_result_path_properties.py [--apply]

Without ``--apply`` it only reports what it would change.
"""

import argparse
import io
import json
import os
import sys

from minio import Minio

RESULTS_BUCKET = "results"


def make_client() -> Minio:
    endpoint = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
    # .env carries the docker-internal host; outside the compose network the
    # API port published on localhost is the reachable one.
    if endpoint.startswith("minio:"):
        endpoint = f"localhost:{os.environ.get('MINIO_API_PORT', '9000')}"
    return Minio(
        endpoint,
        access_key=os.environ["MINIO_ROOT_USER"],
        secret_key=os.environ["MINIO_ROOT_PASSWORD"],
        secure=os.environ.get("MINIO_SECURE", "false").lower() == "true",
    )


def scrub(properties: dict) -> dict:
    return {
        k: v
        for k, v in properties.items()
        if not (isinstance(v, str) and v.startswith("/"))
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true",
                        help="rewrite the affected objects (default: dry run)")
    args = parser.parse_args()

    client = make_client()
    if not client.bucket_exists(RESULTS_BUCKET):
        print(f"bucket {RESULTS_BUCKET!r} does not exist — nothing to scrub")
        return 0

    seen = affected = rewritten = errors = 0
    for obj in client.list_objects(RESULTS_BUCKET, recursive=True):
        if not obj.object_name.endswith("/result.json"):
            continue
        seen += 1
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

        properties = blob.get("properties")
        if not isinstance(properties, dict):
            continue
        cleaned = scrub(properties)
        if cleaned == properties:
            continue

        affected += 1
        removed = sorted(set(properties) - set(cleaned))
        print(f"{obj.object_name}: removing {', '.join(removed)}")
        if not args.apply:
            continue

        blob["properties"] = cleaned
        data = json.dumps(blob, indent=2).encode("utf-8")
        try:
            client.put_object(
                RESULTS_BUCKET,
                obj.object_name,
                io.BytesIO(data),
                length=len(data),
                content_type="application/json",
            )
            rewritten += 1
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR rewriting {obj.object_name}: {exc}", file=sys.stderr)
            errors += 1

    mode = "applied" if args.apply else "dry run"
    print(f"\n{mode}: {seen} results scanned, {affected} with path properties, "
          f"{rewritten} rewritten, {errors} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
