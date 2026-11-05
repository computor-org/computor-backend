# Updater sidecar — watches Redis for update requests queued by the admin API
# (POST /system/update) and launches a detached runner container that executes
# ./computor.sh's update flow from the bind-mounted repository.
#
# Deliberately minimal: ALL update logic lives in the repo (ops/lib/update.sh),
# this image only provides the tools (git, docker CLI + compose, redis-cli) and
# the ~40-line watcher loop. That keeps "an old updater driving a new repo"
# safe — the contract is just `cmd_update_exec prod`.
FROM alpine:3.24@sha256:be2656061b536c1883c4034790e21d0a09c5aaaf51968b89368a3c0371ea2c9a

RUN apk add --no-cache bash git curl redis docker-cli docker-cli-compose docker-cli-buildx

# Repository trust is scoped by ops/lib/git.sh to the selected deployment.

COPY docker/updater/watch.sh /usr/local/bin/watch.sh

CMD ["bash", "/usr/local/bin/watch.sh"]
