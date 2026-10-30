# Lena and course-message mentions

Learners can type or paste `@lena`, `@luna` or `@ai` in an assignment message,
or select Lena from the `@` autocomplete dropdown. All three handles resolve
to the same existing tutor account. The display name is Lena; `@luna` remains
a supported legacy alias. Multiple handles in one message produce one stored
recipient, so they do not create duplicate tutor jobs.

## Deployment

Set `TUTOR_AGENT_USER_ID` in the backend environment to the UUID of the
**existing** course-message tutor user. The production Compose configuration
forwards this setting. Do not create a replacement user or change the worker's
authenticated identity, memberships, permissions or credentials.

Use the administrator Users API to rename that user's `given_name` to `Lena`
(`PATCH /users/<existing-user-id>` with `{"given_name": "Lena"}`). Retain its
family name unless the deployment intentionally changes its display label.
The mentionable-users endpoint supplies the canonical Lena name and the three
aliases for the configured identity, even while an older account label is
being migrated. Existing UUID mentions labelled Luna continue to resolve.

Deploy the backend before the extension update. Without a configured tutor
identity, reserved tutor handles stay ordinary text rather than selecting a
same-named human. The public Ask Lena form uses a separate restricted worker;
its existing enable flag and credentials remain applicable.

## Routing unaddressed messages to Lena

A course can send every student message that mentions nobody to Lena. The
setting is `tutor_agent_auto_route` on the course (default off), offered as a
checkbox when a course is created in the web UI and on its edit page; it is
also part of `CourseCreate` / `CourseUpdate`.

When it is on, a new message gets a visible `@[Lena](<tutor id>)` prepended if
all of these hold: `TUTOR_AGENT_USER_ID` is set and that user is active, the
author is a `_student` of the course, the content (after plain-name resolution)
mentions nobody, the message is not a reply to Lena (her follow-up handling
already covers those), and Lena is in the message's audience. From there it is
an ordinary mention, so the worker needs no change. Edits are never rewritten.

Lena must be a course member for the audience gate to accept her; add the
tutor account to the course as `_tutor`.

## Unit description drafts

Lecturers can ask Lena for a draft description of a unit, written from the
assignments in it (computor-org/issues#559). The draft is only shown to the
lecturer; nothing is saved until they save it.

| Route | Who |
|---|---|
| `GET /course-contents/description-drafts/availability` | anyone signed in |
| `POST /course-contents/{id}/description-draft` | `_lecturer` or higher in the course |
| `GET /course-contents/description-drafts/{job_id}` | the lecturer who asked |
| `DELETE /course-contents/description-drafts/{job_id}` | the lecturer who asked |
| `POST /course-contents/description-drafts/worker/claim` | the tutor agent only |
| `POST /course-contents/description-drafts/worker/complete/{job_id}` | the tutor agent only |

The content must be a unit (its kind has descendants) with at least one
assignment that is not archived. The backend builds the job: the unit's title
and description, the course title, and for each assignment in tree order its
title, content type and the student-visible `content/index*.md` of the
assigned example version, filtered like the student description download
(never `meta.yaml`, `test.yaml`, tests or solutions). Texts are shortened to
fit 40,000 characters per job. No student or lecturer data is included.

Languages default to every `index_<lang>.md` the assignments have (at most
four, the course language first), otherwise the course language, otherwise
English. Drafts come back per language, at most 4096 characters each (the
description column's size).

The queue is the public Lena queue under its own Redis keys
(`description_draft:v1`): one pending draft per lecturer, 20 per hour and 60
per day, results kept for an hour. `DELETE` drops the lecturer's job, queued,
running or finished, and frees their pending slot at once; a worker still
writing it gets 409 on completion. It answers 204 for any job id, so it
reveals nothing about other lecturers' jobs.

The feature is offered (availability `enabled: true`) only while
`TUTOR_AGENT_USER_ID` names an active user and a worker is there: it has
claimed within the last 90 seconds, which a `computor-agent` with unit
descriptions enabled does every few seconds while idle, or it holds a draft
job whose lease has not expired, which covers a long draft.

## Resolution rules

The backend resolves new messages, replies and edited content before
persisting mention relations. The worker continues to query `mentions_me` and
recognize follow-ups by user ID. Only active users in the message audience
can be resolved; aliases do not grant access or add course membership.

An exact, unique human given/family name also resolves when sent. Ambiguous
human names return an error asking the learner to choose from autocomplete.
Unknown names remain visibly unlinked text. Autocomplete lists the configured
tutor first; humans with the same name remain selectable. Autocomplete results
are not used to infer uniqueness; the backend queries exact names against the
full audience.

Code blocks, inline code, email addresses, URLs such as
`https://medium.com/@ai`, escaped `\@lena` and longer names such as
`@lenabelle` stay literal text. Ctrl/Cmd+Enter sends, even with the
dropdown open; plain Enter or Tab can select its highlighted candidate.

## Internal compatibility names

The public-worker module, `/public-luna` routes, `X-Public-Luna-Worker-Key`
header, `PUBLIC_LUNA_*` environment variables, `luna-public` gateway alias,
launchd service identifiers and browser storage keys retain their existing
names. They are internal compatibility contracts, not the displayed tutor
name. Renaming them independently would break installed workers or clients.
