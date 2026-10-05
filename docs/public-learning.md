# Public learning on computor.at

`/learn` is the anonymous, first-party course reader. Course discovery comes
from `GET /public/courses`; a reader then loads
`GET /public/courses/{course_id}/outline` and
`GET /public/course-contents/{content_id}`. The web app renders the pedagogical
unit/exercise hierarchy, descriptions, media and language variants without
sending learners to a repository browser. GitHub is provenance and reuse
information only.

The public reader applies the same visibility/release rules as the student
view, plus `Course.public` and archive checks. Assignment Markdown is read only
from the deployed example's top-level `content/index*.md` or `README*.md`
files. Public media is restricted to `content/mediaFiles/**`. The projection
never returns repository credentials, reference solutions, local tests,
submission data or instructor-only files. Reading requires no account and
triggers no server execution.

A course opens on an explicit welcome/start content item when one exists.
Until such an item exists, the reader shows the course description and a clear
link to the first released exercise. Learners can then sign in to join the
course or work in a hosted Coder workspace, local VS Code, or GitHub Codespaces.

For a public deployment with Coder enabled, set
`CODER_MAX_RUNNING_WORKSPACES=30`. The API refuses hosted creation/start when
this positive limit or the verified workspace cgroup is missing. It counts all
running and starting containers, including staff workspaces, separately from
the existing distinct-user limit. Concurrent launches use a Postgres
transaction lock to compare a complete Coder fleet inventory with durable
reservations before calling Coder. Reservations have no guessed timeout,
because a queued build can outlive one. A new active or terminal Coder build
reconciles its reservation. If a launch failed before Coder created a build,
an operator must compare `public_workspace_reservation` with the Coder fleet,
verify no matching build remains queued, and remove only that stale row. For
example, after confirming that `alice/vscode` has no pending build, delete
only that row with `DELETE FROM public_workspace_reservation WHERE
owner_name='alice' AND workspace_name='vscode';`. Database and Coder failures
refuse new launches, leaving local VS Code and Codespaces available.

Verified, signed-in learners can join public courses and submit work. Once
`PUBLIC_LUNA_ENABLED=true` and the restricted worker are deployed, an assignment
page also shows a short Ask Luna form. A learner sends a question and selected
code or result text; the backend adds only the visible assignment description.
It does not fetch repositories, reference solutions, hidden tests, or other
learners' work. Existing course messages remain a separate teaching channel.

The backend admits at most 10 requests per account in a rolling hour, 30 in a
rolling day, one outstanding per account, 20 waiting globally, and four active.
Requests expire after 15 minutes; a completed answer remains available to its
author for 24 hours. Queue operations are atomic in Redis and fail closed if
Redis is unavailable. The worker pulls jobs over HTTPS, sends them through the
restricted `luna-public` Slopgate credential to batched Qwen on faepmac2, and
posts one answer. It has no general Computor API token, inbound listener, tool
bridge, or code execution capability. Before enabling it, verify that the
model host writes no content logs.
Luna availability is off by default and the UI hides the form until enabled.

The extension keeps its existing publisher and ID and uses supported server
capabilities so one Marketplace version works with both 26.10 and main.
