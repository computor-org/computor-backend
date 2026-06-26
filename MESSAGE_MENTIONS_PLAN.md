# Message Mentions — Implementation Plan

Branch (all three repos): **`feat/message-mentions`**, cut from `release/2026.10`
(`computor-agent` cuts its `release/2026.10` from `main`).

## Goal

Let a message **mention a user**, creating a real `user ↔ message` relation. A mention is
only allowed if the mentioned user can actually *see* the message (visibility depends on the
message's scope). Mentions power two things from one mechanism:

- **Human mention** → a notification (feeds the existing notification bell).
- **Agent-user mention** → *activation*. The tutor AI is a user in the system; mentioning it
  activates it. This **replaces** the legacy `#ai` hashtag trigger in `computor-agent`.

The mention gate ("can only mention someone who can see the message") and the agent's
activation reach ("only activates where it has access") are the **same rule**.

## Locked decisions

1. **Hashtags** — *not* promoted to a table. The only consumer of message hashtags is the
   agent's `#ai` trigger; once activation moves to mentions, the regex tag filter
   (`interfaces/message.py`) is left in place but unused (harmless), and the agent drops its
   `#ai` / `#ai-response` dependence. No tag table, no migration, no backfill.
2. **Mentions are users picked from a dropdown — never typed handles.** No nicknames, no git
   handles, no `User.username` (there is none). On opening the message view the client
   **pre-fetches the mentionable users** (= the message scope's audience), and `@` opens a
   dropdown completing on **`{given_name} {family_name}`**. Selection stores the **`user_id`**.
3. **Gating** — backend rejects (HTTP 422) any mention whose `user_id` is not in the message's
   audience (defense-in-depth; the dropdown already prevents it, but API clients / stale ids
   get caught). Same for an unresolvable id.
4. **Parse from `content` only.** The title stays the legacy `#tag` carrier; mentions live in
   the body.
5. **Sequencing** — agent activation is the headline; human mention-notifications ride along
   as a fast-follow.

## Wire format

A mention is stored inline in `content` as a Markdown-link-like token:

```
@[Given Family](<user_id>)
```

- `<user_id>` (a UUID) is **authoritative**; the bracketed name is a human-readable cache.
- Clients re-render the **current** name from the `mentions[]` the API returns (renames never
  go stale); raw content stays readable (good for notifications and the agent's LLM prompt).
- Extraction regex (backend): `@\[[^\]]*\]\(([0-9a-fA-F-]{36})\)` → capture group = `user_id`.

## Backend (`computor-fullstack`)

### Data model — `message_mention`
New table (in `model/message.py`, alongside `MessageRead`):

| column | type | notes |
|--------|------|-------|
| `id` | UUID pk | `uuid_generate_v4()` |
| `message_id` | FK `message.id` ON DELETE CASCADE | |
| `mentioned_user_id` | FK `user.id` ON DELETE CASCADE | |
| `created_at` | timestamptz | |

- `UNIQUE(message_id, mentioned_user_id)` — one row per (message, user).
- `INDEX(mentioned_user_id, message_id)` — the "mentions of me" fast path.
- `Message.mentions = relationship('MessageMention', back_populates='message', cascade='all, delete-orphan')`.
- Alembic migration `down_revision = 'a7f3b1c9d2e8'` (current head — verify with `alembic heads`, not grep: the repo mixes `revision = '…'` and `revision: str = '…'` header formats). No backfill.

### Audience resolver — `permissions/message_audience.py` (new)
The canonical **inverse** of `MessagePermissionHandler.build_query` (`handlers_impl.py:898-1084`):

- `is_user_in_audience(db, targets, user_id) -> bool` — the write-time gate.
- `eligible_mentionable_users(db, targets, search=None, limit=50) -> list[User]` — the
  dropdown source (returns `id, given_name, family_name`).

Per-scope audience (mirror of the read handler; staff floor = `_tutor`):

| scope | audience |
|-------|----------|
| `user` | recipient + author |
| `course_member` | that member + course staff `_tutor`+ |
| `submission_group` | group members (`SubmissionGroupMember`) + staff `_tutor`+ |
| `course_group` | group members + staff `_tutor`+ |
| `course_content` | any course_member of the course |
| `course` | any course_member |
| `course_family` | family role `_developer`+ or any course_member in the family (cascade) |
| `organization` | org role `_developer`+ or any course_member in the org (cascade) |
| `global` | everyone — autocomplete is search-only; v1 may restrict |

A unit test cross-checks `is_user_in_audience` against `MessagePermissionHandler` on fixtures
per scope so the two can't drift.

### Write flow (`business_logic/messages.py`, create + update)
After existing write-permission checks:
1. `extract_mentions(content)` → list of `user_id`s.
2. For each, `is_user_in_audience(...)`. Unknown / not-in-audience → collect.
3. If any collected → raise 422 with `{unresolved: [...], not_permitted: [...]}`.
4. Else upsert `message_mention` rows; on update, reconcile (delete gone, insert new).
5. Emit a mention event per mentioned user (notification + agent activation signal).

### Fetch (mirrors tag ergonomics; always composed with `MessagePermissionHandler`)
- `MessageQuery`: add `mentioned_user_id: Optional[str]`, `mentions_me: Optional[bool]`
  (filter via EXISTS/join on `message_mention`).
- `MessageGet` / `MessageList`: add `mentions: List[MessageMentionRef]`
  (`{id, given_name, family_name}` — same shape as `MessageAuthor`).
- New `GET /messages/mentionable-users?<scope target ids>&search=&limit=` → eligible users.
  Pre-fetch fully for small scopes; server-side `search` for large (course/family/org/global).

### Threading / follow-up
Unchanged structurally; replies inherit scope, mentions in replies gate against the inherited
target. "Follow-up activation" (continue pinging the agent in a thread without re-mention) is an
agent-side rule (below), supported by the existing thread endpoint.

### Types (`computor-types`)
Add `MessageMentionRef`; extend `MessageGet/List/Query`; regenerate TS for web + extension.

## Extension (`computor-vsc-extension`)
- Regenerate `src/types/generated/messages.ts`; add `getMentionableUsers()` + the two mention
  filters to `ComputorApiService`.
- `webview-ui/messages-input.js`: **inline `@` autocomplete** (the extension's first) scoped to
  the compose target/thread; insert a highlighted token; pre-fetch on open.
- `webview-ui/messages.js`: render `@mentions` as highlighted chips; add a "Mentions me" filter.

## Agent (`computor-agent` — base branch from `main`)
- Learn its **own `user_id`** at startup (`GET /user` / `/auth/me`).
- **Activation**: poll `GET /messages?mentions_me=true&unread=true` (or a mention WS event)
  instead of `tags=["ai"]`.
- **Self-exclusion** by `author_id == own id` (drop the `#ai-response` title tag).
- **Follow-up**: keep responding in threads it participates in (authored / mentioned in root).
- Ensure the agent user has a real display name (e.g. `given_name="AI"`, `family_name="Tutor"`)
  so it appears in the dropdown; substitute mention tokens → names before the LLM prompt.
- LLM layer (OpenAI-compatible) untouched.

## Phases
1. **Backend data layer** — model + migration + schemas. ← starting here
2. **Backend logic** — audience resolver + gate + write flow + cross-check test.
3. **Backend API** — fetch filters + `mentionable-users` endpoint + `mentions[]` enrichment.
4. **Extension** — types, API client, `@` autocomplete, highlight rendering.
5. **Agent** — identity + mention-based activation + follow-up.
