#!/bin/bash
# Behavioral regression for Coder template deployment under a private umask.
set -euo pipefail

repo_root=$(cd "$(dirname "$0")/../.." && pwd)
scratch=$(mktemp -d)
cleanup() {
    docker run --rm --network none --entrypoint chown -v "$scratch:/scratch" \
        alpine -R "$(id -u):$(id -g)" /scratch >/dev/null 2>&1 || true
    rm -rf "$scratch"
}
trap cleanup EXIT
mkdir -p "$scratch/source/matlab-vscode" "$scratch/source/operator-template" \
    "$scratch/source/bash" "$scratch/target/matlab-vscode" \
    "$scratch/target/operator-template"
printf 'new\n' > "$scratch/source/matlab-vscode/template.json"
printf 'should-not-replace\n' > "$scratch/source/operator-template/template.json"
printf 'bash\n' > "$scratch/source/bash/template.json"
printf 'old\n' > "$scratch/target/matlab-vscode/template.json"
touch "$scratch/target/matlab-vscode/.computor-managed"
printf 'operator\n' > "$scratch/target/operator-template/template.json"

run_seed() {
    docker run --rm --network none --read-only --security-opt no-new-privileges \
        --user 0:0 --cap-drop ALL --cap-add CHOWN --cap-add DAC_OVERRIDE \
        --cap-add FOWNER --pids-limit 64 --memory 128m --entrypoint sh \
        -v "$scratch/source:/source:ro" -v "$scratch/target:/target" \
        -v "$repo_root/ops/lib/seed_coder_templates.sh:/seed.sh:ro" \
        alpine@sha256:294b683cb724975bec92580e1e685676bd4b50bda910ddb8c51d4cabeaec77e6 \
        -e /seed.sh /source /target "$1" "$2"
}

# Reproduce an old deployment whose entire mount is private to a foreign UID.
docker run --rm --network none --entrypoint sh -v "$scratch/target:/target" \
    alpine -ec 'chown -R 1234:1234 /target; chmod 700 /target /target/matlab-vscode; chmod 600 /target/matlab-vscode/*'

# A staging failure must leave the old managed template in place.
if (umask 077; run_seed no-such-user "$(id -g)") > "$scratch/failed.log" 2>&1; then
    echo 'Expected staging ownership failure' >&2
    exit 1
fi
docker run --rm --network none --entrypoint sh -v "$scratch/target:/target:ro" \
    alpine -ec 'test "$(cat /target/matlab-vscode/template.json)" = old'
test -z "$(find "$scratch/target" -maxdepth 1 -name '.computor-stage-*' -print -quit)"

(umask 077; run_seed "$(id -u)" "$(id -g)")
test "$(cat "$scratch/target/matlab-vscode/template.json")" = new
test "$(cat "$scratch/target/bash/template.json")" = bash
test -f "$scratch/target/matlab-vscode/.computor-managed"
test "$(cat "$scratch/target/operator-template/template.json")" = operator
test "$(stat -c %u "$scratch/target/matlab-vscode/template.json")" = "$(id -u)"
test "$(stat -c %u "$scratch/target")" = "$(id -u)"
docker run --rm --network none --user 23100:23100 --entrypoint sh \
    -v "$scratch/target:/templates:ro" alpine -ec \
    'test -r /templates/matlab-vscode/template.json && test "$(cat /templates/matlab-vscode/template.json)" = new'

# Recover a previous interruption between renaming old and publishing new.
mv "$scratch/target/matlab-vscode" "$scratch/target/.computor-backup-matlab-vscode"
(umask 077; run_seed "$(id -u)" "$(id -g)")
test "$(cat "$scratch/target/matlab-vscode/template.json")" = new
test ! -e "$scratch/target/.computor-backup-matlab-vscode"

# An on-disk link must not let template publication escape the target tree.
rm -rf "$scratch/target/matlab-vscode"
ln -s operator-template "$scratch/target/matlab-vscode"
if run_seed "$(id -u)" "$(id -g)" > "$scratch/symlink.log" 2>&1; then
    echo 'Expected symlink refusal' >&2
    exit 1
fi
test "$(cat "$scratch/target/operator-template/template.json")" = operator
echo 'Coder template seed behavior passed'
