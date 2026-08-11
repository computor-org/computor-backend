---
name: computor-testing
description: The Computor testing framework — the computor-testing package (ctcore/ctexec/testers/blocks/sandbox), test.yaml and meta.yaml authoring, per-language runners and testing worker images. Use when adding or debugging a language runner or test type, writing/validating an assignment's test.yaml or meta.yaml, or working on how a student submission is actually executed and graded.
---

# Computor testing framework

You own `computor-fullstack/computor-testing` — the pytest-based framework that
executes student submissions in Python, Octave/MATLAB, R, Julia, C/C++, Fortran
and plain documents, plus the per-language worker images that run it.

**Read first:** `computor-testing/docs/DEVELOPER_GUIDE.md` — it has the module
map, the end-to-end execution flow, and a step-by-step "Adding a New Language"
(executor → registry → runtime info → runner → test infrastructure → CLI). Six
steps, all required; skipping the registry step fails at runtime, not import.
`computor-testing/docs/USER_GUIDE.md` is the assignment-author view.

## Module map

| Module | Owns |
|---|---|
| `ctcore/` | shared models, path security, stdio capture, helpers |
| `ctexec/` | execution: `interpreted.py`, `compiled.py`, runtime + resource limits |
| `testers/` | per-language runners, executors, the `computor-test` CLI |
| `blocks/` | pydantic definitions of test-case blocks per language; exports JSON Schema + TS for the VS Code extension |
| `sandbox/` | sandboxed execution backends and their security config |
| `dependencies/` | `dependencies.yaml` installer for example-level deps |

CLI: `computor-test <language> run`, plus per-language aliases (`pytester`,
`octester`, `rtester`, `ctester`, `ftester`, `jltester`, `doctester`).

## The two files an assignment carries

- **`meta.yaml`** — identity and metadata: `identifier`, `version`, `title`,
  authors, license, `content.*` tags, and `properties.studentSubmissionFiles`.
  It also carries the `executionBackend` that decides *which worker* runs it.
- **`test.yaml`** — the test plan: `type` (language), `properties.timeout`, and a
  list of typed test groups (`exist`, `variable`, `stdout`, `exitcode`,
  `compile`, `graphics`, `structural`, `wordcount`, `section`, …), each with its
  own `tests:` entries.

Properties **inherit** down the test.yaml tree — a value set at the top applies
to every group that does not override it. That is deliberate; read the
"Property Inheritance" section before changing how a property resolves.

Both files have generated JSON schemas (`bash generate.sh schemas` from the
monorepo root). If you add a field to either, the schema and the `blocks`
definitions must move with it, or the extension's editors go stale.

## Routing: which worker runs a submission

- A testing worker's task queue is derived from the service's `config.language`
  as `testing-<language>`; an explicitly configured queue wins.
- Examples bind to a runner **by language**. The service `slug` is a strict
  *optional pin*, not the selector — do not reintroduce slug-based dispatch.
- `config.language_version` narrows routing further when several versions coexist.
- A worker **refuses to start when its image cannot provide the language it
  claims**. That guard is intentional; fix the image, never downgrade it to a
  warning.

Adding a language end to end touches five places that nothing cross-checks: a
token in `.env`, a service in a deployment file, a container in compose, the
runtime inside the image, and `executionBackend` in every example's `meta.yaml`.
**Use `scripts/add-testing-language.sh <language>`** — it does the first two and
prints the compose block for the third. MATLAB is deliberately excluded: it is a
separate image with its own entrypoint (`docker/temporal-worker-matlab`).

Images live in `docker/testing-runtimes` (shared multi-language) and
`docker/temporal-worker-testing`.

## Execution and security

Student code is hostile input. Execution is subprocess-isolated with resource
limits (`ctexec/resources.py`) and a scrubbed environment; path handling in
`ctcore/security.py` validates against directory traversal. When adding a test
type that reads a student-supplied path or filename, route it through that
validation rather than `open()`. `SECURITY.md` states the threat model.

## Performance notes that cost real time

- MATLAB: `clear all` per submission dominated runtime (2.77s → 0.61s without
  it). Reuse the session; do not reintroduce a full clear as "safety".
- MATLAB `getframe` is ~110ms per frame — movie-producing examples are slow by
  construction, not broken.
- MATLAB runs **one submission at a time** on purpose, so a worker restart cannot
  kill a live test.

## Verifying

Never ship a runner change unrun. Execute a real example from
`computor-testing/examples/` (there are working examples for every supported
language) with the matching CLI, and check the produced report, not just the exit
code. `scripts/integration_test.sh` covers the cross-language path.

For the Temporal workflows that *call* this framework
(`temporal_student_testing.py`, `temporal_tutor_testing.py`), and for queue or
worker-lifecycle questions, hand off to `computor-backend-tasks`.
