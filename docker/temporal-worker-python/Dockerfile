FROM python:3.10-slim

RUN apt-get update && apt-get install -y postgresql-client git

RUN useradd -ms /bin/bash worker
WORKDIR /home/worker

# Copy computor-types, computor-utils and computor-backend as root
ADD computor-types /home/worker/computor-types
ADD computor-utils /home/worker/computor-utils
ADD computor-backend /home/worker/computor-backend

# Copy the python-worker.py script
COPY docker/temporal-worker-python/python-worker.py /home/worker/python-worker.py

# Change ownership
RUN chown -R worker:worker /home/worker

# Switch to worker user
USER worker

# Install local packages first (computor-types and computor-utils)
RUN pip install --user -e computor-types
RUN pip install --user -e computor-utils

# Install dependencies
RUN pip install --no-cache-dir --user --upgrade -r computor-backend/src/requirements.txt

# Add src to PYTHONPATH so imports work
ENV PYTHONPATH=/home/worker/computor-backend/src:$PYTHONPATH

ENTRYPOINT ["python", "/home/worker/python-worker.py"]
#ENTRYPOINT ["python", "-m", "computor_backend.tasks.temporal_worker"]