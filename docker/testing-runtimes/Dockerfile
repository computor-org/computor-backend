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
FROM python:3.10-slim

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

# Python 3.13 for test execution (alongside the worker's 3.10)
RUN wget -q https://www.python.org/ftp/python/3.13.1/Python-3.13.1.tgz && \
    tar -xzf Python-3.13.1.tgz && \
    cd Python-3.13.1 && \
    ./configure --enable-optimizations --prefix=/usr/local/python3.13 && \
    make -j$(nproc) && \
    make altinstall && \
    cd .. && \
    rm -rf Python-3.13.1 Python-3.13.1.tgz && \
    ln -s /usr/local/python3.13/bin/python3.13 /usr/local/bin/python3.13 && \
    ln -s /usr/local/python3.13/bin/pip3.13 /usr/local/bin/pip3.13

# Julia (not in Debian repos). Optional — testing still works for other
# languages if this fails.
RUN wget -q https://julialang-s3.julialang.org/bin/linux/x64/1.10/julia-1.10.0-linux-x86_64.tar.gz -O /tmp/julia.tar.gz && \
    tar -xzf /tmp/julia.tar.gz -C /opt/ && \
    rm /tmp/julia.tar.gz && \
    ln -s /opt/julia-1.10.0/bin/julia /usr/local/bin/julia || echo "Julia installation failed, skipping"

# Match computor-base's worker user (uid lines up) so the copied env owns cleanly.
RUN useradd -ms /bin/bash worker
WORKDIR /home/worker
