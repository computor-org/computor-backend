FROM python:3.10-slim

RUN apt-get update && apt-get install -y postgresql-client git

RUN useradd -ms /bin/bash worker
WORKDIR /home/worker

# Copy computor-types and src as root, then change ownership
ADD computor-types /home/worker/computor-types
ADD src /home/worker/src

# Change ownership
RUN chown -R worker:worker /home/worker

# Switch to worker user
USER worker

# Install computor-types first (local package)
RUN pip install --user -e computor-types

# Install dependencies
RUN pip install --no-cache-dir --user --upgrade -r src/requirements.txt

# The source code will be mounted as a volume for hot reload
# We'll add the source to PYTHONPATH instead of using editable install
WORKDIR /home/worker/src

# Add src to PYTHONPATH so imports work
ENV PYTHONPATH=/home/worker/src:$PYTHONPATH

# Default command - start temporal worker directly
CMD ["python", "-m", "computor_backend.tasks.temporal_worker", "--queues=computor-tasks"]