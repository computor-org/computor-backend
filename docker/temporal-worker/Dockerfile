# Core temporal worker — runs the system task queue (course/family creation,
# student-template deployment, ...). Used in BOTH dev and prod.
#
# All Python setup (packages + deps) comes from the shared base image; this only
# selects the queue. See docker/base/Dockerfile.
FROM computor-base:latest

CMD ["python", "-m", "computor_backend.tasks.temporal_worker", "--queues=computor-tasks"]
