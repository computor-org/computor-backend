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
