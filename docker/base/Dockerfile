# Shared base image for the Python computor services (api + temporal workers).
#
# Built once and tagged `computor-base:latest`; the service images do
# `FROM computor-base:latest` and add only their own delta (a CMD, extra
# runtimes, ...). The matlab worker can't inherit (different OS base) so it
# `COPY --from=computor-base` instead.
#
# Two-layer install so editing computor *source* does NOT reinstall the heavy
# third-party dependencies:
#   1. deps layer  — copy only pyproject.toml manifests (+ a stub package) and
#                    install the third-party deps. Rebuilds only when a
#                    pyproject.toml changes.
#   2. source layer — copy the real source and re-install it editable with
#                    --no-deps. Cheap; rebuilds on every source change.
FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        postgresql-client \
        git \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

# Timezone: UTC
ENV TZ=UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN useradd -ms /bin/bash worker
WORKDIR /home/worker
USER worker
ENV PATH="/home/worker/.local/bin:${PATH}"

# ---------------------------------------------------------------------------
# Layer 1: third-party dependencies (cached unless a pyproject.toml changes)
# ---------------------------------------------------------------------------
# Only the manifests are copied here. A stub package per project lets pip build
# each wheel and pull its declared dependencies without the real source — so a
# source edit below does not bust this (expensive) layer. computor-types is
# listed first because computor-client/-backend depend on it.
COPY --chown=worker:worker computor-types/pyproject.toml    computor-types/README.md    computor-types/
COPY --chown=worker:worker computor-client/pyproject.toml   computor-client/README.md   computor-client/
COPY --chown=worker:worker computor-backend/pyproject.toml  computor-backend/README.md  computor-backend/
RUN mkdir -p computor-types/src/computor_types \
             computor-client/src/computor_client \
             computor-backend/src/computor_backend \
    && touch computor-types/src/computor_types/__init__.py \
             computor-client/src/computor_client/__init__.py \
             computor-backend/src/computor_backend/__init__.py \
    && pip install --user --no-warn-script-location \
        ./computor-types ./computor-client ./computor-backend

# ---------------------------------------------------------------------------
# Layer 2: real source, re-installed editable (deps already satisfied → fast)
# ---------------------------------------------------------------------------
COPY --chown=worker:worker computor-types    computor-types
COPY --chown=worker:worker computor-client   computor-client
COPY --chown=worker:worker computor-backend  computor-backend
RUN pip install --user --no-deps --no-warn-script-location \
        -e computor-types -e computor-client -e computor-backend

# Source on PYTHONPATH so imports resolve from the working tree (alembic, etc.).
ENV PYTHONPATH=/home/worker/computor-backend/src
