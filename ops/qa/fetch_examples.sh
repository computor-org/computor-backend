#!/usr/bin/env bash
# Fetch the runnable examples package for the QA stack (computor-org/issues#529).
#
# computor.at's examples come from the private GitLab repository
# codeability/development/examples. Run this where glab is signed in to
# gitlab.tugraz.at; only the archive goes to the QA host, never a credential.
#
#   ops/qa/fetch_examples.sh REF [HOST:DIR]
#
# Writes examples-<commit12>.tar.gz (the python/ directory, as qactl.sh
# deploy --examples expects) and examples-<commit12>.zip (the same examples
# for the web upload, one folder per example) into QA_INPUTS (default: the
# current directory) and copies the tarball to HOST:DIR when given.
set -euo pipefail

ref=${1:?usage: fetch_examples.sh REF [HOST:DIR]}
target=${2:-}
project=codeability%2Fdevelopment%2Fexamples
host=gitlab.tugraz.at
out=${QA_INPUTS:-.}

commit=$(glab api --hostname "$host" "projects/$project/repository/commits/$(printf %s "$ref" | sed 's#/#%2F#g')" \
    | python3 -c 'import json, sys; print(json.load(sys.stdin)["id"])')
short=${commit:0:12}
mkdir -p "$out"
tarball="$out/examples-$short.tar.gz"
glab api --hostname "$host" "projects/$project/repository/archive.tar.gz?sha=$commit&path=python" > "$tarball.tmp"
mv "$tarball.tmp" "$tarball"

# The zip a lecturer uploads on /examples/upload: the example folders at its root.
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
tar -xzf "$tarball" -C "$work"
(cd "$work"/*/python && zip -qr -X "$work/examples.zip" .)
mv "$work/examples.zip" "$out/examples-$short.zip"

echo "examples $ref = $commit"
echo "  $tarball"
echo "  $out/examples-$short.zip"
if [ -n "$target" ]; then
    scp -q "$tarball" "$target/"
    echo "  copied to $target/examples-$short.tar.gz"
fi
