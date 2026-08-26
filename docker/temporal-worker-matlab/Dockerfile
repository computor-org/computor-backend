# Default matches the tag computor.sh builds from docker/matlab/Dockerfile when
# .env does not name a prebuilt image (ops/lib/common.sh owns the release).
ARG MATLAB_BASE_IMAGE=computor-matlab-base:r2025b
# Reuse the already-installed computor python environment from the shared base.
# The matlab base is a different OS image, so we can't `FROM computor-base`; we
# COPY from it instead. Both run CPython 3.10, so the installed wheels are ABI
# compatible. See docker/base/Dockerfile.
FROM computor-base AS pybase

FROM ${MATLAB_BASE_IMAGE}

USER root

# Install Python and system dependencies including tini for proper PID 1 handling.
#
# python3.10 comes from deadsnakes because the OS under the MATLAB image moved
# to Ubuntu 24.04 (noble) with R2025b, and noble packages python3.12 ONLY —
# `apt-get install python3.10` there fails with "Unable to locate package".
# R2024b sat on jammy, whose system python IS 3.10, which is why this worked
# without a PPA until the release bump. The 3.10 pin itself is not negotiable
# here: the computor packages and their compiled dependencies are COPYed in
# below as cp310 wheels built in computor-base, so the interpreter that runs
# them has to be 3.10 as well.
RUN export DEBIAN_FRONTEND=noninteractive \
    && apt-get update \
    && apt-get install --no-install-recommends --yes \
        software-properties-common \
        ca-certificates \
    && add-apt-repository --yes ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install --no-install-recommends --yes \
        python3.10 \
        python3.10-venv \
        python3.10-dev \
        git \
        nano \
        curl \
        tini \
    && apt-get clean \
    && apt-get autoremove \
    && rm -rf /var/lib/apt/lists/*

# Bootstrap pip for 3.10 and pin setuptools. Must come BEFORE the engine install
# below, which needs setuptools for this interpreter.
#
# ensurepip (shipped by python3.10-venv) rather than the `python3-pip` package:
# that one belongs to the system 3.12. It is still *importable* from 3.10 —
# Debian puts arch-independent modules in /usr/lib/python3/dist-packages, which
# is on every Debian python's sys.path — but it is dpkg-owned and carries no
# RECORD, so pip refuses to uninstall or upgrade it ("Cannot uninstall pip 24.0,
# RECORD file not found"). Hence: never upgrade pip itself here, and pass
# --ignore-installed for the other dpkg-owned distributions (wheel, packaging)
# so they are installed fresh into /usr/local/lib/python3.10/dist-packages,
# which precedes /usr/lib/python3/dist-packages on the path.
#
# setuptools gets its own step WITHOUT --ignore-installed on purpose: ensurepip
# leaves a 79.x behind, and ignoring it would let that shadow the version we ask
# for here. The < 70 pin is not cosmetic — the COPYed computor deps include
# grapheme, which has no setuptools of its own and resolves pkg_resources from
# this interpreter at runtime.
RUN python3.10 -m ensurepip --upgrade \
    && python3.10 -m pip install --upgrade "setuptools>=65.0,<70" \
    && python3.10 -m pip install --upgrade --ignore-installed wheel packaging

# Derive MATLAB's root instead of naming a release. This image is built FROM
# ${MATLAB_BASE_IMAGE}, whose tag lives in .env, so a hardcoded
# /opt/matlab/R2024b breaks the build the moment that tag moves — and it is a
# `cd` into a missing directory, so it fails loudly rather than silently, but
# only after everything above it has already been built.
#
# Python 3.10 stays supported by the engine in R2025b (its setup.py lists
# 3.9-3.12, unchanged from R2024b), which is what lets the worker keep the
# 3.10 pin it shares with computor-base.
#
# Invoked as `python3.10`, not `python`: noble has no unversioned `python` on
# PATH, and the engine has to land in the site-packages of the interpreter the
# worker runs — not the system 3.12's.
RUN cd "$(dirname "$(dirname "$(readlink -f "$(which matlab)")")")/extern/engines/python" \
    && python3.10 setup.py install

# Bring in the computor packages + their installed third-party deps from the
# shared base, at the SAME /home/worker path the editable installs were built
# against (so they resolve). PYTHONUSERBASE points matlab's python3.10 at the
# copied user-site; the MATLAB engine stays in the system site-packages.
COPY --from=pybase /home/worker/.local           /home/worker/.local
COPY --from=pybase /home/worker/computor-types    /home/worker/computor-types
COPY --from=pybase /home/worker/computor-client   /home/worker/computor-client
COPY --from=pybase /home/worker/computor-backend  /home/worker/computor-backend

# Copy the matlab-server.py script
COPY docker/temporal-worker-matlab/matlab-server.py /home/worker/matlab-server.py

RUN chmod -R 777 /home/worker

RUN rm /etc/sudoers.d/localsudo
RUN passwd -d matlab

# Set timezone to UTC (must be done as root before switching user)
ENV TZ=UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

USER matlab
WORKDIR /home/matlab

# Ensure python3.10 is used
ENV PYTHON_EXECUTABLE=/usr/bin/python3.10

# Use the computor env copied from the base: user-site deps + source on the path
ENV PYTHONUSERBASE=/home/worker/.local
ENV PATH=/home/worker/.local/bin:$PATH
ENV PYTHONPATH=/home/worker/computor-backend/src

# Default entrypoint - tini with -s registers as subreaper for zombie reaping
# even when not PID 1; -u for unbuffered Python output. matlab-server.py starts
# the temporal worker internally.
ENTRYPOINT ["/usr/bin/tini", "-s", "--", "python3.10", "-u", "/home/worker/matlab-server.py"]
