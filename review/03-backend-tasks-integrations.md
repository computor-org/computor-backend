# Refactoring Plan: Backend Tasks & Integrations

**Scope:** `computor-backend/src/computor_backend/` — `tasks/`, `coder/`, `git_provider/`, `git_server/`, `generator/`, `plugins/`, `testing/`, `gitlab_utils.py`, `task_tracker.py`, `maintenance_scheduler.py`
**Reviewed:** 2026-07-07 (branch `release/2026.10`)
**Total LOC in scope:** ~12,600

## Architecture context (read first)

- `tasks/` holds Temporal workflows + activities, one module per domain. Each module exports `WORKFLOWS`/`ACTIVITIES` lists and self-registers via `@register_task`. `temporal_worker.py` re-lists all modules; `temporal_executor.py` wraps the Temporal client; `task_tracker.py` mirrors submissions into Redis for permission-aware listing.
- Git integration exists in **three generations**:
  1. Legacy raw helpers `gitlab_utils.py` + org-properties-token flows (`temporal_student_repository.py`, `temporal_assignments_repository.py`)
  2. `generator/gitlab_builder.py` (org/family/course hierarchy provisioning)
  3. New `git_provider/` Protocol (`GitLabProviderClient`, `ForgejoProviderClient`) driven by the `CourseGitBinding`/GitServer-registry model. `temporal_student_template_v2.py` straddles generations 1 and 3.
- `coder/` is a self-contained async httpx client + pydantic settings; `tasks/temporal_coder_setup.py` partially bypasses it. `testing/backends.py` is a clean factory. `plugins/` is auth-plugin infra (current). `analytics/` is dead (stale `__pycache__` only). `websocket/event_publisher.py` is the sync-Redis bridge that activities call.

**Key metrics:** largest files: `coder/client.py` 1432 LOC, `tasks/temporal_student_template_v2.py` 1420, `generator/gitlab_builder.py` 960, `tasks/temporal_student_repository.py` 902, `tasks/temporal_student_testing.py` 856, `tasks/temporal_coder_setup.py` 664. 104 broad `except Exception` in scope; 6 hand-rolled retry/poll loops; `print()` in prod code at `gitlab_utils.py:7,10,23` and `tasks/temporal_executor.py:398`.

---

## TASK-301: Unify the three GitLab integration layers (token/fork/member logic)

- **Category:** layering / duplication — **Priority: P1** — **Effort: L**
- **Files:** `gitlab_utils.py` (134 LOC), `generator/gitlab_builder.py` (960), `git_provider/gitlab.py` (273), `tasks/temporal_student_repository.py:200-227,646-668`, `tasks/temporal_student_template_v2.py:575-612`, `tasks/temporal_assignments_repository.py:60-75`, `business_logic/course_git.py:64-85,383-384`

**Problem:** The same primitives are implemented 2–3 times across generations. Fork-with-poll exists twice (`fork_project_with_polling` async/`asyncio.sleep` in `temporal_student_repository.py:29-90` vs `_poll_for_project` sync/`time.sleep` in `git_provider/gitlab.py:211-226`). Idempotent add-member exists twice (`add_members_to_project` `temporal_student_repository.py:93-197` vs `GitLabProviderClient.add_member` `git_provider/gitlab.py:255-273`). Push-token resolution (org `properties.gitlab.token` → `CourseGitBinding.token` → `git_server.token`, all via `decrypt_secret`) is copy-pasted in at least 3 places with subtly different fallback orders. `Gitlab(...)` clients are constructed at 4 independent sites with/without `keep_base_url` and `transform_localhost_url`.

