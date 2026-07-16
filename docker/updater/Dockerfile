# Updater sidecar — watches Redis for update requests queued by the admin API
# (POST /system/update) and launches a detached runner container that executes
# ./computor.sh's update flow from the bind-mounted repository.
#
# Deliberately minimal: ALL update logic lives in the repo (ops/lib/update.sh),
# this image only provides the tools (git, docker CLI + compose, redis-cli) and
# the ~40-line watcher loop. That keeps "an old updater driving a new repo"
# safe — the contract is just `cmd_update_exec prod`.
FROM alpine:3.20

RUN apk add --no-cache bash git curl redis docker-cli docker-cli-compose docker-cli-buildx

# The repo is bind-mounted and owned by the host user; the container runs as
# that uid (compose `user:`), but belt-and-braces for uid mismatches.
ENV GIT_CONFIG_COUNT=1 \
    GIT_CONFIG_KEY_0=safe.directory \
    GIT_CONFIG_VALUE_0=*

COPY docker/updater/watch.sh /usr/local/bin/watch.sh

CMD ["bash", "/usr/local/bin/watch.sh"]
