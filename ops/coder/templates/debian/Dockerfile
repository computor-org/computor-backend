# =========================
# Stage 1: Build VSIX extension
# =========================
FROM node:20-bookworm AS vsix-builder

ARG EXTENSION_REPO_URL=https://github.com/computor-org/computor-vscode.git
ARG EXTENSION_REPO_REF="release/2026.10"

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
# Stage 2: Runtime image with code-server (plain Debian, no toolchains)
# =========================
FROM ghcr.io/coder/code-server:latest

USER root

RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    curl \
    git \
    socat \
    nano \
    less \
    procps \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Prepare extensions directory
RUN mkdir -p /opt/code-server/extensions \
    && chown -R coder:coder /opt/code-server

# Copy VSIX from builder stage
COPY --from=vsix-builder --chown=coder:coder /tmp/extension.vsix /opt/code-server/extension.vsix

USER coder

# Install the Computor extension and clean up the VSIX
RUN code-server --extensions-dir /opt/code-server/extensions --install-extension /opt/code-server/extension.vsix --force \
    && rm /opt/code-server/extension.vsix
