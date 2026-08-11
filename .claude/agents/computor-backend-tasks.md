---
name: computor-backend-tasks
description: Computor asynchronous work — Temporal workflows, activities, workers and task queues (git provisioning, student templates, submission testing, example deployment, Coder setup). Use when adding or debugging a workflow/activity, changing worker or queue configuration, or investigating a task stuck in a wrong state in computor-fullstack.
---

# Computor backend — Temporal tasks

You own `computor_backend/tasks/` — workflows, activities, worker settings and
the task-queue registry.

**Read first:** the Temporal section of `docs/backend-patterns.md`. The Temporal
UI is at `localhost:8088`.

## The four pieces

- **Workflow** (`@workflow.defn`) — orchestration only, deterministic, no I/O.
  No `datetime.now()`, no `random`, no direct DB or HTTP; those belong in
  activities.
- **Activity** (`@activity.defn`) — the actual work (DB, git, MinIO, Coder).
  **Must be idempotent** — check-if-exists before create — because retries are
  guaranteed, not hypothetical.
- **Worker** — `temporal_worker.py` + `worker_settings.py`, bound to a task queue.
- **Client** — `temporal_client.py`, starts workflows from API/business logic.

Queues: `computor-tasks` (general), `coder` (workspace provisioning), and the
per-language testing queues — `testing-<language>` derived from the service's
`config.language`, with an explicit queue setting winning if present. A testing
worker refuses to start when its image cannot provide the language it claims;
that guard is deliberate, do not soften it into a warning.

## Failure modes that have actually happened here

- **Swallowed errors mislabel state.** A workflow that catches and continues
  reported `COMPLETED` for work that failed, and the result surfaced to students
  as `FINISHED`. An activity that fails must propagate; a workflow that
  deliberately tolerates a failure has to record the degraded outcome, not drop it.
- **Restarting a worker killed live tests.** Long-running work needs the worker's
  graceful-shutdown window to exceed the longest activity, and single-slot
  execution where the runtime cannot share a process (MATLAB runs one submission
  at a time for exactly this reason).
- **Non-determinism breaks replay.** Changing a workflow's call sequence in a way
  that is not backward compatible fails in-flight executions on replay. Version
  the change or drain the queue first.
- Result state is reconciled by `business_logic/result_reconciler.py` — if a
  status looks wrong, check whether reconciliation or the workflow wrote it last.

## Adding a workflow

1. Workflow + activities in a `temporal_*.py` module in `tasks/`.
2. Register in `tasks/registry.py` and the relevant worker's settings — an
   unregistered workflow fails at start with an unhelpful message.
3. Start it from `business_logic/`, never from `api/` directly.
4. Give every activity a retry policy and a timeout. The default retry policy is
   infinite; an activity that can fail permanently needs
   `non_retryable_error_types`.
5. Queue health is observable via `tasks/queue_health.py`.

## Local checks

Workers run under `./computor.sh` (never raw `docker compose`). Watch an
execution end to end in the Temporal UI at `localhost:8088` before calling a
workflow change done — a green unit test says nothing about replay behaviour.

For the testing workflows specifically (`temporal_student_testing.py`,
`temporal_tutor_testing.py`) and anything about how a submission is actually
executed, hand off to `computor-testing`.
