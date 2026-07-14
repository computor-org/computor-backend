# MATLAB R2024b with browser-based VS Code and the official MathWorks extension.
FROM ghcr.io/coder/code-server:latest AS code-server

FROM mathworks/matlab:r2024b

USER root

RUN export DEBIAN_FRONTEND=noninteractive \
    && apt-get update \
    && apt-get install --yes --no-install-recommends \
        ca-certificates \
        curl \
        git \
        socat \
    && rm -rf /var/lib/apt/lists/*

# Reuse code-server from its official image. Its Node runtime is bundled under
# /usr/lib/code-server, so only these two paths are needed at runtime.
COPY --from=code-server /usr/lib/code-server /usr/lib/code-server
COPY --from=code-server /usr/bin/code-server /usr/bin/code-server

# All Computor workspaces share /home/coder at uid 1000. Preserve the MATLAB
# image's home as a seed because the shared volume masks /home/coder at runtime.
# /home/matlab remains a compatibility symlink for matlab-proxy's pipx scripts.
RUN set -eux; \
    existing_user="$(getent passwd 1000 | cut -d: -f1)"; \
    if [ -n "$existing_user" ] && [ "$existing_user" != matlab ]; then usermod --uid 11000 "$existing_user"; fi; \
    existing_group="$(getent group 1000 | cut -d: -f1)"; \
    if [ -n "$existing_group" ] && [ "$existing_group" != matlab ]; then groupmod --gid 11000 "$existing_group"; fi; \
    usermod --uid 1000 --login coder --home /home/coder matlab; \
    groupmod --gid 1000 --new-name coder matlab; \
    sed -i 's/matlab/coder/g' /etc/sudoers.d/matlab; \
    mv /etc/sudoers.d/matlab /etc/sudoers.d/coder; \
    mv /home/matlab /opt/matlab-home-seed; \
    mkdir -p /home/coder /opt/code-server/extensions; \
    touch /home/coder/.volume-owner; \
    chown -R coder:coder /home/coder /opt/matlab-home-seed /opt/code-server/extensions; \
    ln -s /home/coder /home/matlab

ARG MATLAB_EXTENSION_VERSION=1.3.12
RUN curl -fsSL \
      "https://github.com/mathworks/MATLAB-extension-for-vscode/releases/download/v${MATLAB_EXTENSION_VERSION}/language-matlab-${MATLAB_EXTENSION_VERSION}.vsix" \
      -o /tmp/language-matlab.vsix \
    && chown coder:coder /tmp/language-matlab.vsix

USER coder
RUN code-server \
      --user-data-dir /tmp/code-server-data \
      --extensions-dir /opt/code-server/extensions \
      --install-extension /tmp/language-matlab.vsix --force \
    && rm -rf /tmp/language-matlab.vsix /tmp/code-server-data

USER root
RUN chown -R coder:coder /home/coder

USER coder
ENV HOME=/home/coder
ENV PATH=/home/matlab/.local/bin:${PATH}
WORKDIR /home/coder