**Steps:**
1. Create `git_provider/token_resolution.py` with one function `resolve_course_push_credentials(db, course_id) -> (token, server_type, public_base, reachable_base)` encapsulating the org-properties → binding → git_server chain currently inlined at `temporal_student_template_v2.py:575-612` and `course_git.py:75-85,383-384`; replace all three call sites. **Preserve each caller's fallback order behind explicit parameters** (template v2 prefers org token; course_git prefers binding).
2. Move `fork_project_with_polling` into `GitLabProviderClient` (single implementation; accept a sleep function or run sync in an activity thread); delete the `temporal_student_repository.py` copy; have `_poll_for_project` delegate to it.
3. Move `add_members_to_project`'s Account-lookup part into a small `git_provider/gitlab_members.py` that calls `GitLabProviderClient.add_member` for the API half; delete the 409-handling duplicate.
4. Add a single `make_gitlab_client(url, token)` factory (docker-aware, `keep_base_url=True`) in `git_provider/gitlab.py`; replace the 4 ad-hoc `Gitlab(...)` constructions.
5. Fold `gitlab_utils.gitlab_fork_project`/`gitlab_unprotect_branches` into `GitLabProviderClient` (replace `print` with `logger`); keep `construct_gitlab_*_url` as a pure-URL module or move to `computor_types`.

**Risks / verification:** Token-resolution fallback order differs per site — do not normalize silently. Test: template release on a legacy org-token course, a binding GitLab course, and a managed Forgejo course; student repo fork on an un-migrated course.

---

## TASK-302: Split god-activity `generate_student_template_activity_v2` (~890 lines)

- **Category:** god-file — **Priority: P1** — **Effort: L**
- **Files:** `tasks/temporal_student_template_v2.py:433-1321` (single function, one `with get_db_session()` + nested try spanning 840 lines; file total 1420)

**Problem:** One activity does deployment-status transitions + broadcasts, token resolution, repo clone/init, repo-state-mismatch scanning, per-content download/processing, legacy service-linking (meta.yaml parsing inline, lines 833-894), README generation (lines 1000-1061), push-with-retry, reference-repo mirroring, and final status/event fan-out. It is untestable except end-to-end, and error paths mutate deployment rows in four separate blocks.

**Steps:**
1. Create package `tasks/student_template/` with modules:
   - `selection.py` — `select_deployments(db, course_id, release, force_redeploy)` (from lines 483-558 + 674-750)
   - `status.py` — `mark_deploying/mark_deployed/mark_failed` + history + event collection (from lines 514-558, 1133-1246, 1270-1321)
   - `readme.py` — README generation (lines 1000-1061)
   - `service_link.py` — legacy testing-service fallback (lines 833-894)
   - `reference.py` — `_push_reference_repo` + `process_example_for_reference_v2`
2. Keep the activity as a ~100-line orchestrator calling these; each helper takes `db` and plain data, **no Temporal imports**.
3. Move the `publish_deployment_status_changed` fan-out into a single `broadcast_events(events)` helper (currently three near-identical loops at 546-556, 1234-1246, 1300-1312).
4. Unit-test `selection.py` and `status.py` against a fixture DB.

**Risks / verification:** Temporal activity name `generate_student_template_activity_v2` and its payload/signature must not change (history compatibility). The deploying→deployed/failed state machine has ordering subtleties (README uses "deploying" rows before commit) — write an integration test snapshotting behavior BEFORE splitting.

---

## TASK-303: Extract shared git plumbing (clone-or-init, identity, push-with-rebase-retry)

- **Category:** duplication — **Priority: P1** — **Effort: M**
- **Files:** `tasks/temporal_student_template_v2.py:370-379,412-426,617-648,1066-1112`; `tasks/temporal_assignments_repository.py:118-150,221-245`

**Problem:** Three sites hand-roll the identical sequence: authed-URL build → `Repo.clone_from` → fallback `Repo.init` + `checkout -b main` + `create_remote` → `git config user.email/name` from `SYSTEM_GIT_EMAIL/NAME` → `add(A=True)`/dirty-check/commit → push with a 3-attempt non-fast-forward pull-rebase loop (two variants) or a `-u` fallback (third variant, which does NOT handle non-fast-forward).

