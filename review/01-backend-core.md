# Refactoring Plan: Backend Core / Data Layers

**Scope:** `computor-backend/src/computor_backend/` — `model/`, `repositories/`, `database.py`, `cache.py`, `redis_cache.py`, `permissions/`, `auth/`, `middleware/`, `exceptions/`, `custom_types/`, `settings.py`, `storage_config.py`, `storage_security.py`, `minio_client.py`, `utils/`
**Reviewed:** 2026-07-07 (branch `release/2026.10`)
**Total LOC in scope:** ~24,100

## Architecture context (read first)

FastAPI app; `database.py` provides a sync SQLAlchemy engine + `get_db`/`get_db_session` (commit-on-exit). `model/` holds declarative models (bare `Base`, no mixins). `repositories/` has two families: entity repos extending `BaseRepository[T]` (write-through Redis caching via `cache.py`'s tag-based `Cache`) and `ViewRepository` subclasses (student/tutor/lecturer views, self-managed lazy DB sessions). `permissions/` is a handler-registry system: `auth.py` builds a `Principal` (Redis-cached per token hash), `handlers_impl.py` implements per-entity `can_perform_action`/`build_query`, `core.py` registers handlers. `redis_cache.py` exposes module-level sync+async Redis clients. `exceptions/` maps a YAML error registry to typed `ComputorException`s. **The repository layer is largely bypassed: most of `api/` and `business_logic/` query sessions directly.**

**Key metrics:** largest files: `permissions/handlers_impl.py` 1310 LOC, `repositories/course_member_gradings.py` 1195, `repositories/course_content_queries.py` 975, `repositories/view_base.py` 729, `cache.py` 642, `model/course.py` 628, `repositories/base.py` 610. 53 broad `except Exception`; 10 `print()` (all `auth/keycloak.py`); 54 function-level deferred imports (circular-import workarounds).

**Safety-net note:** Tasks 103, 108, 109, 110 touch authorization or transaction semantics. Before starting those, verify integration-test coverage of (a) course-member CRUD + permission cache invalidation, (b) org/family scoped visibility, (c) submission write flows — add characterization tests where missing.

---

## TASK-101: Fix class-name collision — two `CourseMemberRepository` classes (model vs repository)

- **Category:** consistency — **Priority: P1** — **Effort: S**
- **Files:** `model/git_server.py:117` (SQLAlchemy model — a member's git repo record), `repositories/course_member.py:23` (repository class). Consumers of both names: `business_logic/course_git.py:774,816,961` (model), `business_logic/tutor.py:103` (repository). `repositories/submission_group_provisioning.py:47` already does a function-level import specifically to dodge this.

**Problem:** A database model and a data-access repository share the exact class name `CourseMemberRepository`. Which one you get depends on the import path — a live footgun for auto-imports and refactors.

**Steps:**
1. Rename the model in `model/git_server.py` to `CourseMemberGitRepository` (table name unchanged — no DB migration).
2. Update the three call sites in `business_logic/course_git.py` and the import in `repositories/submission_group_provisioning.py` (hoist it to module level once un-conflicted).
3. `grep -rn "CourseMemberRepository"` to confirm remaining references are the repository class only.

**Risks / verification:** Purely mechanical rename; run the course-git provisioning tests.

---

## TASK-102: Fix broken/LSP-violating overrides and silently-skipped filters in `BaseRepository`

- **Category:** error-handling — **Priority: P1** — **Effort: M**
- **Files:** `repositories/base.py:296-298,503-505,538-540,569-571` (filter loop `if hasattr(self.model, key)` silently drops unknown criteria); `repositories/course_member.py:86-102,104-125,242-249`.

**Problem:** `CourseMemberRepository.update(self, entity)` calls `super().update(entity)` but the base signature is `update(self, entity_id, updates)` (`base.py:354`) — a guaranteed `TypeError` if ever called; `delete(self, entity)` similarly passes an ORM instance where the base expects an ID. Currently dead code paths, which is why nothing crashes. Worse: `find_active_members()` (`course_member.py:249`) calls `find_by(archived_at=None)`, but `CourseMember` has no `archived_at` column (`model/course.py:359-408`) — the `hasattr` guard silently drops the filter and the method returns **all** members. The silent-skip design converts typos into wrong data.

**Steps:**
1. In `base.py`, replace the `hasattr` guards in `list`, `find_by`, `find_one_by`, `count` with `raise ValueError(f"{self.model.__name__} has no column {key}")` (or use `self.model.__mapper__.attrs` lookup).
2. Delete the broken `update`/`delete` overrides in `course_member.py`; move `_invalidate_permission_cache` into overrides matching the base signatures, or add post-write hooks (`_after_create/_after_update/_after_delete`) to `BaseRepository` and implement those instead.
3. Delete `find_active_members` (no `archived_at` column) or add the column if genuinely intended.
4. Chain the swallowed cause at `base.py:344-349`: `raise DuplicateError(...) from e`.

**Risks / verification:** Strict filter validation may surface latent bad callers — run the full repository/API test suite and grep call sites of `find_by`/`find_one_by` for keyword typos first.

---

## TASK-103: Establish a single unit-of-work (repositories commit mid-request vs `get_db` commit at request end)

- **Category:** layering — **Priority: P1** — **Effort: L** — **HIGHEST-RISK TASK IN THIS FILE**
- **Files:** `repositories/base.py:334,377,419,457` (`self.db.commit()` inside `create/update/update_entity/delete`); `database.py:60-79` (`_get_db` commits on generator exit); `permissions/auth.py:213` (commit inside authentication, updating token usage stats).

**Problem:** No single unit-of-work. A handler that uses a repository plus direct session writes gets partial commits: the repo commit flushes everything pending on the shared session, so a later exception cannot roll back earlier "repo" writes. It also breaks `SET LOCAL app.user_id` audit tracking (`database.py:65`) — `SET LOCAL` is transaction-scoped, so after the repo's first commit, subsequent statements in the same request lose `created_by/updated_by` attribution.

**Steps:**
1. Change `BaseRepository.create/update/update_entity/delete` to `flush()` (+ `refresh`) instead of `commit()`.
2. Let `get_db`/`get_db_session` remain the sole commit point.
3. Cache invalidation must not fire for rolled-back transactions: collect tags on the session (e.g. `db.info.setdefault("cache_tags", set())`) and invalidate them in `_get_db` after the successful `commit()`.
4. Audit the ~10 direct repo-write call sites (`api/submissions.py:524,1297`, `api/results.py:145`, `api/course_contents.py:227`, `api/examples.py:1011`, `business_logic/auth.py:248`, `business_logic/submissions.py:736`, `business_logic/api_tokens.py:359`) for code relying on the immediate commit (e.g. reading server defaults) and adjust.

**Risks / verification:** Behavior around IntegrityError timing shifts from repo-call-time to request-end. Build an integration-test safety net around submissions/grading writes BEFORE starting.

---

## TASK-104: Single source of truth for grading-status vocabulary (currently 5 implementations)

- **Category:** duplication — **Priority: P1** — **Effort: M**
- **Files:** `model/course.py:25-30` (`GradingStatus(IntEnum)`), `computor-types/src/computor_types/grading.py` (second `GradingStatus` — the one `repositories/view_mappers.py:16` uses), literal `{0:"not_reviewed",...}` maps at `repositories/view_base.py:698-703` and `repositories/student_view.py:153-158`, `repositories/view_mappers.py:44-48` (`_GRADING_STATUS_LOOKUP`), aggregation rules duplicated in Python (`utils/grading_status.py:15-26`) and raw SQL (`repositories/course_member_gradings.py:481-489`), `model/artifact.py:171` storing the raw int with a comment as documentation.

**Problem:** Adding a status value requires touching 5+ places in two packages; the SQL CASE and the Python aggregator can drift silently. Additionally `repositories/student_view.py:~130-185` is a ~60-line verbatim copy of `ViewRepository._aggregate_single_unit_status_for_list` (`view_base.py:662-729`) including magic tuple indices.

**Steps:**
1. Keep `computor_types.grading.GradingStatus` as the single enum; delete `model/course.py:25-30` and re-import where needed (`business_logic/tutor.py` already uses the computor_types one).
2. Add `GradingStatus.to_slug()`/`from_int()` (or a `STATUS_SLUGS` dict) in `computor_types/grading.py`; replace the three literal maps.
3. Delete `StudentViewRepository._aggregate_single_unit_status` and call the inherited `_aggregate_single_unit_status_for_list`.
4. Replace raw `row[3]/row[5]/row[10]` indexing in `view_base.py:713-717` and `student_view.py` with the existing `CourseMemberCourseContentQueryResult.from_tuple` (`repositories/course_content_queries.py:74`), which already names those columns.
5. In `course_member_gradings.py` SQL, add a comment pointing at the enum, or generate the CASE values from the enum ints.

**Risks / verification:** Status mapping is user-visible (student/tutor dashboards); snapshot the view endpoints' JSON before/after.

---

## TASK-105: Delete the dead & broken permission-caching layer

- **Category:** dead-code — **Priority: P1** — **Effort: S**
- **Files:** `permissions/cache.py:25-238` (`PermissionCache`, `CoursePermissionCache`, `cached_permission_check`); only external references are re-exports in `permissions/__init__.py:54-56,98-100`. `permissions/query_builders.py:46-84` (`user_courses_subquery_cached`) has zero callers.

**Problem:** ~215 lines of unused code that is also wrong: `PermissionCache.invalidate_user` never deletes Redis keys (only logs, `cache.py:129-136`), and `CoursePermissionCache.get_user_courses_cached` wraps an instance method reading mutable state in `@lru_cache` (`cache.py:155-156`) — would cache stale/None results indefinitely. The dead `user_courses_subquery_cached` contains an `asyncio.run()`-inside-sync hack. Keeping broken "security cache" code invites someone to wire it in.

**Steps:**
1. Delete `PermissionCache`, `CoursePermissionCache`, `permission_cache`, `course_permission_cache`, `cached_permission_check` from `permissions/cache.py` and their exports in `permissions/__init__.py`.
2. Keep the actually-used functions: `get_user_course_memberships`, `get_user_courses_with_role`, `invalidate_user_course_memberships`, `invalidate_course_all_memberships`.
3. Delete `CoursePermissionQueryBuilder.user_courses_subquery_cached` in `query_builders.py` (and its `asyncio` import).
4. Also delete the never-used `ViewRepository._build_cache_key` (`repositories/view_base.py:88-107`).

**Risks / verification:** Minimal — `grep -rn` after removal; run the test suite.

---

## TASK-106: Remove `asyncio.run()` from sync repository cache invalidation

- **Category:** consistency — **Priority: P1** — **Effort: M**
- **Files:** `repositories/course_member.py:60,120`; root cause: `permissions/cache.py:361-379` (`invalidate_user_course_memberships` is async-only because `redis_cache.get_redis_client` returns the async client).

**Problem:** `asyncio.run()` raises `RuntimeError` whenever a running event loop exists in the thread — so this invalidation silently no-ops (caught at `course_member.py:62-66`, merely logged) if the repository is ever used from an async endpoint or Temporal activity. The module's own docstring calls this invalidation "CRITICAL for security".

**Steps:**
1. Add a sync variant in `permissions/cache.py` using the existing sync client (`redis_cache._sync_redis_client`, exposed via `get_cache().client`): `def invalidate_user_course_memberships_sync(user_id)` deleting `permission:user:{user_id}:course_memberships`.
2. Call it from `CourseMemberRepository._invalidate_permission_cache` and the delete path; drop `asyncio` from the module.
3. Keep the async version for async callers as a thin wrapper sharing the key constant — extract `def _membership_cache_key(user_id)` so the key string exists once (currently duplicated at `cache.py:267,372,405`).

**Risks / verification:** Low; integration test with Redis that creating/updating/deleting a course member invalidates `permission:user:<id>:course_memberships`.

---

## TASK-107: Deduplicate Principal-cache logic and cache-key convention (3 modules)

- **Category:** duplication — **Priority: P2** — **Effort: M**
- **Files:** `permissions/auth.py:302-336` (`build_with_cache`), `auth.py:394-455` (`get_current_principal` re-implements get/validate/ban-check/set inline), `auth.py:469-499` (`get_current_principal_optional`, a third variant), key derivation `sha256(f"sso_permissions:{token}")` duplicated at `auth.py:396-403` and `auth.py:489-491`, re-implemented a third time in `middleware/principal_lookup.py:97-109` ("Same cache key format as permissions/auth.py").

**Problem:** The cache-hit path (deserialize + banned-flag check) exists twice with drift risk, and the key convention is a magic-string contract between `auth.py` and the middleware. `auth.py:496` has `except (UnauthorizedException, Exception)` — redundant first element; the catch swallows programming errors during optional auth.

**Steps:**
1. In `permissions/auth.py`, add `def principal_cache_key(kind: str, token: str) -> str`; use it in both places; import it from `middleware/principal_lookup.py` instead of re-hashing.
2. Extract `async def _get_cached_principal(cache_key) -> Optional[Principal]` (get + `model_validate` + `is_user_banned_cached` gate) and `async def _store_principal(cache_key, principal)`; have `get_current_principal`, `build_with_cache`, and `get_current_principal_optional` all call them.
3. Replace `except (UnauthorizedException, Exception)` at `auth.py:496` with `except UnauthorizedException` plus a separate `except Exception` logging at warning with `exc_info`.

**Risks / verification:** Auth hot path — cover with existing auth tests plus one test for the ban-on-cache-hit path before refactoring.

---

## TASK-108: `Principal.permitted()` cache key ignores `course_role` (wrong cached answers possible)

- **Category:** error-handling — **Priority: P1** — **Effort: S**
- **Files:** `permissions/principal.py:220-222` (`_cache_key` = `f"{resource}:{action}:{resource_id or ''}"`), `principal.py:428-451`.

**Problem:** `permitted("course", "get", cid, course_role="_lecturer")` and the same call with `course_role="_student"` share one cache slot; whichever runs first fixes the answer for the other within that `Principal` instance. Handlers call `permitted(..., course_role=...)` (e.g. `core.py:247`), so a single request checking two different role floors on the same course can read a stale result — an authorization correctness hazard hiding as a micro-optimization.

**Steps (option 2 recommended):**
1. Option 1: include `course_role` in `_cache_key` (`f"{resource}:{action}:{resource_id or ''}:{course_role or ''}"`).
2. Option 2 (simpler, recommended): delete `_permission_cache` entirely — every check is dict/set lookups on in-memory claims; the cache buys nothing measurable. Remove `_permission_cache`, `_cache_key`, `clear_permission_cache`.
3. Add a regression test asserting the two role-floor checks return independent results.

**Risks / verification:** None functional if option 2 is taken (pure lookups).

---

## TASK-109: Split `handlers_impl.py` god file; merge near-verbatim scoped-handler clones

- **Category:** god-file — **Priority: P2** — **Effort: M**
- **Files:** `permissions/handlers_impl.py` (1310 lines, 18 handler classes). `OrganizationPermissionHandler` (253-344) vs `CourseFamilyPermissionHandler` (346-425) differ only in scope name, the `Course` FK column (`organization_id`/`course_family_id`), and the role-map attribute — the docstring even says "Symmetric to OrganizationPermissionHandler". The file already contains the right pattern: `_ScopeMemberPermissionHandler` (1113-1244) parametrizes exactly this for member entities.

**Problem:** ~170 duplicated lines of security-critical query logic; any fix must be applied twice. One module mixes 18 unrelated entity policies.

**Steps:**
1. Create `_ScopedEntityPermissionHandler(PermissionHandler)` with class attrs `scope_name`, `course_fk_column` (callable returning `Course.<col>`), `ACTION_ROLE_MAP`, `READ_COURSE_ROLE`; move the shared `can_perform_action`/`build_query` bodies there.
2. Reduce `OrganizationPermissionHandler`/`CourseFamilyPermissionHandler` to ~5-line subclasses (mirroring how the member handlers already subclass `_ScopeMemberPermissionHandler`).
3. Split the module by domain: `handlers_user.py` (User/Account/Profile/StudentProfile), `handlers_course.py` (Course/Content/Member/Message/Result), `handlers_scoped.py` (org/family + members), `handlers_misc.py` (ReadOnly, Example, UserRole); keep `handlers_impl.py` as a re-export shim so `core.py:12-30` imports don't change in step one.

**Risks / verification:** Permission behavior must be bit-identical — write table-driven tests over `can_perform_action` for both scopes (admin / general claim / scoped role / none) BEFORE extracting.

---

## TASK-110: Decide the repository-layer question (bypassed by most of the codebase)

- **Category:** consistency — **Priority: P2** — **Effort: L**
- **Files:** 24 `BaseRepository` subclasses under `repositories/`, but `api/` has 111 raw `db.query(` calls and `business_logic/` 295, versus ~11 repository usages total (e.g. `OrganizationRepository`: 0 call sites). Cache-deserialization hack: `repositories/base.py:164-212` (`object.__new__` + manual `InstanceState`, plus `ast.literal_eval` fallback for "legacy cached JSONB").

**Problem:** Two parallel data-access idioms coexist; the write-through entity cache only works when writes go through repositories, so any raw-session write to a cached entity (the common case) leaves stale cache entries until TTL. The repos carry heavy machinery (detached-ORM reconstruction from JSON) serving almost no traffic. The newer layer never won adoption.

**Steps:**
1. Decide direction explicitly (recommend: keep repositories only where caching demonstrably matters — `CourseMember`, `Organization`, `ApiToken` — and delete unused repo subclasses; grep each of the 24 for external call sites first).
2. For entities kept cached, route the remaining raw writes in `api/`/`business_logic/` through the repo or at least through a shared invalidation helper (tags already defined in each repo's `get_entity_tags`).
3. Remove the legacy-format branches in `_deserialize_entity` (`base.py:190-204`) — the "old cached data" they guard against expired long ago (TTL ≤ 15 min).
4. Document the chosen pattern in `repositories/__init__.py` docstring so new endpoints stop flip-flopping.

**Risks / verification:** Deleting repos is safe after call-site grep; consolidating writes risks cache-staleness changes — verify entity-cache hit/miss behavior in integration tests with Redis.

---

## TASK-111: Introduce model mixins for the 19×-repeated audit-column boilerplate

- **Category:** duplication — **Priority: P2** — **Effort: M**
- **Files:** `model/base.py` (4 lines, bare `declarative_base()`); the block `id/version/created_at/updated_at/created_by/updated_by/properties` + `created_by_user`/`updated_by_user` relationships repeated in 19 classes across `model/auth.py, course.py, git_server.py, organization.py, result.py, message.py` (24 `created_by_user = relationship(...)` occurrences). `try: from ..custom_types import LtreeType except ImportError:` duplicated in `model/course.py:11-15`, `model/organization.py:11`, `model/deployment.py:20`, `model/example.py:17`, `model/service.py:26`.

**Steps:**
1. In `model/base.py`, add `class UUIDPkMixin` (`id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))`), `class VersionedMixin` (`version`), and `class AuditMixin` using `@declared_attr` for `created_at/updated_at/created_by/updated_by` and the two user relationships (declared_attr required for `relationship` on mixins; `foreign_keys` need lambdas).
2. Migrate one model file at a time (`class Course(UUIDPkMixin, AuditMixin, Base)`), asserting `Base.metadata` unchanged via `alembic revision --autogenerate` producing an empty diff after each file.
3. Fix `alembic/env.py` to put the package root on `sys.path` (or use `prepend_sys_path` in `alembic.ini`) and delete the five try/except import fallbacks, importing `from computor_backend.custom_types import LtreeType` unconditionally.

**Risks / verification:** Mapper configuration errors surface at import time (fast feedback); the empty-autogenerate check is the safety net. Test one model with `Mapper.configure_mappers()` before rolling out.

---

## TASK-112: Remove debug print()s and secret-bearing logs from Keycloak token exchange

- **Category:** error-handling — **Priority: P2** — **Effort: S**
- **Files:** `auth/keycloak.py:218,220,308-340` — 10 `print(f"[DEBUG] ...")` calls, plus `logger.info(f"Request data: {data}")` (~line 312) where `data` contains `client_secret`, and `print(f"[DEBUG] Starting token exchange for code: {code[:20]}...")` leaking an authorization-code prefix. Also `get_login_url` (line 204) builds the query string manually without URL-encoding (`"&".join(f"{k}={v}")`).

**Steps:**
1. Delete all 10 `print` calls; convert genuinely useful ones to `logger.debug`.
2. Redact `data` before logging: log only `grant_type`, `client_id`, presence of `redirect_uri`.
3. Replace manual query building with `urllib.parse.urlencode(params)`.

**Risks / verification:** Smoke-test the SSO login flow (Keycloak realm `computor`).

---

## TASK-113: Consolidate configuration (8 modules, import-time side effects)

- **Category:** consistency — **Priority: P3** — **Effort: M**
- **Files:** `database.py:13-34` (env + engine created at import), `redis_cache.py:15-49` (two Redis clients at import), `minio_client.py:29-41`, `storage_config.py:7-10`, `settings.py` (hand-rolled thread-safe singleton `BackendSettings`), `auth/keycloak.py`, `auth/keycloak_admin.py`, `utils/docker_utils.py`.

**Problem:** Env read at import time in five places outside `settings.py`, so tests/scripts can't override config after import; importing `database.py` constructs an engine even for code that never touches the DB. `settings.py` re-implements what pydantic-settings provides and doesn't cover DB/Redis/MinIO.

**Steps:**
1. Introduce `computor_backend/config.py` with pydantic-settings classes (`DatabaseSettings`, `RedisSettings`, `MinioSettings`, `AppSettings`) and a cached `get_settings()`.
2. Convert `database.py`'s engine and `redis_cache.py`'s clients to lazily-initialized accessors (`get_engine()`, `get_async_redis()`), keeping module-level names as deprecated aliases initially.
3. Fold `storage_config.py`'s size limits and `BackendSettings` fields into `AppSettings`; keep a `settings = ...` shim for the 20+ import sites.

**Risks / verification:** Import-order sensitivity (anything importing `database.SessionLocal` at module scope); do it alias-first, flip call sites incrementally, run the full test suite plus a container boot check.

---

## TASK-114: `course_member_gradings.py` — dedupe aggregation blocks; resolve the parallel stats implementation

- **Category:** god-file — **Priority: P3** — **Effort: M**
- **Files:** `repositories/course_member_gradings.py` (1195 lines: repository with 10 query methods + two ~180-line pure functions `calculate_grading_stats`:916 and `calculate_grading_stats_for_all_members`:1094). The "collect content types / latest-submission max / per-content-type stats" block is copy-pasted 4× inside these two functions. A second, live implementation of hierarchical stats exists in `utils/grading_stats.py:process_hierarchical_stats` (used by `repositories/grading_read.py:59-72`).

**Steps:**
1. First determine whether the Python pipeline still has callers (grep `calculate_grading_stats` — currently only re-exported via `business_logic/course_member_gradings.py:25` with `noqa: F401`); if the SQL pipeline fully replaced it, **delete instead of refactor**.
2. If kept: extract helpers into `utils/grading_stats.py` (`collect_content_types(contents)`, `latest_submission(subs)`, `content_type_stats(contents, submitted_ids, submitted_info)`); rewrite both `calculate_*` functions on top (pure functions — characterization-test first).
3. Move both `calculate_*` functions out of the repository module into `utils/grading_stats.py` so `course_member_gradings.py` is queries-only (~800 lines).

**Risks / verification:** Dashboard numbers are user-visible; write golden-output tests for one synthetic course before touching.

---

## TASK-115: Fix stale permission docs; replace magic role strings with `roles.py` enums

- **Category:** dead-code / consistency — **Priority: P3** — **Effort: S**
- **Files:** `permissions/README.md` (claims the system is "NOT YET INTEGRATED" and that the app uses "the old permission system in `api/permissions.py`" — that file no longer exists; 71 files import the new system) and `permissions/MIGRATION_GUIDE.md` (instructs importing `permissions.migration` / `permissions.integration`, both deleted). Role literals: 63 occurrences of `"_lecturer"/"_student"/"_tutor"/"_maintainer"/"_owner"` across `model/repositories/permissions` while `permissions/roles.py` (the self-declared "single source of truth", imported by only 8 files) provides `CourseRole.LECTURER` etc.

**Steps:**
1. Delete `MIGRATION_GUIDE.md`; rewrite `README.md` (~30 lines) to describe the current integrated architecture and file map.
2. Mechanically replace role literals with `roles.CourseRole`/`ScopeRole` members in `permissions/` first (`handlers_impl.py`, `core.py`), then `repositories/` — the enums are `str` subclasses so `.in_()` filters keep working.

**Risks / verification:** Trivial; string-equality semantics unchanged (str-enum). Run permission tests.
