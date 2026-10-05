# shellcheck shell=bash
# Running this deployment's scripts explicitly trusts this checkout. Scope the
# ownership exception to each Git invocation, never to all repositories globally.
deployment_git() {
    git -c "safe.directory=$REPO_ROOT" -C "$REPO_ROOT" "$@"
}
