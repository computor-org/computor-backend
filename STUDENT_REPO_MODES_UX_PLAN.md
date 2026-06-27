# Student Repository Modes UX — Implementation Plan (effort "b")

Branch: `feat/student-repo-modes-ux` (computor-fullstack + computor-vsc-extension, both off
`release/2026.10`). Consumes the managed-GitLab backend already merged
(`GITLAB_MANAGED_PROVISIONING_PLAN.md`).

## Goal

Build the student + lecturer repository UX **once**, across all backends, driven by the course's
single configured mode — instead of bolting each mode on separately. Modes:

- **managed** — Computor hosts the student repo. Dispatches on the bound `GitServer.type`:
  Forgejo (existing) or GitLab (new GLPAT-register flow). Staff get access implicitly.
- **external** — student hosts their own repo on **any** git provider (provider-agnostic; the
  former GitLab-only "BYO"). Linked to the course template as `upstream`.
- **download** — no student repo; the student downloads the template as a ZIP and works locally.

Includes the rename (`student-template`→`template`, `assignments`→`reference`) and the drafted
user-facing descriptions.

## Decisions (defaults — confirm the risky ones before building)

- **Single mode field.** Add a singular `student_repo_mode` to the course binding (the list
  `student_repo_modes` stays as the *offered* set during migration; UI configures one). *Low risk,
  additive.*
- **Download content source.** Stream the bound managed server's **archive API** (Forgejo
  `/api/v1/repos/{owner}/{repo}/archive/{ref}.zip`; GitLab `/api/v4/projects/{id}/repository/archive.zip`),
  authenticated with the registry service token. No MinIO path. *Low risk.*
- **External seeding.** The client seeds an empty external repo from the template; the backend
  exposes a **read-scoped way to fetch the template** (reuse the download archive, or a short-lived
  read token). Recommend: reuse the archive endpoint for the seed content. *Low risk.*
- **`GET /git-servers` gate.** Relax LIST (read-only, no secrets) to the course-creator cohort so the
  lecturer picker works; keep create/update/delete admin-only. *Needs the "who creates courses" call.*
- **Rename rollout.** `assignments`→`reference`, `student-template`→`template`. Already used on the
  new managed-GitLab path. Applying it to the **legacy** Forgejo/GitLab repos + the two Temporal
  workflows is **risky** (existing courses, orphaning) — keep it a **separate, deliberate sub-task**,
  not bundled with the UX.

## Phases

1. **Backend prereqs** (additive):
   - [x] `GET /user/courses/{id}/template/archive` — backend fetches the template from the bound
         managed server with the service token and returns the ZIP (download mode + external seed
         source); membership-gated, student never sees the token. (`get_template_archive_source` +
         endpoint in `api/user.py`.)
   - [ ] Single `student_repo_mode` on the binding (DTO + column/migration) alongside the offered list.
   - [x] Relax `GET /git-servers` LIST to authenticated users (read-only; no secrets). Mutations stay
         registry-admin. (`list_git_servers`.)
2. **Extension — student** (`computor-vsc-extension`):
   - [ ] Drive the flow off the single course mode; drop the "where should your repo live?" picker.
   - [x] managed: Forgejo (existing) + **GitLab** — `provisionAndCloneGitlabManaged` (provision fork →
         prompt GLPAT via `GitLabTokenManager` → `register-gitlab` → clone with the student's token).
         `StudentRepoMode` + `registerGitlabManaged` API method + picker entry. Type-check clean.
   - [ ] external: provider-agnostic refactor of `GitLabByoProvisioner`/`GitLabTokenManager`; add the
         **seed/link** step (clone template → push to the student's empty repo → set `upstream`).
   - [x] download: **"Download Template"** command (`computor.student.downloadTemplate`) → the archive
         endpoint; offers save-as-ZIP or extract-to-folder (jszip, strips the git-archive wrapper dir).
         Type-check clean.
   - [ ] Apply the drafted descriptions/prompts.
3. **Extension — lecturer:**
   - [x] **Configure Course Git** command (`computor.lecturer.configureCourseGit`, on a course tree
         item) — pick a managed git server + the modes to offer (managed / download / external) →
         `PUT /courses/{id}/git`. For managed GitLab this provisions the course structure server-side.
   - [ ] Fold the selector into `createCourse` itself (needs `CourseTaskRequest` + the async course
         deploy task to set the binding at creation; the dedicated command covers it for now).
4. **Web UI (`computor-web`):** course git-config panel + GitServer-registry admin (greenfield;
   generate the missing TS types/clients).
5. **Tests + copy.**

## Status

- [x] Branches created (both repos), managed-GitLab backend merged into `release/2026.10`.
- [ ] Phase 1 …
