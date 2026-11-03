# Computor Testing Framework - Security

The testers run untrusted student code. This document describes how that code
is isolated and which settings control the isolation.

## Threat Model

A submission may try to read the reference solution or other submissions,
read secrets from the environment, reach the network or internal services,
exhaust CPU, memory, processes or disk, signal other processes, or plant files
(symlinks, FIFOs, huge files) that the harness later reads.

## Measures

Every student process is started by an executor in `ctexec/` and
`testers/executors/`, never with in-process `exec()` in the harness.

- **Clean environment** (`ctexec/environment.py`): a minimal environment with
  a fixed `PATH`, `HOME=/tmp` (R keeps the real `HOME`) and UTF-8 locale. Known
  secret variables are blocked; only language-specific variables such as
  `PYTHONPATH` or `R_LIBS_USER` pass through.
- **Resource limits** (`ctexec/resources.py`): rlimits on every student
  process, configurable through `COMPUTOR_JOB_CPU_SECONDS`,
  `COMPUTOR_JOB_MEMORY_BYTES`, `COMPUTOR_JOB_MAX_PROCESSES`,
  `COMPUTOR_JOB_MAX_FILE_SIZE` and `COMPUTOR_JOB_MAX_OPEN_FILES` (`0` disables
  a limit). Core dumps are always off. Output is capped by
  `COMPUTOR_JOB_MAX_OUTPUT_BYTES`, math-library threads by
  `COMPUTOR_JOB_THREADS` (default 1).
- **Process-tree teardown** (`ctexec/process.py`): each job runs in its own
  process group and the whole tree is killed at the end or on timeout.
- **Kernel sandbox** (`sandbox/launch.py`): with `COMPUTOR_SANDBOX_ENABLE=1`
  every student process runs under Landlock with a file-path allow-list (the
  working directory and a private temporary directory are writable, the
  reference and example cache are not readable) and with all outbound TCP
  denied. A small seccomp filter refuses UDP, raw and packet sockets and
  io_uring. With Landlock ABI 6 the job is also scoped, so it cannot signal or
  reach abstract UNIX sockets outside itself. The testing worker requires
  ABI 6 and fails closed on older kernels. `python sandbox/launch.py --probe`
  reports what the running kernel supports.
- **Safe reads** (`ctexec/safe_io.py`): files a job could have written, such
  as result JSON and submitted sources, are read without following symlinks,
  only as regular files and up to a size cap (`COMPUTOR_JOB_MAX_RESULT_BYTES`,
  `COMPUTOR_JOB_MAX_REPORT_BYTES`).
- **Path validation** (`ctcore/security.py`): paths from `test.yaml` must stay
  inside the test root.
- **Bounded regular expressions**: patterns from `test.yaml` run with a
  timeout, so a pathological pattern cannot stall the harness.

Local runs by lecturers leave the kernel sandbox off; the rlimits always apply.

## Deployment

In production the testing worker sets `COMPUTOR_SANDBOX_ENABLE=1` and the
`COMPUTOR_JOB_*` limits, runs as a dedicated non-root UID with no
capabilities and `no-new-privileges`, and has container memory, CPU and PID
limits that bound all concurrent jobs together
(`ops/docker/docker-compose.prod.yaml`). Because `RLIMIT_NPROC` counts per
UID, the container's PID limit is the effective fork-bomb ceiling.

`Dockerfile.sandbox` builds a standalone non-root image for running a tester
in a locked-down container; its header lists the recommended `docker run`
options.

## Tests

The isolation is covered by `tests/test_job_isolation.py`,
`tests/test_sandbox_launch.py` and `tests/test_env_filter.py`. Cases that need
the kernel sandbox skip themselves when Landlock ABI 6 is not available.
