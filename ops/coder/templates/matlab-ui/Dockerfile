# MATLAB R2025b native browser UI, served by the image's MATLAB Proxy.
#
# Digest-pinned to R2025b Update 5. The previous pin was R2024b Update 6,
# because Update 8 broke the browser desktop under a non-empty MWI_BASE_URL
# (file open failed with "Invalid function name", icon and label bundles 404'd
# on a doubled path prefix) — https://github.com/mathworks/matlab-proxy/issues/88,
# still open upstream. This release line was validated against that bug rather
# than assumed clear of it: R2025b Update 5 was run behind MWI_BASE_URL
# =/coder/<owner>/<workspace> and the desktop rendered in full — ribbon, file
# browser, icons, navigation — and `edit('startup.m')` opened the editor with no
# error and no failed request. The #88 symptoms do not reproduce here.
#
# One nested-base-URL defect does remain, and it is new in this release: the
# desktop requests `<base>toolbox/studio/cache-js/src/workers/PersistenceWorker.js`
# — the base and the path joined without a separator — which 404s and logs
# "WorkerService error". R2024b Update 6 does not do this. It costs the
# desktop's own state persistence, not the session, so it is a known blemish
# rather than a blocker. Recheck it when moving again.
#
# Keep this digest identical to matlab-vscode's: the two templates seed the
# same shared per-user home volume and must be on the same MATLAB build.
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

# Match the uid-1000 /home/coder contract used by every workspace template.
# Keep MathWorks' original home as a runtime seed because it contains the pipx
# MATLAB Proxy installation and preferences hidden by the shared-home mount.
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
    mkdir -p /home/coder; \
    touch /home/coder/.volume-owner; \
    chown -R coder:coder /home/coder /opt/matlab-home-seed; \
    ln -s /home/coder /home/matlab

USER coder
ENV HOME=/home/coder
ENV PATH=/home/matlab/.local/bin:${PATH}
WORKDIR /home/coder
