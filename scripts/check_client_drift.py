#!/usr/bin/env python3
"""Fail when the checked-in Python client no longer matches the API.

``computor-client/src/computor_client/endpoints/`` is generated from the
backend's OpenAPI spec, but nothing used to verify that the committed output
still corresponded to the current routes. It drifted: whole endpoint groups
(course-workspaces, the course template download, the system update API) simply
did not exist in the client, and there was no signal until something 404'd or an
attribute was missing at runtime.

This regenerates into a temporary directory and diffs. It never writes to the
working tree.

Usage:
    python scripts/check_client_drift.py           # exit 1 on drift
    python scripts/check_client_drift.py --quiet   # only print on failure

Regenerate with: bash generate.sh python-client
"""

import argparse
import contextlib
import difflib
import io
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENDPOINTS_DIR = REPO_ROOT / "computor-client" / "src" / "computor_client" / "endpoints"


def _ensure_importable() -> None:
    """Put the backend and types packages on the path, as generate.sh does."""
    for package in ("computor-backend/src", "computor-types/src"):
        path = str(REPO_ROOT / package)
        if path not in sys.path:
            sys.path.insert(0, path)


def compare(generated_dir: Path, committed_dir: Path) -> list[str]:
    """Return human-readable descriptions of every difference found."""
    generated = {f.name: f.read_text() for f in generated_dir.glob("*.py")}
    committed = {f.name: f.read_text() for f in committed_dir.glob("*.py")}

    problems: list[str] = []

    for name in sorted(set(generated) - set(committed)):
        problems.append(f"missing from the committed client: {name}")
    for name in sorted(set(committed) - set(generated)):
        problems.append(f"committed but no longer generated: {name}")

    for name in sorted(set(generated) & set(committed)):
        if generated[name] == committed[name]:
            continue
        diff = difflib.unified_diff(
            committed[name].splitlines(),
            generated[name].splitlines(),
            fromfile=f"committed/{name}",
            tofile=f"generated/{name}",
            lineterm="",
            n=1,
        )
        body = "\n".join(list(diff)[:40])
        problems.append(f"{name} differs:\n{body}")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true", help="only print on failure")
    args = parser.parse_args()

    _ensure_importable()
    from computor_backend.scripts.generate_python_clients import main as generate

    if not ENDPOINTS_DIR.is_dir():
        print(f"❌ No generated client at {ENDPOINTS_DIR}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="computor-client-drift-") as tmp:
        target = Path(tmp) / "endpoints"
        try:
            # The generator narrates every file it writes; that is useful when
            # regenerating on purpose, just noise when only the diff matters.
            with contextlib.redirect_stdout(io.StringIO()):
                generate(output_dir=target)
        except SystemExit as e:
            # The generator refuses to run on an unresolvable schema; that is a
            # failure worth surfacing here too rather than reporting as drift.
            print(f"❌ Client generation failed:\n{e}", file=sys.stderr)
            return 1

        problems = compare(target, ENDPOINTS_DIR)

    if problems:
        print("❌ The committed Python client is out of date.\n", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        print(
            "\nRegenerate and commit the result:\n"
            "  bash generate.sh python-client\n",
            file=sys.stderr,
        )
        return 1

    if not args.quiet:
        print("✅ Committed Python client matches the current API spec.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
