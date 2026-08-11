# src/types — hand-written types

The rule across this repo: `src/X` is hand-written, `src/generated/X` is
generated (same split as `src/clients/` vs `src/generated/clients/`). The
code generators never write into this directory, and everything under
`src/generated/` is wiped on the next `bash generate.sh` run — so nothing
in here may be a copy of a backend DTO, and nothing generated may be edited.

What belongs here:

- **UI-only view models** with no backend counterpart (`auth.ts` — session
  shapes under HttpOnly-cookie auth).
- **Runtime constants** — codegen emits types only, never values
  (`AGENT_LIFECYCLE_GAVE_UP`, the `TaskStatus` enum components use as values).
- **Narrowings of untyped pydantic fields** — e.g. a `str` field the UI knows
  the literal values of (`TemplateRolloutState`), or a `Dict[str, Any]`
  progress payload with a known structure (`CoderTaskProgress`).
- **Re-required response fields** — codegen marks a field optional because the
  pydantic field has a default, although the endpoint always serializes it.

Narrowings must be built **on top of** the generated type
(`Gen & {...}` or `Omit<Gen, 'field'> & {...}`, aliasing the generated name
via `import type { X as GenX } from 'types/generated'`) — never as
free-standing mirrors, so every other field change flows in automatically.
Use `Omit` whenever a field's type changes; the bare intersection is only for
re-requiring a field of the same type.

When a hand-written type gains a full generated counterpart, re-export it and
delete the local copy (`export type { X } from 'types/generated'`) — see the
consent types and `WorkspaceRoleAssign` for the precedent. If a whole module
of DTOs is missing from `types/generated`, the fix is a category branch in
`computor-backend/src/computor_backend/scripts/generate_typescript_interfaces.py`
plus a regeneration, not a new mirror here.
