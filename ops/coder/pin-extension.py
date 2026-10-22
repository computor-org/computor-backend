#!/usr/bin/env python3
"""Pin a computor-vscode release as the extension this backend branch approves.

    ops/coder/pin-extension.py 2027.3.5            # rewrite the pin
    ops/coder/pin-extension.py --check             # verify the current pin

Downloads computor-<version>.vsix and SHA256SUMS from the GitHub release
v<version>, checks the VSIX against SHA256SUMS, and writes version and sha256
to computor-backend/src/computor_backend/coder/approved_extension.json. Commit
that on the branch the instance deploys (main for computor.at, release/2026.10
for code.tugraz.at) and deploy: the backend registers the pinned release at
startup and running workspaces install it within 30 minutes
(ops/coder/templates/README.md, "Extension updates"). Standard library only.
"""

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

PIN = Path(__file__).resolve().parents[2] / "computor-backend/src/computor_backend/coder/approved_extension.json"
RELEASES = "https://github.com/computor-org/computor-vscode/releases/download"


def fetch(url):
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def verified_digest(version):
    filename = f"computor-{version}.vsix"
    vsix = fetch(f"{RELEASES}/v{version}/{filename}")
    digest = hashlib.sha256(vsix).hexdigest()
    for line in fetch(f"{RELEASES}/v{version}/SHA256SUMS").decode().splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("*").removeprefix("./") == filename:
            if parts[0].lower() != digest:
                raise SystemExit(f"{filename}: sha256 {digest} does not match SHA256SUMS {parts[0]}")
            return digest
    raise SystemExit(f"SHA256SUMS of v{version} has no entry for {filename}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("version", nargs="?", help="release version x.y.z")
    parser.add_argument("--check", action="store_true", help="verify the current pin against its release")
    args = parser.parse_args()
    pin = json.loads(PIN.read_text())
    if args.check:
        digest = verified_digest(pin["version"])
        if digest != pin["sha256"]:
            raise SystemExit(f"pin {pin['version']} has sha256 {pin['sha256']}, the release has {digest}")
        print(f"pin {pin['version']} matches its release ({digest})")
        return
    if not args.version or not re.fullmatch(r"\d+\.\d+\.\d+", args.version):
        raise SystemExit("give a release version x.y.z (or --check)")
    pin.update(version=args.version, sha256=verified_digest(args.version))
    PIN.write_text(json.dumps(pin, indent=2) + "\n")
    print(f"pinned {pin['extension']} {pin['version']} sha256 {pin['sha256']}")


if __name__ == "__main__":
    sys.exit(main())
