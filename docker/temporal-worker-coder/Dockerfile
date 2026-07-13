# Coder temporal worker — runs the coder-tasks queue (workspace provisioning,
# image building, template pushing).
#
# The Docker CLI + coder CLI live in their own image (computor-coder-runtime) so
# editing project source no longer re-runs that apt/curl install. We build FROM
# the runtime and COPY the (small, fast-changing) computor env on top — both are
# python:3.10-slim based, so the CPython-3.10 env is ABI-compatible. This mirrors
# the testing/matlab workers; see docker/coder-runtime/Dockerfile and
# docker/base/Dockerfile.
FROM computor-base:latest AS pybase

FROM computor-coder-runtime:latest

# Bring in the computor python project env from the shared base. Same /home/worker
# path + CPython 3.10, so the editable installs + their deps resolve.
COPY --from=pybase --chown=worker:worker /home/worker/.local           /home/worker/.local
COPY --from=pybase --chown=worker:worker /home/worker/computor-types    /home/worker/computor-types
COPY --from=pybase --chown=worker:worker /home/worker/computor-client   /home/worker/computor-client
COPY --from=pybase --chown=worker:worker /home/worker/computor-backend  /home/worker/computor-backend

USER worker
WORKDIR /home/worker
# Re-declare the env the base set (we FROM the runtimes image, not computor-base).
ENV PATH=/home/worker/.local/bin:$PATH
ENV PYTHONPATH=/home/worker/computor-backend/src

CMD ["python", "-m", "computor_backend.tasks.temporal_worker", "--queues=coder-tasks"]
