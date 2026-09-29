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
    && rm -rf /var/lib/apt/lists/*

# coder CLI: pinned release tarball, verified against its published sha256
# (no `curl | sh` of a moving install script). Keep in lockstep with the
# ghcr.io/coder/coder server tag in ops/docker/docker-compose.coder.yaml.
ARG CODER_VERSION=2.37.3
ARG CODER_SHA256_AMD64=c941bef3b2656da89e9ea9b509884085b99b7d7a08620abd8484c50d77f41eed
ARG CODER_SHA256_ARM64=6729d7ed6c9e3067518fbe08db2c2f1df5847a49f6e5342b8db8f5c9ffc34a97
RUN set -eu; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
        amd64) sum="$CODER_SHA256_AMD64" ;; \
        arm64) sum="$CODER_SHA256_ARM64" ;; \
        *) echo "unsupported arch $arch" >&2; exit 1 ;; \
    esac; \
    curl -fsSL -o /tmp/coder.tgz \
        "https://github.com/coder/coder/releases/download/v${CODER_VERSION}/coder_${CODER_VERSION}_linux_${arch}.tar.gz"; \
    echo "${sum}  /tmp/coder.tgz" | sha256sum -c -; \
    tar -xzf /tmp/coder.tgz -C /usr/local/bin ./coder; \
    rm /tmp/coder.tgz; \
    coder version

# Timezone: UTC
ENV TZ=UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Match computor-base's worker user (uid lines up) so the copied env owns cleanly.
RUN useradd -ms /bin/bash worker
WORKDIR /home/worker
