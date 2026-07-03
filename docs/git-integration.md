# Git Integration

Every course connects to a git backend that hosts its **template** repository (the
assignment skeleton students receive), an optional **reference** repository (full
solutions, staff-only), and each member's **student repository**. Git is configured
**per course** — the choice of server and credentials belongs to the course, not to the
organization.

There are two providers and three delivery/hosting modes.

## Providers & modes

| | **In-system Forgejo** | **External GitLab** | **Download** |
|---|---|---|---|
| `provider` | `forgejo` | `gitlab` | any / none |
| `base_url` | omit (the managed instance) | required (e.g. `https://gitlab.tugraz.at`) | — |
| Where creds live | the system server's — nothing on the course | the **course's own** group token, on the binding | — |
| Course home | one Forgejo org per course | a GitLab group under `parent_group_id` | template archive only |
| Student access | forked repo + babysat clone token | student's own repo via their PAT | archive download, no repo |
| `delivery` | `git` | `git` | `download` |

- **In-system managed Forgejo** — the platform's own Forgejo, run as part of the stack. It
  auto-registers into the GitServer registry at startup, so a course just points at it with
  `provider: forgejo` (no URL, no credentials). Best default for new courses.
- **External GitLab** — an existing institutional GitLab. The course brings its own
  **parent group** (its course group is created underneath) and a **group access token**
  stored encrypted on the binding. Students bring their **own** GitLab PAT.
- **Download** — no per-student git; assignments are delivered as a template archive. Set
  `delivery: download`. Useful for lightweight or unbound courses.

## Data model

- **GitServer registry** — a global list of git servers (`type`, `base_url`, …), *not*
  scoped to an organization. Managed Forgejo self-registers; external GitLab instances are
  registered as **tokenless pointers** (no shared credential — the token lives per course).
- **CourseGitBinding** — one per course. Points at a `GitServer` and carries the
  course-specific bits: for GitLab, `parent_group_id` and an **encrypted** `token`
  (the group access token). Template/reference repo references live here too.
- **CourseMemberRepository** — the 1:1 mapping of a course member to their student repo.
  (A separate, older per-submission-group home under `submission_group.properties` still
  exists for team assignments.)

### The binding is immutable once materialized

A course's git binding **locks** as soon as it is materialized — i.e. once the template
repo has been created or any student repository exists. Renaming or repointing the template
after that orphans every student fork. So: **configure git at course creation**; there is
deliberately no casual "edit git" path afterwards. (Before materialization, the binding can
still be adjusted.)

## Configuring git

Two entry points. Both end in the same `CourseGitBinding`.

### 1. Manually (web UI)

- **On create** — the course-create page has a git step: pick the server (managed Forgejo or
  an external GitLab) and, for GitLab, the `parent_group_id` + group token.
- **Admin** — the git-servers admin UI manages the `GitServer` registry.
- Manual creation with **no** git config produces an **unbound** course; git can be
  configured later (while still unmaterialized).

### 2. From a deployment file

Deploying a course file — via **CLI** (`computor deployment`), **web upload**, or the
**VSCode** extension — sets up the git binding straight from the file. This is the
recommended path: the connection travels with the course definition.

The `git:` block on a course is a `CourseGitConfig`:

| Field | Applies to | Meaning |
|-------|-----------|---------|
| `delivery` | all | `git` (fork/clone) or `download` (archive). Default `git`. |
| `provider` | all | `forgejo` or `gitlab`. `forgejo` with no `base_url` = the in-system managed Forgejo. |
| `base_url` | GitLab | Server URL. Required for external GitLab; omit for managed Forgejo. |
| `parent_group_id` | GitLab | Parent group id/path the course group is created under. |
| `token` | GitLab | Group access token, stored **encrypted** on the binding. Supports `${ENV_VAR}`. |
| `template_repo` / `template_url` | optional | Explicit template ref/URL (auto-derived for managed servers). |
| `default_branch` | optional | Template default branch (defaults to `main`). |
| `student_repo_modes` | optional | Allowed hosting modes: subset of `['managed', 'external', 'download']`. |

Omit the whole `git:` block to create an **unbound** course.

**Portable reference.** A server is referenced by `provider` (+ `base_url` for external
instances), **not** by a machine-specific `git_server_id` UUID — so the same file deploys
across systems. At deploy time the backend resolves `(provider, base_url)` to the registry
server, creating a tokenless GitLab pointer if none exists yet.

**Token handling.** `${ENV_VAR}` in `token` is expanded **client-side** (by the CLI / web
uploader) before the request leaves — the backend receives the literal token, encrypts it,
and stores it on the binding. See [Credentials & security](#credentials--security).

### Example: in-system Forgejo

```yaml
course:
  name: "Programming 1"
  path: prog1
  git:
    provider: forgejo        # managed instance — no base_url, no token
    delivery: git
```

### Example: external GitLab

```yaml
course:
  name: "Programming 1"
  path: prog1
  git:
    provider: gitlab
    base_url: https://gitlab.tugraz.at
    parent_group_id: "12345"          # course group is created under this
    token: ${GITLAB_PROG1_TOKEN}      # group token; expanded client-side, stored encrypted
    default_branch: main
```

### Example: download-only

```yaml
course:
  name: "Intro Seminar"
  path: intro
  git:
    delivery: download                # template archive, no per-student repos
```

## Credentials & security

- **Forgejo** uses the system server's credentials. Students never handle a token: each gets
  a **babysat, per-user rotating clone token** minted on demand.
- **GitLab** uses the course's own **group access token** (on the binding) for
  server-side operations — creating the course group, template/reference repos, and forking
  student repos. Students authenticate with their **own** GitLab PAT (registered via the
  register-gitlab flow), which grants them access to their fork.
- **The group token is never exposed over the API.** It is encrypted at rest; its DTOs are
  **write-only** (you can set it, never read it back); read responses expose only a
  `has_token: bool`. Every decrypt happens server-side inside a workflow/activity. The
  template-archive endpoint streams bytes server-side without revealing the token.

## Deploy, release & student repos

- **"Release" == deploy to git.** There is no separate visibility flag — releasing an
  assignment means deploying its assigned example into the course's **template** repo.
  Trigger `POST /system/courses/{id}/generate-student-template` (`{}` = all pending;
  `{release: {course_content_ids}}` = specific). The
  `generate_student_template_v2` workflow is course-git-aware and finds pending content
  itself.
- The template deploy also populates the **reference** repo (README from the content index,
  solution files, `additionalFiles`, `mediaFiles`, and exposed `meta.yaml`/`test.yaml`).
- **Student repos are provisioned lazily** — on demand (e.g. the VSCode "Set up repository"
  action or first access), not eagerly on enrollment. On Forgejo the repo is forked and a
  babysat clone token issued; on GitLab it is forked using the group token and the student is
  granted access with their own PAT.

## Relevant endpoints

| Endpoint | Purpose |
|----------|---------|
| `PUT /courses/{id}/git` · `GET /courses/{id}/git` | Set / read the binding (read is token-free — `has_token` only). |
| `GET /user/courses/{id}/git` | Membership-gated, token-free binding view for a member. |
| `GET/POST/… /git-servers` | Manage the GitServer registry. |
| `POST /system/courses/{id}/generate-student-template` | Release: deploy template (+ reference). |

## See also

- Workflows powering this: [backend-patterns.md](backend-patterns.md#temporal-workflows).
- Deployment file formats (full-hierarchy vs. single-course upload): the `computor-types`
  deployment configs and [`ops/docs/`](../ops/docs/).
