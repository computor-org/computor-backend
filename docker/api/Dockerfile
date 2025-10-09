FROM python:3.10-slim

RUN apt-get update && apt-get install -y postgresql-client git

RUN useradd -ms /bin/bash uvicorn
WORKDIR /home/uvicorn

# Copy source code and installation files as root, then change ownership
ADD computor-types /home/uvicorn/computor-types
ADD computor-utils /home/uvicorn/computor-utils
ADD computor-client /home/uvicorn/computor-client
ADD computor-backend /home/uvicorn/computor-backend
ADD migrations.sh /home/uvicorn/migrations.sh
ADD docker/api/startup.bash startup.bash

# Change ownership of files to uvicorn user
RUN chown -R uvicorn:uvicorn /home/uvicorn

# Switch to uvicorn user
USER uvicorn

# Set PATH to include local pip install directory
ENV PATH="/home/uvicorn/.local/bin:${PATH}"

# Install local packages first (needed by computor-backend)
RUN pip install --user -e computor-types
RUN pip install --user -e computor-utils
RUN pip install --user -e computor-client

# Install computor-backend (installs all dependencies from pyproject.toml)
RUN pip install --user -e computor-backend