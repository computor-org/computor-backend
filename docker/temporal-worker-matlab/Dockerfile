# Default matches the tag computor.sh builds from docker/matlab/Dockerfile when
# .env does not name a prebuilt image (ops/lib/common.sh owns the release).
ARG MATLAB_BASE_IMAGE=computor-matlab-base:r2025b
# Reuse the already-installed computor python environment from the shared base.
# The matlab base is a different OS image, so we can't `FROM computor-base`; we
# COPY from it instead. Both run CPython 3.12, so the installed wheels are ABI
# compatible. See docker/base/Dockerfile.
FROM computor-base AS pybase

FROM ${MATLAB_BASE_IMAGE}

USER root

# Install Python and system dependencies including tini for proper PID 1 handling.
#
# Python 3.12 is the system interpreter of Ubuntu 24.04 (noble), the OS under
# the R2025b MATLAB image, so no PPA is needed. It must match computor-base: the
# computor packages and their compiled dependencies are COPYed in below as
# cp312 wheels built there, so the interpreter that runs them has to be 3.12.
# Installing python3.12 here also pulls its current noble security update.
RUN export DEBIAN_FRONTEND=noninteractive \
    && apt-get update \
    && apt-get install --no-install-recommends --yes \
        python3.12 \
        python3.12-venv \
        python3.12-dev \
        python3-pip \
        git \
        nano \
        curl \
        tini \
    && apt-get clean \
    && apt-get autoremove \
    && rm -rf /var/lib/apt/lists/*

# Pin setuptools and the other build tools for the system 3.12. Must come
# BEFORE the engine install below, which needs setuptools for this interpreter.
#
# pip is the dpkg-owned python3-pip of noble. It carries no RECORD, so pip
# refuses to uninstall or upgrade it ("Cannot uninstall pip 24.0, RECORD file
# not found"). Hence: never upgrade pip itself here, and pass
# --ignore-installed so setuptools, wheel and packaging are installed fresh
# into /usr/local/lib/python3.12/dist-packages, which precedes the dpkg-owned
# /usr/lib/python3/dist-packages on the path. --break-system-packages is
# needed because noble marks its interpreter EXTERNALLY-MANAGED; these are
# image-build tools only, installed outside the dpkg-owned directories.
#
# The < 70 setuptools pin is not cosmetic — the COPYed computor deps include
# grapheme, which has no setuptools of its own and resolves pkg_resources from
# this interpreter at runtime.
# Both steps install from hash-locked, wheel-only files (compiled with the
# 7-day cooldown: uv pip compile --generate-hashes --python-version 3.12
# --exclude-newer <cutoff>), so the rebuild cannot pick up a newer release.
COPY docker/temporal-worker-matlab/bootstrap-setuptools.lock docker/temporal-worker-matlab/bootstrap-tools.lock /tmp/
RUN python3.12 -m pip install --break-system-packages --ignore-installed \
        --require-hashes --only-binary :all: -r /tmp/bootstrap-setuptools.lock \
    && python3.12 -m pip install --break-system-packages --ignore-installed \
        --require-hashes --only-binary :all: -r /tmp/bootstrap-tools.lock \
    && rm /tmp/bootstrap-setuptools.lock /tmp/bootstrap-tools.lock

# Derive MATLAB's root instead of naming a release. This image is built FROM
# ${MATLAB_BASE_IMAGE}, whose tag lives in .env, so a hardcoded
# /opt/matlab/R2024b breaks the build the moment that tag moves — and it is a
# `cd` into a missing directory, so it fails loudly rather than silently, but
# only after everything above it has already been built.
#
# The engine in R2025b supports Python 3.9-3.12 (its setup.py lists them),
# which covers the 3.12 interpreter the worker shares with computor-base.
#
# Invoked as `python3.12`, not `python`: noble has no unversioned `python` on
# PATH, and the engine has to land in the site-packages of the interpreter the
# worker runs.
RUN cd "$(dirname "$(dirname "$(readlink -f "$(which matlab)")")")/extern/engines/python" \
    && python3.12 setup.py install

# Drop the passwordless-sudo grant the MathWorks image ships and clear the
# matlab account password. Nothing below uses sudo, so this belongs up here with
# the other base tweaks instead of after the COPY steps, where it re-ran on every
# source change. Timezone likewise — it must be set as root, before USER matlab.
ENV TZ=UTC
RUN rm /etc/sudoers.d/localsudo \
    && passwd -d matlab \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone

# Everything above this line depends only on the MATLAB base, so it stays cached
# across source changes. Keep it that way: the COPY steps below move on every
# commit, and anything placed after them re-runs with them.

# Own the destination up front. COPY creates missing parents, and a root-owned
# /home/worker would leave the runtime user unable to write into it.
RUN install -d -o matlab -g matlab /home/worker

# Bring in the computor packages + their installed third-party deps from the
# shared base, at the SAME /home/worker path the editable installs were built
# against (so they resolve). PYTHONUSERBASE points matlab's python3.12 at the
# copied user-site; the MATLAB engine stays in the system site-packages.
#
# --chown rather than a trailing `chmod -R 777`: that chmod rewrote the mode bits
# of the whole copied tree — ~320 MB — into a fresh layer on top of an 8+ GB base
# on every single source edit. Setting ownership during the COPY costs nothing and
# leaves no extra layer. Same approach as docker/temporal-worker-testing/Dockerfile.
COPY --from=pybase --chown=matlab:matlab /home/worker/.local           /home/worker/.local
COPY --from=pybase --chown=matlab:matlab /home/worker/computor-types    /home/worker/computor-types
COPY --from=pybase --chown=matlab:matlab /home/worker/computor-client   /home/worker/computor-client
COPY --from=pybase --chown=matlab:matlab /home/worker/computor-backend  /home/worker/computor-backend

# Copy the matlab-server.py script
COPY --chown=matlab:matlab docker/temporal-worker-matlab/matlab-server.py /home/worker/matlab-server.py

USER matlab
WORKDIR /home/matlab

# Ensure python3.12 is used
ENV PYTHON_EXECUTABLE=/usr/bin/python3.12

# Use the computor env copied from the base: user-site deps + source on the path
ENV PYTHONUSERBASE=/home/worker/.local
ENV PATH=/home/worker/.local/bin:$PATH
ENV PYTHONPATH=/home/worker/computor-backend/src

# Default entrypoint - tini with -s registers as subreaper for zombie reaping
# even when not PID 1; -u for unbuffered Python output. matlab-server.py starts
# the temporal worker internally.
ENTRYPOINT ["/usr/bin/tini", "-s", "--", "python3.12", "-u", "/home/worker/matlab-server.py"]
