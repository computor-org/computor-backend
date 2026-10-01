# Public learning on computor.at

The `/learn` page and `GET /public/learning` expose a curated set of public
Python courses and links. Reading requires no account and triggers no server
execution. Learners can work in a hosted Coder workspace after signing in, on
their own computer with VS Code, or in a GitHub Codespace using their GitHub
quota. A full hosted pool leaves the other two paths available.

Verified, signed-in learners can join public courses, submit work, and ask Luna
in course messages. The public Luna worker uses a private TU Graz model service
and has no code execution capability. The public model quota and queue are
separate from existing TU teaching workers. Instructor solutions, credentials,
and private grading tests must never enter its context.

The extension keeps its existing publisher and ID and uses supported server
capabilities so one Marketplace version works with both 26.10 and main.