**Steps:**
1. Create `tasks/git_ops.py` with:
   - `clone_or_init(url, token, server_type, dest, branch="main") -> Repo`
   - `configure_identity(repo)` (reads env once)
   - `commit_and_push(repo, message, branch="main", max_attempts=3) -> bool` containing the rebase-retry loop
2. Replace the three inline blocks; give `temporal_assignments_repository.py` the same rebase-retry semantics (fixes its missing concurrent-push handling).
3. Reuse `make_provider_auth_url` from `temporal_base` inside `clone_or_init` so the Forgejo/GitLab auth difference lives in one place.

**Risks / verification:** assignments repo gains rebase-on-conflict behavior it didn't have — verify no force-push expectations. Test: two concurrent template releases (retry path), first-push-to-empty-repo path (`-u`/init path).

---

## TASK-304: Deduplicate legacy `temporal_student_repository.py` (two ~200-line near-clones)

- **Category:** duplication / dead-code — **Priority: P2** — **Effort: M**
- **Files:** `tasks/temporal_student_repository.py:423-613` (`create_student_repository`) vs `:616-816` (`create_team_repository`); marked LEGACY at `business_logic/course_member_post_create.py:195-211` (skipped whenever a `CourseGitBinding` exists)

**Problem:** `create_team_repository` re-inlines `get_gitlab_client` (646-668 duplicates 200-227), re-inlines the student-template path lookup incl. the same regex `r'/([^/]+/[^/]+/[^/]+/student-template)$'` (293-303 vs 682-691), and repeats fork/unprotect/add-members/URL-construction. Both build `repository_info` dicts with divergent shapes. This whole workflow only runs for un-migrated org-level GitLab courses.

**Steps:**
1. Extract shared module-level helpers: `_resolve_template_project(gitlab, course) -> project_id` (single copy of the path/regex fallback), `_fork_and_grant(gitlab, template_id, repo_path, repo_name, namespace_id, member_ids, db, provider_url) -> project` (fork+unprotect+members), `_build_repository_info(gitlab_url, project, namespace_id) -> dict` (one canonical shape).
2. Rewrite both activities as thin wrappers (~40 lines each) over these helpers.
3. Add a module docstring declaring the legacy scope and the retirement condition (all courses migrated to `CourseGitBinding`), so nobody extends it for Forgejo.

**Risks / verification:** `repository_info` dict shape is consumed from `course_member.properties['gitlab']` and `submission_group.properties` — keep both key sets (including the duplicated nested `gitlab` block in the team variant) byte-compatible. Test: member-join on an un-migrated course.

---

## TASK-305: `CoderClient` — collapse 20× token/client/status boilerplate; stop bypassing the client

- **Category:** duplication — **Priority: P2** — **Effort: M**
- **Files:** `coder/client.py` (boilerplate `token = await self._get_session_token(); client = await self._ensure_client()` at ~15 sites: lines 254-256, 344-346, 399-400, 454-455, 502-503, 527-528, 621-622, 656-657, 681-682, 739-741, 816-817, 895-896, 1062-1063, 1124-1125, 1146-1147); header inconsistency (`{"Coder-Session-Token": token}` vs `self._get_headers(token)` which adds `X-Admin-Secret`); `CoderUser(...)` hand-mapped 3× (265-272, 303-310, 379-386). `tasks/temporal_coder_setup.py:223-233,272-289` re-implements Coder login + template GET/PATCH with raw httpx.

**Steps:**
1. Add `async def _request(self, method, path, *, json=None, params=None, ok=(200,), admin_headers=False, timeout=None) -> httpx.Response` to `CoderClient` handling token fetch, header building, and raising `CoderAPIError` on unexpected status; convert each public method to 3-6 lines. Per-endpoint 409/404 special-casing survives via the `ok=` parameter.
2. Decide the `X-Admin-Secret` question once: use `_get_headers` everywhere (currently GETs omit it inconsistently).
3. Add `CoderUser.from_api(dict)` and use it in `get_user`, `_find_user_by_email`, `create_user`.
4. In `temporal_coder_setup.push_coder_template`, replace the raw login block with `CoderClient` (settings already support URL/credentials); add `get_template(name)` / `patch_template_ttl(id, ttl, bump)` methods to the client.

