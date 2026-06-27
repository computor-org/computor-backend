# GitLab Managed Provisioning — Implementation Plan

Branch: `feat/gitlab-managed-provisioning` (computor-fullstack + computor-vsc-extension, both off `release/2026.10`).

## Goal

Make GitLab a **first-class managed provider** alongside Forgejo:

- The backend holds a **parent-group access token** (a registered `GitServer`). With it, it
  provisions a course **flat under that parent group**: a `template` project, a `reference`
  project, and a `students` subgroup; per-student repos are forks into the students subgroup.
- Students gain access by **registering their own GLPAT**: the backend calls `GET /api/v4/user`
  with the student's PAT (proves their GitLab identity — no admin/email-search needed), links the
  GitLab account to the authenticated course member, then uses **its own group token** to grant the
  student membership on their repository.

This re-targets the **existing legacy machinery** (`_fetch_gitlab_user_profile`,
`register_user_course_account` / `validate_user_course`, `_sync_gitlab_memberships` in
`business_logic/users.py`) from the org-level GitLab properties to the new
`GitServer` / `CourseGitBinding` / `CourseMemberRepository` model. It does NOT rebuild them.

## Decisions (defaults — flag to change)

- **Mode value:** `gitlab_managed` (internal, unambiguous vs `gitlab_byo`). User-facing label TBD.
- **No new columns** — GitLab metadata in JSON `properties`:
  - `GitServer.properties.gitlab = { parent_group_id, parent_group_path }`
  - `CourseGitBinding.properties.gitlab = { template_project_id, reference_project_id, students_group_id, students_group_path }`
  - `CourseMemberRepository.properties.gitlab = { project_id, namespace_id }`
- **DB hierarchy unchanged** — Course keeps `organization_id` / `course_family_id` (NOT NULL stays).
  Only the **GitLab** structure is flattened (course group directly under the parent group; no
  GitLab subgroups for org/family). Avoids the large blast radius of nullable course FKs.
- **Student access** = backend group token grants membership by GitLab user-id resolved from the
  student's PAT via `GET /user`. Email match (`User.email` / `StudentProfile.student_email`) is
  optional hardening, not required for the link.
- **No clone-token minting** for GitLab (unlike Forgejo) — the student clones with their own
  GitLab credentials once they are a member.

## Phases

1. **Foundation** — `gitlab_managed` mode: `_VALID_STUDENT_REPO_MODES` (types), `CourseMemberRepository.mode`
   CHECK constraint (model) + alembic migration. Update DTO docstrings.
2. **GitLabProviderClient** (`git_provider/gitlab.py`) — implement, all on the **group token**:
   - `ensure_course_structure(parent_group_id, course_slug)` → create/get `template` + `reference`
     projects and `students` subgroup under the parent group (flat). Reuse `gitlab_builder` calls.
   - `provision_student_fork(template_project_id, students_group_id, name)` → fork into students group.
   - `add_member(project_or_group_id, gitlab_user_id, access_level)`.
   - Resolve parent group from `GitServer.properties.gitlab.parent_group_id` (or discover from token).
3. **`business_logic/course_git.py`** — generalize the Forgejo-only gates to dispatch on
   `server.type` when `managed`; add the `gitlab_managed` provisioning path (create binding metadata
   at upsert, fork at provision, descriptor exposes `gitlab_managed`). No clone token on GitLab branch.
4. **PAT registration → new model** — re-target `register_user_course_account` /
   `_sync_gitlab_memberships` to read server+token from the `GitServer` registry and grant on the
   `CourseMemberRepository` repo. Add/confirm the student endpoint (`/user/courses/{id}/register-gitlab`
   or reuse existing). This is the "register with a GLPAT" piece.
5. **Course-create wiring** — carry `student_repo_mode` + `git_server_id` (+ parent group) into course
   creation so the binding + GitLab structure are set at creation (immutable thereafter).
6. **Extension** (`computor-vsc-extension`) — student "register GLPAT" + managed-GitLab setup flow;
   lecturer course-create mode selector (later sub-task).
7. **Tests** — provider client (mocked GitLab), the PAT-registration link, the provision path.

## Status

- [x] Branches created (backend + extension).
- [x] **Phase 1** — `gitlab_managed` mode: types `_VALID_STUDENT_REPO_MODES`, model CHECK constraint,
      migration `61d25ae196fb` (verified single head).
- [x] **Phase 2** — `GitLabProviderClient` managed methods (`git_provider/gitlab.py`):
      `ensure_course_structure` (flat: course group + `template`/`reference` projects + `students`
      subgroup under a parent group), `provision_student_fork` (fork → students group, unprotect,
      idempotent), `add_member` (grant by GitLab user id via the group token). Reuses
      `gitlab_utils` + python-gitlab; syntax + deps verified.
- [x] **Phase 3** — `business_logic/course_git.py`: renamed `_resolve_forgejo_handle` →
      `_resolve_oidc_handle` (shared); `upsert_course_git_binding` provisions the GitLab structure
      via `ensure_course_structure` and stores it in `binding.properties.gitlab` (adopts the template
      project as the binding template); `provision_student_repository` now dispatches on `server.type`
      (extracted `_provision_forgejo`, added `_provision_gitlab_managed` → fork into students group,
      `mode='gitlab_managed'`). Descriptor already generic. Syntax + import verified.
- [ ] **Phase 4** — re-target PAT registration / membership grant to the new model:
      `register_gitlab_managed_access(course_id, glpat, ...)` — `GET /user` with the student PAT
      (reuse `_fetch_gitlab_user_profile`) → link `Account` → ensure repo provisioned → grant member
      via group token (`add_member`, Maintainer). Endpoint on `api/user.py`. Optional email-match check.
- [ ] **Phase 5** — course-create wiring (mode + git server + parent group).
- [ ] **Phase 6** — extension (student register-GLPAT + managed-GitLab flow).
- [ ] **Phase 7** — tests.
