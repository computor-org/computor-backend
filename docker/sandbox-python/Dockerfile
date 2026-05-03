# Minimal Python sandbox image for student-code execution.
#
# Built once and pinned via CT_RUNNER_DOCKER_IMAGE / CT_SANDBOX_DOCKER_IMAGE
# (default tag: ``ct-sandbox:python``). The DockerRunner in
# ``computor-testing/sandbox/backends.py`` invokes containers from this
# image with ``--rm --read-only --cap-drop=ALL --security-opt=no-new-privileges:true``
# (see backends.py for the full flag set), so this image only needs
# Python plus the assignment-runtime libraries.
#
# Intentionally NOT included: git, curl, wget, ssh, build toolchain, pip,
# extra shells. The deny-list at AST-time and the container hardening
# at runtime are layered defences; keeping the image surface minimal is
# the third layer.
#
# Build:
#   docker build -f docker/sandbox-python/Dockerfile -t ct-sandbox:python .
# (run from the repo root — the COPY needs ``computor-testing/requirements.txt``)

FROM python:3.10-slim AS deps

# Build deps for numpy/scipy/sympy native wheels. Discarded in the
# final stage via multi-stage copy.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        gfortran \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY computor-testing/requirements.txt /build/requirements.txt

# Install into a venv we can copy into the runtime image. ``--no-cache-dir``
# keeps the layer small.
RUN python -m venv /opt/sandbox-venv \
 && /opt/sandbox-venv/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/sandbox-venv/bin/pip install --no-cache-dir -r /build/requirements.txt


FROM python:3.10-slim

# Runtime libs needed by the wheels we copy in. matplotlib needs
# libfreetype6 + libpng16 (when not using --no-binary), and scipy
# pulls in libgomp1.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        libgomp1 \
        libfreetype6 \
        libpng16-16 \
 && rm -rf /var/lib/apt/lists/* \
 && apt-get clean

# Non-root execution. The DockerRunner also passes ``--user 1000:1000``
# at runtime; the UID is created here so chown works at build time.
RUN useradd -ms /bin/bash -u 1000 sandbox

COPY --from=deps /opt/sandbox-venv /opt/sandbox-venv

# ``ct-sandbox:python`` is invoked with ``cwd:/sandbox:rw`` mounted by
# the runner. The default WORKDIR matches the mount point so the
# wrapper script's ``[python, /sandbox/<wrapper>.py]`` cmd resolves.
WORKDIR /sandbox

ENV PATH="/opt/sandbox-venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg

USER sandbox
