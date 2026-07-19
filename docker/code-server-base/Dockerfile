# Shared base for every code-server-backed workspace template (vscode,
# matlab-vscode, ...). A drop-in replacement for ghcr.io/coder/code-server:
# the only delta is patch-webview-host.js, which makes webview rendering
# survive a failed/stuck service-worker handshake (Safari private windows,
# Lockdown Mode — computor-org/issues#274). Keeping the patch here means one
# copy of the patcher and every current or future code-server template
# inherits the fix by building FROM computor-code-server:latest.
#
# Built by computor.sh (like computor-base / computor-coder-runtime): on
# `--build` or when the image is missing. The temporal worker builds template
# images against the same host docker daemon, so the local tag resolves
# without a registry — but template builds fail if computor.sh has not built
# this image first.
FROM ghcr.io/coder/code-server:latest

USER root
COPY patch-webview-host.js /tmp/patch-webview-host.js
RUN /usr/lib/code-server/lib/node /tmp/patch-webview-host.js \
        /usr/lib/code-server/lib/vscode/out/vs/workbench/contrib/webview/browser/pre/index.html \
    && rm /tmp/patch-webview-host.js

# Restore the upstream image's user so this stays a drop-in replacement.
USER 1000