**Risks / verification:** Test: provision workspace, rollout workflow, template push (TTL patch), initial-admin bootstrap.

---

## TASK-306: `gitlab_builder.py` — merge copy-pasted group/config/property-update trios

- **Category:** duplication — **Priority: P2** — **Effort: M**
- **Files:** `generator/gitlab_builder.py` — `_create_students_group` (704-773) vs `_create_tutors_group` (775-844) identical except name/path/property-key; `_create_organization_gitlab_config` (598-615) vs `_create_child_gitlab_config` (617-632) differ only by the token line; `_update_organization/_course_family/_course_gitlab_properties` (647-702) are one function ×3; `_create_course` repeats the create-group→child-config→update-properties block three times (314-332, 337-355, 357-376); full-instance group scans `self.gitlab.groups.list(all=True)` at lines 550, 590.

**Steps:**
1. Replace the two subgroup methods with `_ensure_subgroup(course, parent_group, path, name, prop_key)`; call it twice.
2. Merge the two config builders into `_build_gitlab_config(group, include_token: bool)`.
3. Replace the three property-updaters with `_set_gitlab_properties(entity, gitlab_config)` (flag_modified + flush + refresh).
4. In `_create_course`, extract `_ensure_course_group(existing_course_or_none, parent_group)` so validation/recreation happens once.
5. Replace `groups.list(all=True)` scans with `gitlab.groups.get(full_path)` (python-gitlab accepts URL-encoded full path) with a 404 fallback to create.

**Risks / verification:** Property JSON shapes (`students_group`, `tutors_group`, `projects` role slots) are read by workflows and web — keep keys identical. Test: `_create_course` on a fresh course and on an existing course with a stale group_id (recreation path); `tests/test_course_creation.py` covers part of this.

---

## TASK-307: Deduplicate student/tutor testing activities (artifact upload, api-config, client preamble)

- **Category:** duplication — **Priority: P2** — **Effort: S**
- **Files:** `tasks/temporal_student_testing.py:559-618` (`store_test_artifacts`) vs `tasks/temporal_tutor_testing.py:112-171` (`store_tutor_test_artifacts_activity`) — identical ZIP-walk-upload except endpoint; env-override block duplicated verbatim (`temporal_student_testing.py:645-653` vs `temporal_tutor_testing.py:250-258`); the `base_url = transform_localhost_url(...); api_token = ...; if not api_token: raise ApplicationError` + `ComputorClient(...)` preamble appears in 7 activities; both workflows pass a dead placeholder `api_config = {"url": "http://localhost:8000", "token": None}` (`student_testing.py:793-798`, `tutor_testing.py:398-403`) that activities immediately override from env.

**Steps:**
1. Create `tasks/api_client.py` with `resolve_api_config(api_config: dict|None) -> dict` (env-first), `open_computor_client(api_config)` (async context manager doing the transform/validate/header dance), and `upload_artifacts_zip(client, endpoint, artifacts_path) -> int` (the shared walk/zip/upload).
2. Point both artifact activities at `upload_artifacts_zip` with their respective endpoints.
3. Delete the placeholder api_config from both workflows and make the activity parameter optional (`api_config: Optional[dict] = None`) — env is already authoritative.

**Risks / verification:** Activity signatures are positional in `workflow.execute_activity(args=[...])`; keep arity or update both sides together. Test: one student test run + one tutor test run with artifacts.

---

## TASK-308: Reduce workflow-module boilerplate (registration ×4, repeated run() scaffolding)

