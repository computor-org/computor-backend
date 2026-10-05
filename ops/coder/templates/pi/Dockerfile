# Agent-harness workspace: the bash image plus Node.js and the pi coding agent
# (https://github.com/badlogic/pi-mono). The browser terminal (ttyd) runs pi
# directly instead of a login shell — see computor-pi and startup.sh.tftpl.
FROM node:24-bookworm-slim@sha256:0e0ff40c39bc087845bfb27465a0df4ea419520094bc35842ff83dd8cbe6f9b6 AS node

FROM debian:bookworm-slim@sha256:3783cc01769c7b2b1b83a5c5ad96c815348e28ed7da68e2e3687004faa906251

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    git \
    curl \
    wget \
    ca-certificates \
    socat \
    locales \
    nano \
    vim-tiny \
    less \
    procps \
    openssh-client \
    sudo \
    ripgrep \
    fd-find \
    && rm -rf /var/lib/apt/lists/*

# Node.js from the official image (same Debian release, so same glibc). Only
# node + npm/npx are taken — the rest of the node image (its uid-1000 'node'
# user, yarn) is not wanted here.
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && node --version && npm --version

# pi itself, pinned. Installed globally as root so a workspace without root
# cannot replace or "pi update --self" the harness; user-level pi packages and
# config still go to ~/.pi in the shared home.
ARG PI_VERSION=0.73.1
RUN npm install -g --no-fund --no-audit "@mariozechner/pi-coding-agent@${PI_VERSION}" \
    && npm cache clean --force \
    && pi --version

# ttyd is not packaged in bookworm — install the official static binary
# Bump TTYD_VERSION and TTYD_SHA256 together (sha256 of ttyd.x86_64, matches the
# release SHA256SUMS).
ARG TTYD_VERSION=1.7.7
ARG TTYD_SHA256=8a217c968aba172e0dbf3f34447218dc015bc4d5e59bf51db2f2cd12b7be4f55
RUN curl -fsSL -o /usr/local/bin/ttyd \
    "https://github.com/tsl0922/ttyd/releases/download/${TTYD_VERSION}/ttyd.x86_64" \
    && echo "${TTYD_SHA256}  /usr/local/bin/ttyd" | sha256sum -c - \
    && chmod +x /usr/local/bin/ttyd

# The terminal app: runs pi and restarts it when it exits, so the browser
# terminal never drops to a shell.
COPY computor-pi /usr/local/bin/computor-pi
RUN chmod 0755 /usr/local/bin/computor-pi

# UTF-8 locale for a sane terminal experience
RUN sed -i 's/^# *en_US.UTF-8/en_US.UTF-8/' /etc/locale.gen && locale-gen
ENV LANG=en_US.UTF-8

# The pi version is pinned by this image, so its startup update check and
# install telemetry are only noise (and fail outright without internet).
ENV PI_SKIP_VERSION_CHECK=1 \
    PI_TELEMETRY=0

# uid 1000 'coder' with home at /home/coder — must match the other workspace
# images so the shared per-user home volume has consistent ownership.
# Passwordless sudo, as in the bash image; whether it is usable is decided by
# the allow_root policy (no-new-privileges), not by the image.
RUN useradd --create-home --uid 1000 --shell /bin/bash coder \
    && usermod -aG sudo coder \
    && echo "coder ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/coder \
    && chmod 0440 /etc/sudoers.d/coder

USER coder
WORKDIR /home/coder
