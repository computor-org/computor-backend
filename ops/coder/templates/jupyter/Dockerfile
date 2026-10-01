# JupyterLab workspace served in the browser. The workspace app is JupyterLab
# itself (no code-server, no desktop). No sudo — students add Python packages
# with `pip install --user`, which persists in the shared /home/coder volume.
FROM python:3.14-slim-bookworm@sha256:82bc3c539b8813ada9d68c63b40158fa002f7f33de9bf3312a3dfdc0620dff56

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
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
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# UTF-8 locale
RUN sed -i 's/^# *en_US.UTF-8/en_US.UTF-8/' /etc/locale.gen && locale-gen
ENV LANG=en_US.UTF-8

# JupyterLab + a scientific Python stack useful across engineering courses.
# Students add more with `pip install --user` (persisted in the shared home).
# Installed from a hash-locked requirements file (see requirements.in for how
# to regenerate it) so a rebuild never pulls a newer or tampered release.
COPY requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir --require-hashes --only-binary :all: -r /tmp/requirements.lock \
    && rm /tmp/requirements.lock

# uid 1000 'coder' with home at /home/coder — must match the other workspace
# images so the shared per-user home volume has consistent ownership.
RUN useradd --create-home --uid 1000 --shell /bin/bash coder

# Put user-level pip installs (pip install --user) on PATH for the coder user.
ENV PATH=/home/coder/.local/bin:$PATH

USER coder
WORKDIR /home/coder
