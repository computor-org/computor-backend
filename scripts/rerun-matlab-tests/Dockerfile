# Dockerfile for MATLAB Artifact Regeneration
#
# This creates a container that can re-run MATLAB tests to regenerate artifacts
# for existing test results. Based on the temporal-worker-matlab image.
#
# Build:
#   docker build -t matlab-artifact-regenerator -f scripts/rerun-matlab-tests/Dockerfile .
#
# Run:
#   docker run --rm \
#     --env-file .env \
#     -e POSTGRES_HOST=host.docker.internal \
#     -e MINIO_ENDPOINT=host.docker.internal:9000 \
#     -e API_URL=http://host.docker.internal:8000 \
#     matlab-artifact-regenerator --limit 10

ARG MATLAB_BASE_IMAGE=registry.gitlab.tugraz.at/codeability/testing-frameworks/itp-matlab-testing/matlab:r2024b
FROM ${MATLAB_BASE_IMAGE}

# Switch to root for installations
USER root

# Install Python 3.10 and dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-venv \
    python3.10-dev \
    python3-pip \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY computor-types/ /app/computor-types/
COPY computor-client/ /app/computor-client/

# Install MATLAB Python engine
RUN cd /opt/matlab/R2024b/extern/engines/python && python3.10 setup.py install

# Install Python packages
RUN python3.10 -m pip install --upgrade pip && \
    python3.10 -m pip install \
    psycopg2-binary \
    python-dotenv \
    httpx \
    minio \
    pyyaml \
    && python3.10 -m pip install -e /app/computor-types/ \
    && python3.10 -m pip install -e /app/computor-client/

# Copy the regenerator script
COPY scripts/rerun-matlab-tests/artifact_regenerator.py /app/artifact_regenerator.py

# Create matlab user if not exists and set permissions
RUN useradd -m -s /bin/bash matlab 2>/dev/null || true && \
    chown -R matlab:matlab /app

# Switch to matlab user
USER matlab

# Set environment
ENV PYTHONUNBUFFERED=1
ENV HOME=/home/matlab

ENTRYPOINT ["python3.10", "/app/artifact_regenerator.py"]
CMD []
