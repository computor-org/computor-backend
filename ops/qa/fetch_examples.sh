#!/usr/bin/env bash
# Fetch the runnable examples package for the QA stack (computor-org/issues#529).
#
# computor.at's examples come from the private GitHub repository
# computor-org/examples. Run this where gh is signed in with access to it;
# only the archive goes to the QA host, never a credential.
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
repo=computor-org/examples
out=${QA_INPUTS:-.}

commit=$(gh api "repos/$repo/commits/$ref" --jq .sha)
[[ "$commit" =~ ^[0-9a-f]{40}$ ]] || { echo "no commit $ref in $repo" >&2; exit 1; }
short=${commit:0:12}
mkdir -p "$out"
tarball="$out/examples-$short.tar.gz"

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
gh api "repos/$repo/tarball/$commit" > "$work/repo.tar.gz"
mkdir "$work/repo"
tar -xzf "$work/repo.tar.gz" -C "$work/repo" --strip-components=1
# qactl.sh and the computor.at deploy read the commit from the top directory,
# named as GitLab archives were: examples-<ref>-<commit>-python/python/...
top="examples-${ref//\//-}-$commit-python"
mkdir -p "$work/pkg/$top"
cp -a "$work/repo/python" "$work/pkg/$top/python"
tar -czf "$tarball.tmp" -C "$work/pkg" --sort=name --owner=0 --group=0 --numeric-owner "$top"
mv "$tarball.tmp" "$tarball"

# The zip a lecturer uploads on /examples/upload: the example folders at its root.
(cd "$work/pkg/$top/python" && zip -qr -X "$work/examples.zip" .)
mv "$work/examples.zip" "$out/examples-$short.zip"

echo "examples $ref = $commit"
echo "  $tarball"
echo "  $out/examples-$short.zip"
if [ -n "$target" ]; then
    scp -q "$tarball" "$target/"
    echo "  copied to $target/examples-$short.tar.gz"
fi
