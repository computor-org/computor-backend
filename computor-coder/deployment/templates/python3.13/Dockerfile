# =========================
# Stage 1: Build VSIX extension
# =========================
FROM node:20-bookworm AS vsix-builder

ARG EXTENSION_REPO_URL=https://github.com/computor-org/computor-vscode.git
ARG EXTENSION_REPO_REF=main

WORKDIR /build

# Install git
RUN apt-get update && apt-get install -y git \
    && rm -rf /var/lib/apt/lists/*

# Clone extension repository
RUN git clone --depth 1 --branch ${EXTENSION_REPO_REF} ${EXTENSION_REPO_URL} extension

WORKDIR /build/extension

# Build and package extension
RUN npm ci \
    && npm run compile --if-present \
    && npm run build --if-present \
    && npm install -g @vscode/vsce \
    && vsce package --out /tmp/extension.vsix

# =========================
# Stage 2: Runtime image with code-server
# =========================
FROM ghcr.io/coder/code-server:latest

USER root

# Install build dependencies for Python
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    libncursesw5-dev \
    libxml2-dev \
    libxmlsec1-dev \
    libffi-dev \
    liblzma-dev \
    wget \
    curl \
    git \
    socat \
    && rm -rf /var/lib/apt/lists/*

# Install Python 3.13 from source
ARG PYTHON_VERSION=3.13.1
RUN cd /tmp \
    && wget https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz \
    && tar -xzf Python-${PYTHON_VERSION}.tgz \
    && cd Python-${PYTHON_VERSION} \
    && ./configure --enable-optimizations --with-ensurepip=install \
    && make -j$(nproc) \
    && make altinstall \
    && cd / \
    && rm -rf /tmp/Python-${PYTHON_VERSION}*

# Create symlinks for python3 and pip3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/local/bin/python3.13 1 \
    && update-alternatives --install /usr/bin/pip3 pip3 /usr/local/bin/pip3.13 1 \
    && ln -sf /usr/local/bin/python3.13 /usr/bin/python \
    && ln -sf /usr/local/bin/pip3.13 /usr/bin/pip

# Prepare extensions directory
RUN mkdir -p /opt/code-server/extensions \
    && chown -R coder:coder /opt/code-server

# Allow pip to install packages system-wide
ENV PIP_BREAK_SYSTEM_PACKAGES=1

# Copy VSIX from builder stage
COPY --from=vsix-builder --chown=coder:coder /tmp/extension.vsix /opt/code-server/extension.vsix

USER coder

# Install extensions and clean up VSIX
RUN code-server --extensions-dir /opt/code-server/extensions --install-extension /opt/code-server/extension.vsix --force \
    && code-server --extensions-dir /opt/code-server/extensions --install-extension ms-python.python --force \
    && code-server --extensions-dir /opt/code-server/extensions --install-extension ms-toolsai.jupyter --force \
    && rm /opt/code-server/extension.vsix
