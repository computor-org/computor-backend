# Unified testing temporal worker — runs the testing queue. Adds the language
# runtimes (Octave, R, C/C++/Fortran, Python 3.13, Julia) and the
# computor-testing framework on top of the shared base. See docker/base/Dockerfile.
FROM computor-base:latest

USER root

# Language runtimes + Python build deps (for the 3.13 build below)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        wget \
        curl \
        # Python build dependencies
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

# Python 3.13 for test execution (alongside 3.10 for the worker)
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

# Julia (not in Debian repos). Optional — worker still functions if this fails.
RUN wget -q https://julialang-s3.julialang.org/bin/linux/x64/1.10/julia-1.10.0-linux-x86_64.tar.gz -O /tmp/julia.tar.gz && \
    tar -xzf /tmp/julia.tar.gz -C /opt/ && \
    rm /tmp/julia.tar.gz && \
    ln -s /opt/julia-1.10.0/bin/julia /usr/local/bin/julia || echo "Julia installation failed, skipping"

USER worker

# computor-testing framework (not part of the shared base)
ADD --chown=worker:worker computor-testing /home/worker/computor-testing
RUN pip install --user --no-warn-script-location /home/worker/computor-testing

# R user library
ENV R_LIBS_USER=/home/worker/.local/lib/R/library
RUN mkdir -p /home/worker/.local/lib/R/library

# Pre-build the Python 3.13 test venv with base testing deps at build time
# (avoids slow installs at container startup).
RUN python3.13 -m venv /home/worker/test-venv && \
    /home/worker/test-venv/bin/pip install --upgrade pip && \
    /home/worker/test-venv/bin/pip install -r /home/worker/computor-testing/requirements.txt
ENV PYTHON_TEST_EXECUTABLE=/home/worker/test-venv/bin/python

# Testing worker startup script: sets up language envs, then starts the worker.
COPY docker/temporal-worker-testing/testing-worker.py /home/worker/testing-worker.py
ENTRYPOINT ["python", "/home/worker/testing-worker.py"]
