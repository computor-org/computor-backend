# Public learning on computor.at

The `/learn` page and `GET /public/learning` expose a curated set of public
Python courses and links. Reading requires no account and triggers no server
execution. Learners can work in a hosted Coder workspace after signing in, on
their own computer with VS Code, or in a GitHub Codespace using their GitHub
quota. A full hosted pool leaves the other two paths available.

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
