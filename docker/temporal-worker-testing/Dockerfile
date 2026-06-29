# Testing temporal worker = heavy language runtimes (computor-testing-runtimes)
# + the computor python project env (copied from computor-base) + computor-testing.
#
# The runtimes (Octave/R/C/Fortran/Python 3.13/Julia) live in their own image so
# editing project source no longer recompiles them. We build FROM the runtimes
# and COPY the (small, fast-changing) computor env on top — both are python:3.10-slim
# based, so the CPython-3.10 env is ABI-compatible.
# See docker/testing-runtimes/Dockerfile and docker/base/Dockerfile.
FROM computor-base:latest AS pybase

FROM computor-testing-runtimes:latest

# Bring in the computor python project env from the shared base. Same /home/worker
# path + CPython 3.10, so the editable installs + their deps resolve.
COPY --from=pybase --chown=worker:worker /home/worker/.local           /home/worker/.local
COPY --from=pybase --chown=worker:worker /home/worker/computor-types    /home/worker/computor-types
COPY --from=pybase --chown=worker:worker /home/worker/computor-utils    /home/worker/computor-utils
COPY --from=pybase --chown=worker:worker /home/worker/computor-client   /home/worker/computor-client
COPY --from=pybase --chown=worker:worker /home/worker/computor-backend  /home/worker/computor-backend

USER worker
WORKDIR /home/worker
# Re-declare the env the base set (we FROM the runtimes image, not computor-base).
ENV PATH=/home/worker/.local/bin:$PATH
ENV PYTHONPATH=/home/worker/computor-backend/src

# computor-testing framework (not part of the shared base)
ADD --chown=worker:worker computor-testing /home/worker/computor-testing
RUN pip install --user --no-warn-script-location /home/worker/computor-testing

# R user library
ENV R_LIBS_USER=/home/worker/.local/lib/R/library
RUN mkdir -p /home/worker/.local/lib/R/library

# Pre-build the Python 3.13 test venv with base testing deps at build time
# (avoids slow installs at container startup).
RUN python3.13 -m venv /home/worker/test-venv && \
    /home/worker/test-venv/bin/pip install --upgrade pip && \
    /home/worker/test-venv/bin/pip install -r /home/worker/computor-testing/requirements.txt
ENV PYTHON_TEST_EXECUTABLE=/home/worker/test-venv/bin/python

# Testing worker startup script: sets up language envs, then starts the worker.
COPY docker/temporal-worker-testing/testing-worker.py /home/worker/testing-worker.py
ENTRYPOINT ["python", "/home/worker/testing-worker.py"]
