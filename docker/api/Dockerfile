# FastAPI backend (server.py). Runs as a container in prod (in dev the API runs
# on the host). Adds the migration + startup scripts on top of the shared base;
# the compose `command` runs startup.bash. See docker/base/Dockerfile.
FROM computor-base:latest

ADD --chown=worker:worker migrations.sh /home/worker/migrations.sh
ADD --chown=worker:worker docker/api/startup.bash /home/worker/startup.bash
