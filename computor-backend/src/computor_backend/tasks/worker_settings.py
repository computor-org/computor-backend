"""Centralized configuration for the Temporal worker / task layer.

Historically every task-layer activity, the Temporal client, and the testing
backends read their configuration through scattered ``os.environ.get(...)``
calls (with ``"http://localhost:8000"`` hardcoded roughly a dozen times as a
default). This module gathers those reads into a single pydantic
``BaseSettings`` class so there is exactly one place documenting every worker
env var, its precise name, and its precise default.

This is pure config plumbing -- behavior is intentionally identical to the old
``os.environ.get`` calls:

* Each field binds to the SAME env var name the old code used (via
  ``validation_alias``) and carries the SAME default value.
* ``case_sensitive=True`` and NO ``env_file`` -- values come ONLY from the
  process environment, exactly like ``os.environ.get``. (The repo ``.env`` is
  loaded into the environment by the launcher/compose, not read here; reading a
  ``.env`` directly would diverge from the old behavior.)
* ``get_worker_settings()`` is cached but the cache is clearable, so tests that
  mutate the environment can force a re-read via
  ``get_worker_settings.cache_clear()``.

A few legacy call sites do not have a plain static default:

* ``API_URL`` / ``CODER_REGISTRY_HOST`` / ``CODER_URL`` were read as
  ``os.environ.get("X", <runtime value>)`` -- the env var OVERRIDES a
  workflow-passed value. Those are modeled as ``Optional[...] = None`` (except
  ``api_url``; see below) so the call site keeps its own fallback and the
  "was the env var actually set?" distinction survives (``None`` == unset,
  ``""`` == set-but-empty, matching ``os.environ.get``).
* ``TESTING_EXECUTABLE`` falls back to DIFFERENT literals at its two call sites,
  so it is ``Optional`` too and each site keeps its own literal.
* ``API_TOKEN`` had no default (``os.environ.get("API_TOKEN") or ...``), so it
  is ``Optional`` and the call site keeps the ``or`` fallback.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    """Every environment variable read by the task / testing / worker layer."""

    model_config = SettingsConfigDict(case_sensitive=True, extra="ignore")

    # --- API client (tasks/api_client.py) ---------------------------------
    # Old: os.environ.get("API_URL", api_config.get("url", "http://localhost:8000"))
    # The env var overrides the workflow-passed url. The field default is the
    # static fallback; resolve_api_config() inspects model_fields_set to honor
    # the env > api_config > default precedence exactly.
    api_url: str = Field(default="http://localhost:8000", validation_alias="API_URL")
    # Old: os.environ.get("API_TOKEN") or api_config.get("token")  (no default)
    api_token: Optional[str] = Field(default=None, validation_alias="API_TOKEN")

    # --- git worker identity (tasks/git_ops.py) ---------------------------
    system_git_email: str = Field(
        default="worker@computor.local", validation_alias="SYSTEM_GIT_EMAIL"
    )
    system_git_name: str = Field(
        default="Computor Worker", validation_alias="SYSTEM_GIT_NAME"
    )

    # --- example cache (tasks/temporal_student_testing.py) ----------------
    example_cache_dir: str = Field(
        default="/tmp/examples", validation_alias="EXAMPLE_CACHE_DIR"
    )

    # --- Temporal client (tasks/temporal_client.py) -----------------------
    temporal_host: str = Field(default="localhost", validation_alias="TEMPORAL_HOST")
    temporal_port: int = Field(default=7233, validation_alias="TEMPORAL_PORT")
    temporal_namespace: str = Field(
        default="default", validation_alias="TEMPORAL_NAMESPACE"
    )
    temporal_tls_cert: Optional[str] = Field(
        default=None, validation_alias="TEMPORAL_TLS_CERT"
    )
    temporal_tls_key: Optional[str] = Field(
        default=None, validation_alias="TEMPORAL_TLS_KEY"
    )
    temporal_tls_ca: Optional[str] = Field(
        default=None, validation_alias="TEMPORAL_TLS_CA"
    )
    # TLS name to verify the frontend certificate against when it differs from
    # TEMPORAL_HOST (for example when connecting by IP over WireGuard).
    temporal_tls_server_name: Optional[str] = Field(
        default=None, validation_alias="TEMPORAL_TLS_SERVER_NAME"
    )
    # Bearer token (a JWT) for a frontend that runs Temporal's JWT claim mapper
    # and authorizer. Sent as the ``authorization`` gRPC header on every call.
    temporal_api_key: Optional[str] = Field(
        default=None, validation_alias="TEMPORAL_API_KEY"
    )

    # Execution namespaces. Comma-separated ``<queue pattern>=<namespace>``
    # pairs (fnmatch patterns), e.g.
    # ``coder-tasks=computor-coder,testing*=computor-grading``. Workflows on a
    # matching queue are started, polled and looked up in that namespace, all
    # other queues stay in TEMPORAL_NAMESPACE. With a JWT authorizer on the
    # frontend, each execution worker then holds a token for its own namespace
    # only and cannot reach the control workflows. Unset or empty means a single
    # namespace, exactly as before.
    temporal_queue_namespaces: Optional[str] = Field(
        default=None, validation_alias="TEMPORAL_QUEUE_NAMESPACES"
    )

    # --- Temporal worker activity thread pool (tasks/temporal_worker.py) ---
    # Blocking activities (GitPython clone/push, sync SQLAlchemy, sync
    # python-gitlab, docker image build, subprocess test execution) are plain
    # ``def`` activities that Temporal runs in a ThreadPoolExecutor instead of on
    # the worker's asyncio event loop, so a multi-minute clone/build no longer
    # stalls heartbeats or starves other activities. ``max_workers`` is sized
    # from this field. The default 100 matches the SDK's
    # ``max_concurrent_activities`` default so the executor is never smaller than
    # it (the SDK warns otherwise) and activity concurrency is unchanged.
    activity_executor_max_workers: int = Field(
        default=100, validation_alias="TEMPORAL_ACTIVITY_EXECUTOR_MAX_WORKERS"
    )

    # --- Coder template routing ------------------------------------------
    # On a split-host deployment, workspace-ingress must call ForwardAuth on
    # the control plane over WireGuard; the API-side default (uvicorn:8000) is
    # only resolvable on the control-plane Docker network.
    backend_external_url: Optional[str] = Field(
        default=None, validation_alias="BACKEND_EXTERNAL_URL"
    )

    # Cap on activities a worker runs at once. Unset means the SDK default of
    # 100, which is right for workers whose activities are independent. It is
    # wrong for a queue that fronts a single non-reentrant resource: the MATLAB
    # worker drives one shared MATLAB engine over Pyro, and MATLAB executes one
    # command at a time, so pulling 100 test activities only builds a queue
    # inside the engine while each activity's own timeout counts down against
    # the wait rather than the work. Set it to 1 there and scale that worker
    # with replicas (MATLAB_TESTING_WORKER_REPLICAS), each with its own engine.
    max_concurrent_activities: Optional[int] = Field(
        default=None, validation_alias="TEMPORAL_MAX_CONCURRENT_ACTIVITIES"
    )

    # How long a shutting-down worker waits for its in-flight activities before
    # cancelling them. The SDK default is 0 — a plain `docker compose restart`
    # cancelled a running student test instantly, and since test activities are
    # never retried that lost the run. A test executes for minutes, so give it
    # real time to land; the container's stop_grace_period must be at least
    # this large or Docker SIGKILLs the worker before the wait can finish.
    graceful_shutdown_seconds: int = Field(
        default=300, validation_alias="TEMPORAL_GRACEFUL_SHUTDOWN_SECONDS"
    )

    # --- Coder image / template build (tasks/temporal_coder_setup.py) -----
    # Old: os.environ.get("CODER_REGISTRY_HOST", registry_host)  -- env overrides
    #      a runtime parameter, so None == unset and the call site keeps the param.
    coder_registry_host: Optional[str] = Field(
        default=None, validation_alias="CODER_REGISTRY_HOST"
    )
    # Old: os.environ.get("CODER_URL", coder_url)  -- same override-a-param shape.
    coder_url: Optional[str] = Field(default=None, validation_alias="CODER_URL")
    docker_socket_path: str = Field(
        default="/var/run/docker.sock", validation_alias="DOCKER_SOCKET_PATH"
    )
    # Docker endpoint, e.g. tcp://coder-worker-socket-proxy:2375. Takes
    # precedence over docker_socket_path, which stays the fallback for dev
    # setups that still mount the socket.
    docker_host: Optional[str] = Field(default=None, validation_alias="DOCKER_HOST")
    # Spool shared with the host-side computor-coder-hostops units (registry
    # GC, volume-ownership repair): the operations that need a container or
    # exec, which the worker's Docker proxy refuses. See ops/coder/hostops.
    hostops_dir: str = Field(default="/hostops", validation_alias="COMPUTOR_HOSTOPS_DIR")
    # The host's cgroup2 tree, bind-mounted read-only, from which the workspace
    # slice limits are read.
    host_cgroup_root: str = Field(
        default="/host/sys/fs/cgroup", validation_alias="COMPUTOR_HOST_CGROUP_ROOT"
    )

    # --- testing backends (testing/backends.py) ---------------------------
    # ComputorTestingBackend falls back to the literal "computor-test" when
    # this is unset, so it is Optional; None == unset.
    testing_executable: Optional[str] = Field(
        default=None, validation_alias="TESTING_EXECUTABLE"
    )
    runtime_environment: str = Field(
        default="python3", validation_alias="RUNTIME_ENVIRONMENT"
    )
    # Truthiness flag: old code did `if os.environ.get("RUNNING_IN_DOCKER"):`.
    running_in_docker: Optional[str] = Field(
        default=None, validation_alias="RUNNING_IN_DOCKER"
    )


@lru_cache(maxsize=1)
def get_worker_settings() -> WorkerSettings:
    """Return the process-wide worker settings, read lazily from the environment.

    Cached so repeated reads inside activities are cheap. The cache can be
    cleared with ``get_worker_settings.cache_clear()`` (e.g. in tests that set
    env vars after this has already been called).
    """
    return WorkerSettings()
