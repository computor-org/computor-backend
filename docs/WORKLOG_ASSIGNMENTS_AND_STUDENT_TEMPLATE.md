# Assignments Init + Student-Template Release — Refactor Summary

This worklog captures the code and behavior changes made to separate
“assignments” initialization from the “student-template” release, make
student-template strictly sourced from the assignments repository, and
improve content deployment defaults (title/description/path) from Example metadata.

## Overview
- Split responsibilities into two Temporal activities/workflows:
  - Assignments repository initialization (populate from Example Library).
  - Student-template release (read-only from assignments at a specific commit).
- Student-template release is strict: no MinIO fallback; requires files
  from assignments at the resolved commit and path.
- Deployment metadata and CLI improved to derive sensible defaults
  (title/description/path) from ExampleVersion meta and Example.

## New and Updated Tasks
- New module: `src/ctutor_backend/tasks/temporal_assignments_repository.py`
  - Activity: `generate_assignments_repository`
  - Workflow: `GenerateAssignmentsRepositoryWorkflow` (sandboxed=False)
  - Behavior:
    - Clones/initializes the assignments repo (deriving URL from course if needed).
    - For selected contents with an assigned ExampleVersion, downloads full Example
      (from Example Library) and writes it to `deployment_path` (or sets from example.identifier).
    - Single commit + push; writes `deployment.version_identifier = HEAD SHA` and
      creates a history entry per content.
- Student-template workflow refactor: `src/ctutor_backend/tasks/temporal_student_template_v2.py`
  - Strictly reads from assignments repo at per-content commit under `deployment_path`.
  - No MinIO fallback; marks deployment failed if commit/path is missing or empty.
  - Derives `deployment_path` from `ExampleVersion.example.identifier` when missing.
  - Handles null/absent `release.overrides` safely.
  - Transforms `assignments_url` for Docker networking.

## Worker Registration and Sandbox
- `src/ctutor_backend/tasks/temporal_worker.py`
  - Registers the new assignments workflow + activity.
- `src/ctutor_backend/tasks/__init__.py`
  - Imports `temporal_assignments_repository` so API task registry knows the workflow name.
- Pydantic/Temporal sandbox fix:
  - `src/ctutor_backend/interface/base.py`: `BaseEntityList` now allows `arbitrary_types_allowed=True`.
  - Assignments workflow runs with `sandboxed=False` to avoid datetime access restrictions.

## API Additions and Changes
- New endpoint: `POST /system/courses/{course_id}/generate-assignments`
  - File: `src/ctutor_backend/api/system.py`
  - Request model: `GenerateAssignmentsRequest`
    - `assignments_url`, selection (`course_content_ids` | `parent_id+include_descendants` | `all`),
      `overwrite_strategy` (skip_if_exists|force_update), `commit_message`.
  - Response model: `GenerateAssignmentsResponse` with `workflow_id`.
- `POST /system/courses/{course_id}/generate-student-template`
  - Unchanged contract; now strictly reads from assignments and supports a `release` selection
    with `global_commit` and per-item `overrides`.
- `GET /examples/{example_id}/versions` now accepts filters:
  - Added `ExampleVersionQuery(version_tag)` in `src/ctutor_backend/interface/example.py`.
  - Endpoint updated to `params: ExampleVersionQuery = Depends()` in `src/ctutor_backend/api/examples.py`.

## Models and Migration Tweaks
- `CourseContentDeployment.version_identifier`: nullable (no commit at initial assignment).
- `Result.reference_version_identifier`: added, nullable; set by tests when available.
- These are reflected in the initial alembic migration and corresponding models.

## CLI Deployment Improvements
- File: `src/ctutor_backend/cli/deployment.py`
  - Student-template generation now waits for completion before user repo creation
    to avoid race conditions.
  - Assignments init is called before student-template release when using
    `--generate-student-template`.
  - Versions retrieval now uses `custom_client.list("examples/{id}/versions", params={...})`
    with server-side filtering by `version_tag`, and fetches the full version via
    `GET /examples/versions/{version_id}` to access `meta_yaml`.

### CourseContent defaults (title/description/path)
- Path precedence:
  - If deployment provides `path`, it is used as-is (prefixed by parent path when nested).
  - If `path` is omitted, a slugified segment is generated from the best title source
    (deployment title → meta_yaml.title → example.title → example_identifier), and
    uniqueness is ensured by appending `_2`, `_3`, ... as needed.
- Title default:
  - `deployment.title` → `ExampleVersion.meta_yaml.title` → `Example.title` → last path segment.
- Description default:
  - Only `deployment.description` or `ExampleVersion.meta_yaml.description` is used
    (no automatic fallback to `Example.description`).
- When content already exists:
  - Description is updated only if a manual description is provided, or if description
    is empty and meta_yaml.description exists (no overwrite otherwise).

## Student-Template Release Strictness
- Files are read only from assignments repo at `deployment.version_identifier` (or override/global commit), under `deployment.deployment_path`.
- If commit cannot be resolved or no files are found at that commit/path, the deployment is marked `failed` with a clear reason.
- `deployment.deployment_path` is derived from Example.identifier when missing.

## Docker Host URL Transform
- `transform_localhost_url` is used for both student-template and assignments URLs
  to convert `localhost` to the Docker host IP when running inside containers.

## How to Use (CLI)
1. Deploy hierarchy and contents from deployment.yaml:
   - `python src/cli.py deployment apply deployment.yaml --generate-student-template`
   - This creates the hierarchy, creates contents with sensible defaults, 
     initializes the assignments repo from the Example Library, and finally
     releases the student-template (waiting for completion).
2. For API-driven releases later:
   - `POST /system/courses/{id}/generate-assignments` to update assignments
   - `POST /system/courses/{id}/generate-student-template` with a release payload
     to select what to publish and the commits to use.

## Notes and Future Follow-Ups
- Title defaults currently consider Example.title as secondary to version meta.
  If you want title strictly from version meta only, we can align it (like description).
- We can add a validation tool to detect contents assigned to examples but missing
  in assignments at the selected commit, to help lecturers correct the repo before release.

