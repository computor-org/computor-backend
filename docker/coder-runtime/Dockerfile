# System runtime for the coder temporal worker: the Docker CLI (workspace image
# builds go through the Docker socket) + the coder CLI (template pushes shell out
# to `coder templates push`).
#
# Built as its own image (computor-coder-runtime), cached INDEPENDENTLY of the
# computor python project. Previously these packages sat after `FROM
# computor-base` in the worker Dockerfile, so any project source change busted
# the base's source layer and re-ran this apt/curl install (docker.io + the coder
# download) on EVERY build. Now temporal-worker-coder layers the computor env
# (copied from computor-base) on top of this image, and the runtime is built once.
#
# python:3.10-slim base (same as computor-base) so the copied CPython-3.10
# computor env is ABI-compatible.
FROM python:3.10-slim

# git: the task registry imports EVERY task module on every worker, and
# git_ops imports GitPython, which refuses to import without a git binary —
# without it the coder worker crash-loops at startup (computor-base has git,
# but this runtime is python:3.10-slim, not computor-base).
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        docker.io \
        git \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://coder.com/install.sh | sh

# Timezone: UTC
ENV TZ=UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Match computor-base's worker user (uid lines up) so the copied env owns cleanly.
RUN useradd -ms /bin/bash worker
WORKDIR /home/worker
