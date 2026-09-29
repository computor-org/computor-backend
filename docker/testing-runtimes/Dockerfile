# Heavy, slow-changing language runtimes for the testing worker: Octave, R,
# C/C++/Fortran, a from-source Python 3.13, and Julia.
#
# Built as its own image (computor-testing-runtimes) so it is cached
# INDEPENDENTLY of the computor python project. Previously these lived after
# `FROM computor-base` in the testing worker, so any project source change
# busted them and recompiled Python 3.13 (~minutes) every build. Now
# temporal-worker-testing layers the computor env (copied from computor-base)
# on top of this image, and the runtimes are built once.
#
# python:3.10-slim base (same as computor-base) so the copied CPython-3.10
# computor env is ABI-compatible.
FROM python:3.10-slim@sha256:31dd4d9529d02d7436659061cb7564cd4733fc90e5e152709a942d53382ec8d0

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        tzdata \
        build-essential \
        wget \
        curl \
        # Python build dependencies (for the 3.13 build below)
        libssl-dev \
        zlib1g-dev \
        libncurses5-dev \
        libncursesw5-dev \
        libreadline-dev \
        libsqlite3-dev \
        libgdbm-dev \
        libdb5.3-dev \
        libbz2-dev \
        libexpat1-dev \
        liblzma-dev \
        libffi-dev \
        uuid-dev \
        # Language runtimes for computor-testing
        octave \
        r-base \
        gcc \
        g++ \
        gfortran \
    && rm -rf /var/lib/apt/lists/*

# Timezone: UTC
ENV TZ=UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Python 3.13 for test execution (alongside the worker's 3.10). Pinned patch
# release + SHA-256 from python.org's release-file API (sha256_sum), verified
# before extraction so a tampered or swapped tarball fails the build.
ARG PYTHON313_VERSION=3.13.15
ARG PYTHON313_SHA256=c28d9d213c09b5b5ab2c29812950e12f746999e099b82894231be954b26baed9
RUN set -eu; \
    wget -q "https://www.python.org/ftp/python/${PYTHON313_VERSION}/Python-${PYTHON313_VERSION}.tgz"; \
    echo "${PYTHON313_SHA256}  Python-${PYTHON313_VERSION}.tgz" | sha256sum -c -; \
    tar -xzf "Python-${PYTHON313_VERSION}.tgz"; \
    cd "Python-${PYTHON313_VERSION}"; \
    ./configure --enable-optimizations --prefix=/usr/local/python3.13; \
    make -j"$(nproc)"; \
    make altinstall; \
    cd ..; \
    rm -rf "Python-${PYTHON313_VERSION}" "Python-${PYTHON313_VERSION}.tgz"; \
    ln -s /usr/local/python3.13/bin/python3.13 /usr/local/bin/python3.13; \
    ln -s /usr/local/python3.13/bin/pip3.13 /usr/local/bin/pip3.13

# Julia (not in Debian repos), latest 1.10 LTS patch. SHA-256 from the official
# julialang-s3 checksums file (bin/checksums/julia-<ver>.sha256). A checksum
# mismatch fails the build rather than silently skipping Julia.
ARG JULIA_VERSION=1.10.12
ARG JULIA_SHA256=b0c50dfe349d76ffc8580d24e0c0be623988a6d91ed57ad8b73c0137fd27bc0d
RUN set -eu; \
    wget -q "https://julialang-s3.julialang.org/bin/linux/x64/1.10/julia-${JULIA_VERSION}-linux-x86_64.tar.gz" -O /tmp/julia.tar.gz; \
    echo "${JULIA_SHA256}  /tmp/julia.tar.gz" | sha256sum -c -; \
    tar -xzf /tmp/julia.tar.gz -C /opt/; \
    rm /tmp/julia.tar.gz; \
    ln -s "/opt/julia-${JULIA_VERSION}/bin/julia" /usr/local/bin/julia

# Match computor-base's worker user (uid lines up) so the copied env owns cleanly.
RUN useradd -ms /bin/bash worker
WORKDIR /home/worker
