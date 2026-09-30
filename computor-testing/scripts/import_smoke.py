"""Import every top-level module of every installed distribution.

Run at image build time in each sandbox / student environment, so a locked
combination that installs but cannot import (e.g. a package needing the
``pkg_resources`` that newer setuptools no longer ships) fails the build
instead of the first student submission.

Usage: python import_smoke.py [--skip mod ...]
"""

import importlib
import importlib.metadata as md
import sys

# Installer/tooling modules that are not meant to be imported by user code.
DEFAULT_SKIP = {"pip", "_distutils_hack", "distutils-precedence", "pkg_resources"}


def top_level_modules(dist):
    text = dist.read_text("top_level.txt")
    if text:
        return {m.strip() for m in text.split() if m.strip()}
    mods = set()
    for f in dist.files or []:
        parts = f.parts
        if not parts or parts[0].endswith((".dist-info", ".data")) or parts[0] == "..":
            continue
        if len(parts) > 1 and parts[1] == "__init__.py":
            mods.add(parts[0])
        elif len(parts) == 1 and parts[0].endswith(".py"):
            mods.add(parts[0][:-3])
    return mods


def main(argv):
    skip = set(DEFAULT_SKIP)
    if "--skip" in argv:
        skip |= set(argv[argv.index("--skip") + 1:])
    failures, count, seen = [], 0, set()
    for dist in md.distributions():
        for mod in sorted(top_level_modules(dist)):
            if mod in skip or mod.startswith("_") or not mod.isidentifier():
                continue
            if mod in seen:
                continue
            seen.add(mod)
            count += 1
            try:
                importlib.import_module(mod)
            except Exception as exc:  # noqa: BLE001 - report every failure
                failures.append(f"{dist.metadata['Name']}: import {mod}: {exc!r}")
    print(f"import smoke: {count} modules, {len(failures)} failures")
    for line in failures:
        print("  " + line)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
