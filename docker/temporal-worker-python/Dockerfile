FROM python:3.10-slim

RUN apt-get update && apt-get install -y postgresql-client git

RUN useradd -ms /bin/bash worker
WORKDIR /home/worker

# Switch to worker user early
USER worker

ADD src /home/worker/

RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the python-worker.py script
COPY docker/temporal-worker-python/python-worker.py /home/worker/python-worker.py

ENTRYPOINT ["python", "/home/worker/python-worker.py"]
#ENTRYPOINT ["python", "-m", "computor_backend.tasks.temporal_worker"]