- **Category:** consistency — **Priority: P2** — **Effort: M**
- **Files:** `tasks/registry.py` + per-module `WORKFLOWS`/`ACTIVITIES` lists + `tasks/__init__.py:20-41` import list + `tasks/temporal_worker.py:32-52` `_TEMPORAL_MODULES` — four places to touch per new module. Every `run()` repeats: extract params → validate required → build `RetryPolicy(initial_interval, backoff_coefficient=2.0, maximum_attempts=3)` → `execute_activity` → map to `WorkflowResult` → catch-all except → failed `WorkflowResult` (see `temporal_hierarchy_management.py:160-224`, `temporal_assignments_repository.py:321-348`, `temporal_student_template_v2.py:1347-1411`, `temporal_student_testing.py:765-843`, `temporal_tutor_testing.py:368-464`, `temporal_coder_setup.py` ×3).

**Steps:**
1. Make `register_task` also record the module's activities (add `register_activity` or scan the module), then derive worker registration from `task_registry` — collapse `_TEMPORAL_MODULES` and the `__init__.py` import list to a single `TEMPORAL_TASK_MODULES = [...]` constant imported by both.
2. Add to `BaseWorkflow`: `require_params(params, *names) -> Optional[WorkflowResult]` and `default_activity_retry_policy()` (the 5s/1m/3/2.0 policy used verbatim in 6 files); optionally `run_single_activity(activity_fn, args, timeout)` for the 5 single-activity workflows.
3. Standardize the `status` vocabulary — currently `"success"` (`temporal_student_repository.py:881`) vs `"completed"` everywhere else.

**Risks / verification:** `"success"`→`"completed"` change affects anything reading that workflow's result — check `result.status != "completed"` patterns and the web UI. Test: submit each workflow type via TaskExecutor; check the tasks UI listing.

---

## TASK-309: Delete dead code (analytics ghost package, commented blocks, demo workflows in prod)

- **Category:** dead-code — **Priority: P2** — **Effort: S**
- **Files:** `analytics/` (contains ONLY untracked `__pycache__/*.pyc` — no `.py`, zero importers, zero git history at this path); `tasks/temporal_student_template_v2.py:246-275` (`download_example_from_git` — 25 commented-out lines then `raise NotImplementedError`); `tasks/temporal_examples.py` (3 demo workflows + 2 activities registered in the production worker, submittable via public task API); `tasks/temporal_executor.py:282-298` (commented `get_queue_stats`); `temporal_student_template_v2.py:567-570` (commented org query).

**Steps:**
1. Delete the `analytics/` directory (stale bytecode only).
2. Reduce `download_example_from_git` to docstring + `raise NotImplementedError` (delete the commented body), or delete it and let `download_example_files` raise directly for `source_type == 'git'`.
3. Gate `temporal_examples` registration behind an env flag (e.g. only append to module list when `COMPUTOR_ENABLE_EXAMPLE_TASKS=1`) or move under `tests/` — anyone can currently submit `example_long_running` with arbitrary `duration` through the task API.
4. Delete the commented blocks in `temporal_executor.py:282-298` and `temporal_student_template_v2.py:567-570`.

**Risks / verification:** Confirm no ops tooling/smoke test submits `example_long_running` (grep found no api/business_logic callers; also check `scripts/` and CI configs before removal).

---

## TASK-310: Centralize task-layer config/env access into pydantic settings

- **Category:** config — **Priority: P2** — **Effort: M**
- **Files:** `tasks/temporal_client.py:13-20` (module-level env), `tasks/temporal_student_testing.py:37,647-648`, `tasks/temporal_tutor_testing.py:252-253`, `tasks/temporal_assignments_repository.py:147-148`, `tasks/temporal_student_template_v2.py:645-646`, `tasks/temporal_coder_setup.py:114,132,142,220,236`, `testing/backends.py:61,65,135,288`, `websocket/event_publisher.py:47-53` (REDIS_* re-read). `"http://localhost:8000"` hardcoded as default 11× in `tasks/`. Contrast: proper pydantic settings already exist in `coder/config.py`, `git_server/config.py`, `settings.py`.

