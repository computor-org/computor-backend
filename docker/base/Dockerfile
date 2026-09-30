# Shared base image for the Python computor services (api + temporal workers).
#
# Built once and tagged `computor-base:latest`; the service images do
# `FROM computor-base:latest` and add only their own delta (a CMD, extra
# runtimes, ...). The matlab worker can't inherit (different OS base) so it
# `COPY --from=computor-base` instead.
#
# Dependencies install exactly from computor-backend/uv.lock (hash-checked),
# never from the version ranges in pyproject.toml, so a clean rebuild cannot
# pull a newer PyPI release than the one that was locked and reviewed.
#
# Two-layer install so editing computor *source* does NOT reinstall the heavy
# third-party dependencies:
#   1. deps layer  — export the lock to hashed requirements (uv, pinned below)
#                    and pip-install them with --require-hashes --no-deps.
#                    Rebuilds only when uv.lock / a pyproject.toml changes.
#   2. source layer — copy the real source and install it editable with
#                    --no-deps. Cheap; rebuilds on every source change.
#
# pip --user into ~/.local is kept (not a uv venv) because the testing, coder
# and matlab workers COPY ~/.local onto other Python 3.10 interpreters.

# ---------------------------------------------------------------------------
# Stage: export uv.lock to hashed requirements files (uv never reaches the
# runtime image). The 7-day cooldown lives in computor-backend/pyproject.toml
# ([tool.uv] exclude-newer), with the refresh procedure next to it.
# ---------------------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:0.12.21@sha256:a7aed3216253ee804de3e2d8afa5073baa1a177335345d43845cd4165e43b711 AS uv

FROM python:3.14.6-slim@sha256:7bec7ddcddeff7975d6ba9b4be7dd6f6b2f55e7491539145e2978f7f97ce9144 AS lock-export
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /src
COPY computor-types/pyproject.toml    computor-types/
COPY computor-client/pyproject.toml   computor-client/
COPY computor-testing/pyproject.toml  computor-testing/
COPY computor-backend/pyproject.toml computor-backend/uv.lock computor-backend/
# --no-emit-local drops the computor-* path packages (installed from source
# below); --locked fails the build if uv.lock does not match pyproject.toml.
RUN mkdir /locks \
    && EXPORT="uv export --project computor-backend --locked --no-emit-project \
               --no-emit-local --format requirements-txt --no-header" \
    && $EXPORT --no-dev                       -o /locks/runtime.txt \
    && $EXPORT --only-group testing-worker    -o /locks/testing-worker.txt

# ---------------------------------------------------------------------------
# Runtime image
# ---------------------------------------------------------------------------
FROM python:3.14.6-slim@sha256:7bec7ddcddeff7975d6ba9b4be7dd6f6b2f55e7491539145e2978f7f97ce9144

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
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# ---------------------------------------------------------------------------
# Layer 1: third-party dependencies, exactly as locked (hash-checked)
# ---------------------------------------------------------------------------
# Only wheels are accepted except for grapheme (sdist-only, pulled in by
# alive-progress). It and the local packages build with --no-build-isolation
# against the setuptools/wheel shipped in the digest-pinned python image, so
# pip never fetches an unpinned build backend. The exported
# files stay in the image for the testing worker (testing-worker.txt).
COPY --from=lock-export --chown=worker:worker /locks /home/worker/.computor-locks
RUN pip install --user --no-warn-script-location --no-cache-dir \
        --require-hashes --no-deps --no-build-isolation \
        --only-binary :all: --no-binary grapheme \
        -r .computor-locks/runtime.txt

# ---------------------------------------------------------------------------
# Layer 2: real source, installed editable (deps already satisfied → fast)
# ---------------------------------------------------------------------------
COPY --chown=worker:worker computor-types    computor-types
COPY --chown=worker:worker computor-client   computor-client
COPY --chown=worker:worker computor-backend  computor-backend
RUN pip install --user --no-deps --no-build-isolation --no-cache-dir \
        --no-warn-script-location \
        -e computor-types -e computor-client -e computor-backend \
    && pip check

# Source on PYTHONPATH so imports resolve from the working tree (alembic, etc.).
ENV PYTHONPATH=/home/worker/computor-backend/src

# Build provenance, injected by computor.sh at build time. Declared last so a
# changed commit hash never busts the dependency/source layers above. The repo's
# .git is not in the image, so this ENV is the only way a container can know
# which commit it runs (read by /system/update/status).
ARG GIT_COMMIT=unknown
ARG GIT_BRANCH=unknown
ARG BUILD_TIME=
ENV GIT_COMMIT=${GIT_COMMIT} GIT_BRANCH=${GIT_BRANCH} BUILD_TIME=${BUILD_TIME}
