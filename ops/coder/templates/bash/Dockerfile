# Minimal Debian workspace with a browser terminal (ttyd).
# No code-server, no VSIX — the workspace app is the terminal itself.
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
    && rm -rf /var/lib/apt/lists/*

# ttyd is not packaged in bookworm — install the official static binary
# Bump TTYD_VERSION and TTYD_SHA256 together (sha256 of ttyd.x86_64, matches the
# release SHA256SUMS).
ARG TTYD_VERSION=1.7.7
ARG TTYD_SHA256=8a217c968aba172e0dbf3f34447218dc015bc4d5e59bf51db2f2cd12b7be4f55
RUN curl -fsSL -o /usr/local/bin/ttyd \
    "https://github.com/tsl0922/ttyd/releases/download/${TTYD_VERSION}/ttyd.x86_64" \
    && echo "${TTYD_SHA256}  /usr/local/bin/ttyd" | sha256sum -c - \
    && chmod +x /usr/local/bin/ttyd

# UTF-8 locale for a sane terminal experience
RUN sed -i 's/^# *en_US.UTF-8/en_US.UTF-8/' /etc/locale.gen && locale-gen
ENV LANG=en_US.UTF-8

# uid 1000 'coder' with home at /home/coder — must match the other workspace
# images so the shared per-user home volume has consistent ownership.
# Passwordless sudo so students can apt-install their own toolchains; the
# workspace is untrusted-by-design and network-isolated (see the bash template
# variables + docker-compose.coder.yaml), so this matches the ubuntu-desktop and
# MATLAB images. Note: apt-installed packages live in the ephemeral container
# layer and are lost on rebuild — persistent setup belongs in ~/personalize.
RUN useradd --create-home --uid 1000 --shell /bin/bash coder \
    && usermod -aG sudo coder \
    && echo "coder ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/coder \
    && chmod 0440 /etc/sudoers.d/coder

USER coder
WORKDIR /home/coder
