FROM python:3.10-slim

RUN apt-get update && apt-get install -y postgresql-client git

RUN useradd -ms /bin/bash uvicorn
WORKDIR /home/uvicorn

# Copy source code and installation files as root, then change ownership
ADD computor-types /home/uvicorn/computor-types
ADD computor-backend /home/uvicorn/computor-backend
ADD migrations.sh /home/uvicorn/migrations.sh
ADD docker/api/startup.bash startup.bash

# Change ownership of files to uvicorn user
RUN chown -R uvicorn:uvicorn /home/uvicorn

# Switch to uvicorn user
USER uvicorn

# Set PATH to include local pip install directory
ENV PATH="/home/uvicorn/.local/bin:${PATH}"

# Install computor-types first (local package)
RUN pip install --user -e computor-types

# Install dependencies
RUN pip install --user -r computor-backend/src/requirements.txt

# Install the backend package in editable mode
RUN cd computor-backend/src && pip install --user -e .