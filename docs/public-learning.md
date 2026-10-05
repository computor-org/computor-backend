# Public learning on computor.at

`/learn` is an anonymous, first-party static course reader. It reads generated
JSON and raster images under `/learning/`; it makes no API or GitHub requests.
This feature adds no anonymous API endpoints or runtime database/storage access.
The web app renders the course hierarchy, descriptions, math and DE/EN variants.
GitHub is optional provenance and reuse information.

Every frontend `yarn build` regenerates the bundle from the public mirror pinned
in `computor-web/learning-source.json`. The build downloads that exact commit
and checks the archive SHA-256 before extraction. Updating course content means
reviewing the new public revision, updating both pins and rebuilding. A failed
download or checksum mismatch stops the build; deployed content stays available.

The generator selects only the three reviewed Python manifests, public
`content/index*.md`/`README*.md` descriptions and referenced PNG/JPEG/GIF/WebP
images whose signatures match. It rejects symlinks, traversal and oversized
files, and omits hidden/archived/unreleased branches. It never copies solutions,
tests, submissions, credentials, metadata authors or arbitrary example files.
Only publish source content approved for anonymous reading; the bundle is a
snapshot and does not follow later database visibility changes until rebuilt.

Raw HTML, external/inline images and SVG are not rendered. KaTeX disables trusted
commands and bounds expansion. Static assets carry nosniff and a sandboxed CSP.
The public mirror currently refers to an absent pendulum image; its alt text is
shown rather than fetching an unpublished file.

The reader can deploy by replacing only the frontend image. No database
migration, API/worker restart or workspace-template rebuild is required.

Run the publication checks with `yarn test:public-learning` and the browser
checks with `yarn test:e2e e2e/public-learning.spec.ts --workers=2`. After
deployment, repeat the same browser checks with `E2E_BASE_URL=https://computor.at`
to verify the actual public site without starting a local server. These checks
read public pages and check rejected write methods only on the static catalog.

The Next 16.3.6 standalone server denies unsupported static-file methods with
`Allow: GET, HEAD`, but its default 405-page rendering currently throws
`NoFallbackError` and returns 500. Development returns 405. The production
checks accept this known rejection only with the read-only Allow header and
unchanged file bytes; successful writes always fail verification. Reproducer:
POST/PUT/PATCH/DELETE `/learning/catalog.json` in the network-isolated image.
The framework response-rendering repair belongs upstream; no dependency patch
or application workaround is included here. Recheck this focused case on the
next supported Next upgrade and restore the exact 405 expectation when fixed.

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
