FROM python:3.10-slim

# Install system dependencies and language runtimes for unified testing
RUN apt-get update && apt-get install -y \
    # Basic tools
    git \
    tzdata \
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

# Install Python 3.13 for test execution (alongside 3.10 for worker)
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

# Install Julia from official source (not available in Debian repos)
# Julia is optional - worker will still function for other languages if installation fails
RUN wget -q https://julialang-s3.julialang.org/bin/linux/x64/1.10/julia-1.10.0-linux-x86_64.tar.gz -O /tmp/julia.tar.gz && \
    tar -xzf /tmp/julia.tar.gz -C /opt/ && \
    rm /tmp/julia.tar.gz && \
    ln -s /opt/julia-1.10.0/bin/julia /usr/local/bin/julia || echo "Julia installation failed, skipping"

# Set timezone to UTC
ENV TZ=UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Create worker user
RUN useradd -ms /bin/bash worker
WORKDIR /home/worker

# Copy computor packages as root
ADD computor-types /home/worker/computor-types
ADD computor-utils /home/worker/computor-utils
ADD computor-client /home/worker/computor-client
ADD computor-backend /home/worker/computor-backend

# Change ownership
RUN chown -R worker:worker /home/worker

# Switch to worker user
USER worker

# Install local packages first (needed by computor-backend)
RUN pip install --user /home/worker/computor-types
RUN pip install --user /home/worker/computor-utils
RUN pip install --user /home/worker/computor-client

# Install computor-backend with all dependencies
RUN pip install --user /home/worker/computor-backend

# Create directory for computor-testing installation (will be cloned at runtime)
RUN mkdir -p /home/worker/computor-testing

# Add src to PYTHONPATH so imports work
ENV PYTHONPATH=/home/worker/computor-backend/src:$PYTHONPATH

# Add user local bin to PATH (for computor-test CLI after installation)
ENV PATH=/home/worker/.local/bin:$PATH

# Set up R library path for user packages
ENV R_LIBS_USER=/home/worker/.local/lib/R/library
RUN mkdir -p /home/worker/.local/lib/R/library

# Copy the testing worker startup script
COPY docker/temporal-worker-testing/testing-worker.py /home/worker/testing-worker.py

# Entry point runs the startup script which:
# 1. Clones/updates computor-testing repository
# 2. Installs computor-testing framework
# 3. Starts the temporal worker
ENTRYPOINT ["python", "/home/worker/testing-worker.py"]
