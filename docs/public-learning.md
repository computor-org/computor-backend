# Public learning on computor.at

The `/learn` page and `GET /public/learning` expose a curated set of public
Python courses and links. Reading requires no account and triggers no server
execution. Learners can work in a hosted Coder workspace after signing in, on
their own computer with VS Code, or in a GitHub Codespace using their GitHub
quota. A full hosted pool leaves the other two paths available.

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
