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
# Stage 2: Runtime image with MATLAB + code-server
# =========================
FROM registry.gitlab.tugraz.at/codeability/testing-frameworks/itp-matlab-testing/matlab:r2024b

USER root

# Install code-server and dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install code-server
ARG CODE_SERVER_VERSION=4.96.4
RUN curl -fsSL https://code-server.dev/install.sh | sh -s -- --version=${CODE_SERVER_VERSION}

# Prepare extensions directory
RUN mkdir -p /opt/code-server/extensions \
    && chown -R matlab:matlab /opt/code-server

# Copy VSIX from builder stage
COPY --from=vsix-builder --chown=matlab:matlab /tmp/extension.vsix /opt/code-server/extension.vsix

USER matlab

# Install extensions and clean up VSIX
RUN code-server --extensions-dir /opt/code-server/extensions --install-extension /opt/code-server/extension.vsix --force \
    && code-server --extensions-dir /opt/code-server/extensions --install-extension MathWorks.language-matlab --force \
    && rm /opt/code-server/extension.vsix
