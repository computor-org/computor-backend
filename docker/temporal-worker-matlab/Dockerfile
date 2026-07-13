ARG MATLAB_BASE_IMAGE=matlab-base:latest
# Reuse the already-installed computor python environment from the shared base.
# The matlab base is a different OS image, so we can't `FROM computor-base`; we
# COPY from it instead. Both run CPython 3.10, so the installed wheels are ABI
# compatible. See docker/base/Dockerfile.
FROM computor-base:latest AS pybase

FROM ${MATLAB_BASE_IMAGE}

USER root

# Install Python and system dependencies including tini for proper PID 1 handling
RUN export DEBIAN_FRONTEND=noninteractive \
    && apt-get update \
    && apt-get install --no-install-recommends --yes \
        software-properties-common \
        python3.10 \
        python3-pip \
        python3.10-venv \
        libpython3.10-dev \
        git \
        nano \
        curl \
        tini \
    && apt-get clean \
    && apt-get autoremove \
    && rm -rf /var/lib/apt/lists/*

RUN cd /opt/matlab/R2024b/extern/engines/python && python setup.py install

# Pin setuptools < 70 in the system python to avoid the grapheme package
# compatibility issue (computor deps import it at runtime).
RUN python3.10 -m pip install --upgrade pip "setuptools>=65.0,<70" wheel packaging

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
