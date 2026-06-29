# Coder temporal worker — runs the coder-tasks queue (workspace provisioning).
# Adds the Docker CLI (image builds via the Docker socket) and the coder CLI on
# top of the shared base. See docker/base/Dockerfile.
FROM computor-base:latest

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        docker.io \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://coder.com/install.sh | sh
USER worker

CMD ["python", "-m", "computor_backend.tasks.temporal_worker", "--queues=coder-tasks"]
