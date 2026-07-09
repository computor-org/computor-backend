# Ubuntu XFCE desktop workspace served in the browser via KasmVNC.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# XFCE desktop + basics. No browser preinstalled (firefox on 24.04 is
# snap-only, which does not work in docker) — the user has sudo and the
# ~/personalize hook to add one.
RUN apt-get update && apt-get install -y --no-install-recommends \
    xfce4 \
    xfce4-terminal \
    dbus-x11 \
    x11-xserver-utils \
    xterm \
    mousepad \
    sudo \
    git \
    curl \
    wget \
    ca-certificates \
    socat \
    locales \
    nano \
    less \
    procps \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# UTF-8 locale
RUN sed -i 's/^# *en_US.UTF-8/en_US.UTF-8/' /etc/locale.gen && locale-gen
ENV LANG=en_US.UTF-8

# KasmVNC server (web-native VNC: built-in webserver + websocket transport)
ARG KASMVNC_VERSION=1.3.4
RUN curl -fsSL -o /tmp/kasmvncserver.deb \
    "https://github.com/kasmtech/KasmVNC/releases/download/v${KASMVNC_VERSION}/kasmvncserver_noble_${KASMVNC_VERSION}_amd64.deb" \
    && apt-get update \
    && apt-get install -y --no-install-recommends /tmp/kasmvncserver.deb \
    && rm /tmp/kasmvncserver.deb \
    && rm -rf /var/lib/apt/lists/*

# uid 1000 'coder' with home at /home/coder — must match the other workspace
# images so the shared per-user home volume has consistent ownership.
# Ubuntu 24.04 ships a stock uid-1000 'ubuntu' user that has to go first.
RUN userdel -r ubuntu \
    && useradd --create-home --uid 1000 --shell /bin/bash coder \
    && usermod -aG sudo,ssl-cert coder \
    && echo "coder ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/coder \
    && chmod 0440 /etc/sudoers.d/coder

USER coder
WORKDIR /home/coder
