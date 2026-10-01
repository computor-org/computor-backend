# Course assistant policy and public learning

License: CC BY 4.0. Attribution: Computor contributors, TU Graz. Code examples
are also available under the repository's MIT license.

Computor supplies task context and teaching guidance to Hackl. Hackl owns chat,
provider selection and model transport. Learner provider keys stay in VS Code
SecretStorage; Computor authentication credentials are separate. Background
review through computor-agent remains a separate authenticated service.

## Course configuration

Course and course-content JSONB properties accept `assistant_policy`. Course
content can override individual fields; unspecified fields inherit from the
course. An absent stored policy returns `null` for legacy compatibility. The
current extension applies the agreed Ask-only default to legacy courses.

```json
{
  "properties": {
    "assistant_policy": {
      "action_mode": "ask",
      "completion": "off",
      "independent_check": false
    },
    "assistant_guidance": "Ask about the units and the axis labels before suggesting changes."
  }
}
```

`PUT /courses/{id}` accepts a property patch using the existing course update
permissions. Unrelated property keys and unspecified policy controls survive
the patch. Explicit `assistant_policy: null` removes the stored policy. Course
content updates support partial overrides. Teaching guidance is limited to 8,000
characters; content guidance overrides course guidance. Guidance is visible to
the learner and their chosen model: never put instructor reference solutions,
private grading material or credentials in it.

Updating the `gitlab` repository configuration requires a course maintainer or
higher authority, matching the permission boundary for public enrollment.

Student list/detail and course-content detail responses add nullable
`assistant_policy` and `assistant_guidance`. The policy resolves to all three
controls. Existing authentication, submission, test and grading APIs are unchanged.
Course edits invalidate the existing course/student/tutor view caches.

| Control | Values | Course default |
| --- | --- | --- |
| action_mode | ask, edit, work, agent | ask |
| completion | off, single-line, multi-line | off |
| independent_check | boolean | false |

Hackl enforces action ceilings independently of completion. Independent check
disables every generation surface. Yolo, MCP and external agent backends cannot
bypass a host course policy. Invalid policies disable generation. Policy/context
changes abort active requests and clear conversation and attached context.

The editor is controlled by its learner. These controls support teaching; they
do not establish a secure examination environment or guarantee a model's prose.
Assessment rules require controls in the assessment environment as well.

## Public interfaces

`GET /public/courses` returns the published, visible, non-archived course catalog
without member data. `GET /public/learning` returns curated public course,
Marketplace, Codespaces and guide links. It has no database/storage dependency,
does not fetch a caller-supplied URL, and accepts no mutation method. Unknown query
strings cannot change the repository or select a file. Its response is cached for
300 seconds. Public material is served from the reviewed public repository;
instructor solutions and private tests are not published there.

`/learn` and landing-page links work without login even when the catalog backend
is unavailable. A workspace launch failure offers desktop VS Code and Codespaces.
Reading public material does not authorize enrollment, submissions, jobs, hosted
workspace creation or server execution. Those operations retain their existing
authentication and permission checks. Public server admission must also satisfy
the deployment's untrusted-execution security gate.

## Runtime and AI choices

Desktop VS Code can execute code on the learner's computer and connect Hackl to a
local model endpoint or external HTTPS provider. GitHub Codespaces executes code
in the learner's GitHub account and uses an external provider with their own key.
The public devcontainer pins its base image and hash-locks Python dependencies.
Hackl's managed inference engine is disabled in Codespaces and does not auto-start
there. No course or devcontainer contains shared inference credentials.

The learner explicitly approves sending context to an external endpoint. Provider
keys require HTTPS outside loopback. Keep institutional remote model transport
encrypted, for example through HTTPS or an SSH tunnel to a loopback endpoint.
Codespaces and AI provider quotas/billing belong to the learner's accounts.

Plot review accepts explicitly selected PNG/JPEG images, with a 2 MB limit per
image and three images per request. Remote image URLs and active SVG content are
rejected. A vision-capable model gives feedback on axes, units, numerical meaning
and presentation; this feedback is separate from server grading and instructor
assessment. Course tool calls are bounded to eight per turn.

## Release compatibility

The same `computor-org.computor` Marketplace extension version 2027.3.0 supports
the 26.10 and main/27.3 backends. Nullable/new policy fields are additive. Old DTOs
use Ask-only without calling a nonexistent new backend endpoint. Missing Hackl
does not block repository setup, tests or submissions. Updating Hackl supplies
the optional course-policy and figure-review API; it is not a mandatory extension
dependency. Stable `release/2026.10` and code.tugraz.at remain separate from the
public main deployment.

## Verification

Use synthetic accounts and assignments. Cover old DTOs, policy inheritance,
partial updates, malformed policy, forbidden model tool requests, MCP, completion,
independent check, cancellation, logout and course changes. Public browser tests
must run without credentials and with an unavailable backend. Verify anonymous
mutation/execute denial separately from public reads. Record runtime, image and
commit evidence before enabling broader server admission.