**Steps:**
1. Create `tasks/worker_settings.py` (pydantic `BaseSettings`): `api_url`, `api_token`, `system_git_email`, `system_git_name`, `example_cache_dir`, `temporal_host/port/namespace/tls_*`, `coder_registry_host`, `docker_socket_path`.
2. Replace all `os.environ.get` in `tasks/` and `testing/backends.py` with `get_worker_settings()` accessors; settings read only inside activities (workflow determinism — convention already documented at `temporal_student_testing.py:793`).
3. Have `temporal_client.py` read from the settings object instead of module-level constants (currently env is frozen at import; lazily-read settings also make it testable).
4. Point `event_publisher._get_sync_redis` at the existing redis settings used by `redis_cache` instead of re-reading env.

**Risks / verification:** Settings must be read lazily to preserve behavior under test overrides. Test: worker boot in docker compose (env-driven), one testing workflow, one release workflow.

---

## TASK-311: Fix blocking I/O inside async Temporal activities

- **Category:** reliability — **Priority: P2** — **Effort: M**
- **Files:** All git/DB-heavy activities are `async def` but do blocking work: GitPython subprocesses + sync SQLAlchemy sessions in `temporal_student_template_v2.py:433-1321`, `temporal_assignments_repository.py:26-303`; sync python-gitlab HTTP in `temporal_student_repository.py`; `subprocess.run(..., timeout=300)` in `temporal_coder_setup.py:254` and `testing/backends.py:74,311`; sync `redis.Redis.publish` via `websocket/event_publisher.py:61-84` called from inside activities; `time.sleep` in `git_provider/gitlab.py:225`.

**Problem:** Async activities run on the worker's event loop; a multi-minute blocking clone/build stalls heartbeats and every other activity on that worker.

**Steps:**
1. Classify activities: pure-async (Coder API, ComputorClient testing fetch/upload) stay `async def`; blocking ones (template generation, assignments repo, student repo fork, image build, subprocess test execution) become plain `def` activities, and register a `ThreadPoolExecutor` via `Worker(activity_executor=...)` in `temporal_worker.py:106-114`.
2. Alternatively (smaller diff): wrap the blocking bodies in `asyncio.to_thread(...)`.
3. For `event_publisher`, keep sync (it's called from sync API code too) but call it via `asyncio.to_thread` from async activities, or add an async variant using the existing `websocket/pubsub` client.

**Risks / verification:** Sync activities can't `await` shared helpers (`download_example_files` is async — needs a sync wrapper or the to_thread approach). Test under load: run a template release concurrently with student tests on one worker; confirm neither starves.

---

## TASK-312: Replace print() with logging; fix swallowed-error contract in `list_tasks`

- **Category:** error-handling — **Priority: P3** — **Effort: S**
- **Files:** `gitlab_utils.py:4-24` (print for success/404/exception paths; `except Exception ... print ... raise e`), `tasks/temporal_executor.py:396-406` (`print(f"Error listing workflows: {e}")` then returns an empty page with the error embedded — API consumers see success-shaped payloads).

**Steps:**
1. Replace `print` with `logging.getLogger(__name__)` calls in both files; drop redundant `raise e` → `raise`.
2. In `list_tasks`, log via `logger.exception` and decide the contract: either propagate (matching `get_task_status`'s raise behavior) or keep the soft-fail and document it — today the two methods disagree.

**Risks / verification:** None functional if soft-fail retained; if switched to raise, the tasks-list UI endpoint needs a try/except.

---

## TASK-313: `task_tracker.py` — deduplicate accessible-ID computation

- **Category:** duplication — **Priority: P3** — **Effort: S**
- **Files:** `task_tracker.py:207-262` (`list_accessible_tasks`) vs `:264-303` (`get_accessible_task_ids`) — admin/user/lecturer index-union logic verbatim-identical (~30 lines).

**Steps:**
1. Make `list_accessible_tasks` call `await self.get_accessible_task_ids(permissions)`, then fetch/sort/paginate entries.
2. Optional: replace the N× `self.redis.get` loop with a single `mget` pipeline for large task sets.

**Risks / verification:** None; both methods already share semantics. Test the task-listing endpoint for admin and lecturer principals.
