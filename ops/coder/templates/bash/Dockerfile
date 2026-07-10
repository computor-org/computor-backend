# Minimal Debian workspace with a browser terminal (ttyd).
# No code-server, no VSIX — the workspace app is the terminal itself.
FROM debian:bookworm-slim

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
    && rm -rf /var/lib/apt/lists/*

# ttyd is not packaged in bookworm — install the official static binary
ARG TTYD_VERSION=1.7.7
RUN curl -fsSL -o /usr/local/bin/ttyd \
    "https://github.com/tsl0922/ttyd/releases/download/${TTYD_VERSION}/ttyd.x86_64" \
    && chmod +x /usr/local/bin/ttyd

# UTF-8 locale for a sane terminal experience
RUN sed -i 's/^# *en_US.UTF-8/en_US.UTF-8/' /etc/locale.gen && locale-gen
ENV LANG=en_US.UTF-8

# uid 1000 'coder' with home at /home/coder — must match the other workspace
# images so the shared per-user home volume has consistent ownership
RUN useradd --create-home --uid 1000 --shell /bin/bash coder

USER coder
WORKDIR /home/coder
