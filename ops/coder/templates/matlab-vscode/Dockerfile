# MATLAB R2024b with browser-based VS Code, Computor and MathWorks extensions.
FROM node:20-bookworm AS vsix-builder

ARG EXTENSION_REPO_URL=https://github.com/computor-org/computor-vscode.git
ARG EXTENSION_REPO_REF="release/2026.10"

WORKDIR /build

RUN apt-get update \
    && apt-get install --yes --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 --branch "${EXTENSION_REPO_REF}" "${EXTENSION_REPO_URL}" extension

WORKDIR /build/extension

RUN npm ci \
    && npm run compile --if-present \
    && npm run build --if-present \
    && npm install --global @vscode/vsce \
    && vsce package --out /tmp/computor-extension.vsix

FROM ghcr.io/coder/code-server:latest AS code-server

# Make webview rendering survive a failed/stuck service-worker handshake
# (Safari private windows, Lockdown Mode — computor-org/issues#274). Applied
# here so the COPY --from=code-server below ships the patched webview host.
USER root
COPY patch-webview-host.js /tmp/patch-webview-host.js
RUN /usr/lib/code-server/lib/node /tmp/patch-webview-host.js \
        /usr/lib/code-server/lib/vscode/out/vs/workbench/contrib/webview/browser/pre/index.html \
    && rm /tmp/patch-webview-host.js

# Digest-pinned to R2024b Update 6, same digest as matlab-ui: Update 8 breaks
# the browser desktop under a non-empty MWI_BASE_URL (matlab-proxy#88), and the
# two matlab templates must stay on identical MATLAB builds because they seed
# the same shared per-user home volume.
FROM mathworks/matlab:r2024b@sha256:5603328923de4fd5ba5d5b610fbb925e1bcb8aec253df5d17e47bf95f351ca46

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

COPY --from=vsix-builder --chown=coder:coder \
    /tmp/computor-extension.vsix /tmp/computor-extension.vsix

USER coder
RUN code-server \
      --user-data-dir /tmp/code-server-data \
      --extensions-dir /opt/code-server/extensions \
      --install-extension /tmp/language-matlab.vsix --force \
    && code-server \
      --user-data-dir /tmp/code-server-data \
      --extensions-dir /opt/code-server/extensions \
      --install-extension /tmp/computor-extension.vsix --force \
    && rm -rf \
      /tmp/language-matlab.vsix \
      /tmp/computor-extension.vsix \
      /tmp/code-server-data

USER root
RUN chown -R coder:coder /home/coder

USER coder
ENV HOME=/home/coder
ENV PATH=/home/matlab/.local/bin:${PATH}
WORKDIR /home/coder
