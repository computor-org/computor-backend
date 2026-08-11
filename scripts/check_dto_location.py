#!/usr/bin/env python3
"""
Check that API-facing pydantic models live in computor-types.

Companion to check_forbidden_imports.py, which guards the other direction
(computor-types must not import the backend). This one catches a `BaseModel`
declared inside the backend that should have been a shared DTO.

Why it matters — the failure is *partial*, which is what makes it easy to miss:

  * A model in business_logic/ is invisible to every generator. The frontend
    loses the type and someone hand-writes it.
  * A model in api/ does get a TypeScript interface (the interface generator
    scans api/ and tasks/ too) but gets no Python-client type and no client
    method, because those come from EntityInterface discovery. It also sits
    outside the computor-types package that the VS Code extension and
    computor-agent install. So it looks generated and is only half generated.

Scope: DTO-shaped models only. Plenty of pydantic in the backend is legitimately
internal (settings, worker config, structs that never cross the wire), so this
checks the directories where API shapes actually leak from and allows an opt-out
comment for the genuine exceptions.

Usage:
    python scripts/check_dto_location.py
    python scripts/check_dto_location.py --list-allowed
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

# Backend packages whose pydantic models are, by definition, API-facing.
CHECKED_DIRS = (
    "api",
    "business_logic",
)

# Base classes that mark a model as a data-transfer shape.
DTO_BASES = {
    "BaseModel",
    "BaseEntityGet",
    "BaseEntityList",
    "BaseEntityCreate",
    "BaseEntityUpdate",
    "BaseEntityQuery",
}

# Escape hatch. Put this on the line above the class, or anywhere in its
# docstring, for a model that genuinely never crosses the wire.
OPT_OUT = "dto-location: internal"

# Known, accepted exceptions. Keep this list shrinking, never growing.
GRANDFATHERED: set[str] = {
    "computor-backend/src/computor_backend/api/course_contents.py",
}


def iter_models(tree: ast.Module) -> list[tuple[str, int, list[str]]]:
    """Every class in the module that inherits from a DTO base."""
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(base.attr)
        if DTO_BASES.intersection(bases):
            found.append((node.name, node.lineno, bases))
    return found


def has_opt_out(source_lines: list[str], node_line: int, tree: ast.Module, name: str) -> bool:
    # Comment on one of the two lines above the class statement.
    for offset in (2, 3):
        idx = node_line - offset
        if 0 <= idx < len(source_lines) and OPT_OUT in source_lines[idx]:
            return True
    # Or in the class docstring.
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == name:
            doc = ast.get_docstring(node) or ""
            if OPT_OUT in doc:
                return True
    return False


def check(project_root: Path) -> list[dict]:
    violations = []
    backend_src = project_root / "computor-backend" / "src" / "computor_backend"

    for package in CHECKED_DIRS:
        package_path = backend_src / package
        if not package_path.exists():
            continue

        for py_file in sorted(package_path.rglob("*.py")):
            rel = py_file.relative_to(project_root).as_posix()
            if rel in GRANDFATHERED or "__pycache__" in rel:
                continue

            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(py_file))
            except (OSError, SyntaxError) as exc:
                print(f"  ⚠️  Could not parse {rel}: {exc}", file=sys.stderr)
                continue

            lines = source.splitlines()
            for name, lineno, bases in iter_models(tree):
                if has_opt_out(lines, lineno, tree, name):
                    continue
                violations.append(
                    {
                        "file": rel,
                        "line": lineno,
                        "model": name,
                        "bases": ", ".join(bases),
                    }
                )

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--list-allowed",
        action="store_true",
        help="Print the grandfathered files and exit.",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent

    if args.list_allowed:
        print("Grandfathered (move these when you next touch them):")
        for path in sorted(GRANDFATHERED):
            print(f"  {path}")
        return 0

    print("\U0001f50d Checking DTO locations...\n")
    violations = check(project_root)

    if not violations:
        print("  ✅ No API-facing pydantic models outside computor-types.\n")
        return 0

    print(f"  ❌ Found {len(violations)} misplaced model(s):\n")
    for v in violations:
        print(f"     {v['file']}:{v['line']}")
        print(f"     class {v['model']}({v['bases']})")
        print()

    print("=" * 60)
    print("API-facing pydantic models belong in computor-types, so that the")
    print("TypeScript types, the TS and Python clients and the JSON schemas are")
    print("all generated from one source.")
    print()
    print("Move the model to computor-types/src/computor_types/<entity>.py and")
    print("reference it from an EntityInterface, then run: bash generate.sh")
    print()
    print(f"If it genuinely never crosses the wire, mark it: # {OPT_OUT}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
