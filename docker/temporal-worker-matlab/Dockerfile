# Build argument for base image - defaults to local build, can be overridden
# ARG MATLAB_BASE_IMAGE=matlab-base:latest

# # Use the MATLAB base image (can be overridden via --build-arg)
# FROM ${MATLAB_BASE_IMAGE}

FROM registry.gitlab.tugraz.at/codeability/testing-frameworks/itp-matlab-testing/matlab:r2024b

USER root

# Install Python and system dependencies
RUN export DEBIAN_FRONTEND=noninteractive \
    && apt-get update \
    && apt-get install --no-install-recommends --yes \
        software-properties-common \
        python3.10 \
        python3-pip \
        python3.10-venv \
        libpython3.10-dev \
        git \
        nano \
        curl \
    && apt-get clean \
    && apt-get autoremove \
    && rm -rf /var/lib/apt/lists/*

RUN cd /opt/matlab/R2024b/extern/engines/python && python setup.py install

# Upgrade pip, setuptools and packaging to support modern pyproject.toml
# Use setuptools < 70 to avoid grapheme package compatibility issues
RUN python3.10 -m pip install --upgrade pip "setuptools>=65.0,<70" wheel packaging

# Copy computor-types, computor-utils, computor-client and computor-backend
ADD computor-types /home/matlab/computor-types
ADD computor-utils /home/matlab/computor-utils
ADD computor-client /home/matlab/computor-client
ADD computor-backend /home/matlab/computor-backend

# Copy the matlab-server.py script
COPY docker/temporal-worker-matlab/matlab-server.py /home/matlab/matlab-server.py

# Install local packages first (needed by computor-backend)
# Use python3.10 explicitly to ensure correct Python version
RUN python3.10 -m pip install --no-cache-dir /home/matlab/computor-types
RUN python3.10 -m pip install --no-cache-dir /home/matlab/computor-utils
RUN python3.10 -m pip install --no-cache-dir /home/matlab/computor-client

# Install computor-backend with all dependencies
RUN python3.10 -m pip install --no-cache-dir /home/matlab/computor-backend

RUN chmod -R 777 /home/matlab

RUN rm /etc/sudoers.d/localsudo
RUN passwd -d matlab

USER matlab
WORKDIR /home/matlab

# Set timezone to UTC
ENV TZ=UTC

# Ensure python3.10 is used
ENV PYTHON_EXECUTABLE=/usr/bin/python3.10

# Add src to PYTHONPATH so imports work
ENV PYTHONPATH=/home/matlab/computor-backend/src:$PYTHONPATH

# Default entrypoint - matlab-server.py will start the temporal worker internally
ENTRYPOINT ["python3.10", "/home/matlab/matlab-server.py"]