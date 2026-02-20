FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    postgresql-client \
    git \
    tzdata \
    curl \
    # Docker CLI (for image building via Docker SDK which talks to Docker socket)
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Install coder CLI
RUN curl -fsSL https://coder.com/install.sh | sh

# Set timezone to UTC
ENV TZ=UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN useradd -ms /bin/bash worker
WORKDIR /home/worker

# Copy computor-types, computor-utils, computor-client and computor-backend as root, then change ownership
ADD computor-types /home/worker/computor-types
ADD computor-utils /home/worker/computor-utils
ADD computor-client /home/worker/computor-client
ADD computor-backend /home/worker/computor-backend

# Change ownership
RUN chown -R worker:worker /home/worker

# Switch to worker user
USER worker

# Install local packages first (needed by computor-backend)
RUN pip install --user -e computor-types
RUN pip install --user -e computor-utils
RUN pip install --user -e computor-client

# Install computor-backend in editable mode with all dependencies
RUN pip install --user -e computor-backend

# Add src to PYTHONPATH so imports work
ENV PYTHONPATH=/home/worker/computor-backend/src:$PYTHONPATH

# Default command - start temporal worker on coder-tasks queue
CMD ["python", "-m", "computor_backend.tasks.temporal_worker", "--queues=coder-tasks"]
