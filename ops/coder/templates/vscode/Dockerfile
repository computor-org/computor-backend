# =========================
# Stage 1: Build VSIX extension
# =========================
FROM node:20-bookworm AS vsix-builder

ARG EXTENSION_REPO_URL=https://github.com/computor-org/computor-vscode.git
ARG EXTENSION_REPO_REF="release/2026.10"
# The commit EXTENSION_REPO_REF pointed at when the build was submitted,
# resolved and passed in by build_workspace_image (see the template's
# source_repos manifest key). It exists to move this stage's cache key: docker
# keys a RUN layer on its command string, so checking out a *branch name* is
# byte-identical forever — the first checkout ever made stays cached and no
# later commit reaches the image. The extension's package.json version has no
# bearing on that; the checkout simply never runs again.
#
# Empty (a bare `docker build`) falls back to the ref, and with it to the old
# caching behaviour — fine for a one-off local build, never for the fleet.
ARG EXTENSION_REPO_SHA=""

WORKDIR /build

# Install git
RUN apt-get update && apt-get install -y git \
    && rm -rf /var/lib/apt/lists/*

# Fetch the exact commit rather than the branch tip: it pins what the resolver
# saw (no resolve-then-clone race) and keys the layer on the SHA.
RUN git init extension \
    && cd extension \
    && git remote add origin "${EXTENSION_REPO_URL}" \
    && for attempt in 1 2 3; do \
        GIT_TERMINAL_PROMPT=0 git -c http.version=HTTP/1.1 fetch --depth 1 origin "${EXTENSION_REPO_SHA:-${EXTENSION_REPO_REF}}" \
          && break; \
        test "$attempt" -lt 3 || exit 1; \
        sleep $((attempt * 2)); \
      done \
    && git checkout --detach FETCH_HEAD

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
# computor-code-server = upstream code-server + the webview service-worker
# patch (issue #274); built by computor.sh from docker/code-server-base/.
FROM computor-code-server:latest

USER root

# Build dependencies for Python, plus openssh-client: ssh-keygen and ssh let a
# student generate a key in the workspace and clone their own GitLab/GitHub
# project over SSH (computor-org/issues#391). Upstream code-server happens to
# ship the package today — naming it here keeps a base-image bump from quietly
# taking ssh-keygen away.
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
    openssh-client \
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

# Plotting. There is no desktop in this container, so no matplotlib GUI
# backend can work: a student running `python task.py` in the terminal would
# get nothing from plt.show(). computor_figures renders with Agg and publishes
# each figure into COMPUTOR_FIGURES_DIR, where the Computor extension picks it
# up. See docs/figures.md.
RUN pip install --no-cache-dir matplotlib ipykernel

COPY figures/computor_figures.py /tmp/computor_figures.py
RUN python3 -c "import shutil, sysconfig; shutil.copy('/tmp/computor_figures.py', sysconfig.get_paths()['purelib'])" \
    && rm /tmp/computor_figures.py

ENV COMPUTOR_FIGURES_DIR=/tmp/computor-figures \
    MPLBACKEND=module://computor_figures

# Notebooks keep their inline plots — see the IPython profile the startup
# script writes. It cannot be baked in here: IPython reads config from the
# profile directory under IPYTHONDIR and from nowhere else, so it has to be
# written into the user's home at start.

# Record which extension commit this image carries, so "did my change actually
# ship?" is answerable with `docker image inspect` instead of archaeology on
# layer dates. ARGs are per-stage, hence the re-declaration.
ARG EXTENSION_REPO_SHA=""
LABEL computor.extension.revision="${EXTENSION_REPO_SHA}"

# Copy VSIX from builder stage
COPY --from=vsix-builder --chown=coder:coder /tmp/extension.vsix /opt/code-server/extension.vsix

USER coder

# Install extensions and clean up VSIX
RUN code-server --extensions-dir /opt/code-server/extensions --install-extension /opt/code-server/extension.vsix --force \
    && code-server --extensions-dir /opt/code-server/extensions --install-extension ms-python.python --force \
    && code-server --extensions-dir /opt/code-server/extensions --install-extension ms-toolsai.jupyter --force \
    && rm /opt/code-server/extension.vsix
