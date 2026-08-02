# MATLAB R2025b with browser-based VS Code, Computor and MathWorks extensions.
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

RUN apt-get update \
    && apt-get install --yes --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Fetch the exact commit rather than the branch tip: it pins what the resolver
# saw (no resolve-then-clone race) and keys the layer on the SHA.
RUN git init extension \
    && cd extension \
    && git remote add origin "${EXTENSION_REPO_URL}" \
    && git fetch --depth 1 origin "${EXTENSION_REPO_SHA:-${EXTENSION_REPO_REF}}" \
    && git checkout --detach FETCH_HEAD

WORKDIR /build/extension

RUN npm ci \
    && npm run compile --if-present \
    && npm run build --if-present \
    && npm install --global @vscode/vsce \
    && vsce package --out /tmp/computor-extension.vsix

# computor-code-server = upstream code-server + the webview service-worker
# patch (issue #274); built by computor.sh from docker/code-server-base/.
FROM computor-code-server:latest AS code-server

# Digest-pinned to R2025b Update 5, same digest as matlab-ui — the two matlab
# templates seed the same shared per-user home volume, so they must stay on
# identical MATLAB builds.
#
# This template does not serve the browser desktop (code-server plus the
# MathWorks extension talks to MATLAB directly), so matlab-proxy#88 never
# applied to it; see matlab-ui's Dockerfile for how that bug was retested
# before this bump.
FROM mathworks/matlab:r2025b@sha256:7528b0873df0c6b640013cc37cceb848c60261aa2a7e44bd64387be7678b0ff0

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

# Record which extension commit this image carries, so "did my change actually
# ship?" is answerable with `docker image inspect` instead of archaeology on
# layer dates. ARGs are per-stage, hence the re-declaration.
ARG EXTENSION_REPO_SHA=""
LABEL computor.extension.revision="${EXTENSION_REPO_SHA}"

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

# Figures. There is no desktop in this container, so a MATLAB figure window
# has nowhere to appear and a student's `plot(x, y)` would produce nothing
# they can see. figurewatch mirrors every figure of a session into
# COMPUTOR_FIGURES_DIR, where the Computor extension picks it up. It needs no
# display: MATLAB exports figures from a session that has none.
#
# The bootstrap is appended to matlabrc.m rather than dropped in as
# toolbox/local/startup.m, which is what it used to be and why it published
# nothing: the MathWorks base image seeds its own startup.m into
# ~/Documents/MATLAB, that folder is the userpath and comes first on the
# search path, and MATLAB runs only the first `startup` it finds. Both files
# run for every session in this image, including the background MATLAB the
# MathWorks extension starts to run and debug code — but only matlabrc.m
# cannot be shadowed from a home directory. See docs/figures.md.
#
# R2025b's matlabrc.m is still a plain script with no trailing local functions
# (checked when moving off R2024b), so appending to it remains sound. Recheck
# that when the MATLAB version moves again — a file that ends in local
# functions cannot be extended this way.
COPY figures/+figurewatch /opt/computor/matlab/+figurewatch
COPY figures/matlabrc-figurewatch.m /tmp/matlabrc-figurewatch.m
RUN printf '\n' >> /opt/matlab/R2025b/toolbox/local/matlabrc.m \
    && cat /tmp/matlabrc-figurewatch.m >> /opt/matlab/R2025b/toolbox/local/matlabrc.m \
    && rm /tmp/matlabrc-figurewatch.m
ENV COMPUTOR_FIGURES_DIR=/tmp/computor-figures

RUN chown -R coder:coder /home/coder

USER coder
ENV HOME=/home/coder
ENV PATH=/home/matlab/.local/bin:${PATH}
WORKDIR /home/coder
