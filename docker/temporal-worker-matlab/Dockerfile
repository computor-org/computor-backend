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

# Copy computor-types, computor-utils and computor-backend
ADD computor-types /home/matlab/computor-types
ADD computor-utils /home/matlab/computor-utils
ADD computor-backend /home/matlab/computor-backend

# Copy the matlab-server.py script
COPY docker/temporal-worker-matlab/matlab-server.py /home/matlab/matlab-server.py

# Install local packages first (computor-types and computor-utils)
RUN pip install --no-cache-dir -e /home/matlab/computor-types
RUN pip install --no-cache-dir -e /home/matlab/computor-utils

# Install dependencies
RUN pip install --no-cache-dir --upgrade -r /home/matlab/computor-backend/src/requirements.txt

RUN chmod -R 777 /home/matlab

RUN rm /etc/sudoers.d/localsudo
RUN passwd -d matlab

USER matlab
WORKDIR /home/matlab

ENV TZ=UTC
ENV TZ=Europe/Berlin

# Ensure python3.10 is used
ENV PYTHON_EXECUTABLE=/usr/bin/python3.10

# Add src to PYTHONPATH so imports work
ENV PYTHONPATH=/home/matlab/computor-backend/src:$PYTHONPATH

# Default entrypoint - matlab-server.py will start the temporal worker internally
ENTRYPOINT ["python", "/home/matlab/matlab-server.py"]