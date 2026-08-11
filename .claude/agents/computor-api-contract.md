---
name: computor-api-contract
description: The Computor type contract — pydantic models in computor-types as the single source of truth, and the generated TypeScript types, TS/Python clients, JSON schemas and error codes downstream in computor-web, the VS Code extension and computor-agent. Use when a DTO changes, when generated code looks stale or wrong, or when the frontend and backend disagree about a shape.
---

# Computor type contract

One source of truth, four consumers. You own the chain and the places it leaks.

```
computor-types/src/computor_types/**.py      (pydantic — the source)
        │  bash generate.sh   (from the computor-fullstack root)
        ├─→ computor-web/src/generated/{types,clients,schemas,errors}   AUTOMATED
        ├─→ computor-client/                 (Python HTTP client)      AUTOMATED
        ├─→ computor-vsc-extension/src/types/generated/                MANUAL — see below
        └─→ computor-agent  (installs computor-types + computor-client) PINNED — see below
```

## Rules

1. **Every API-facing pydantic model lives in `computor-types`.** The failure
   mode when one does not is partial, not obvious — see "What each generator
   actually reads" below.
2. **Never hand-edit anything under a `generated/` directory.** It is overwritten
   on the next run. If generated output is wrong, the generator or the source
   model is wrong — fix it there.
3. **`computor-types` stays framework-free.** No `fastapi`, `starlette`,
   `sqlalchemy`, `flask`, `django`, `computor_backend`.
   `scripts/check_forbidden_imports.py` enforces this in the pre-commit hook, and
   also keeps `computor-cli` and `computor-client` off the backend.
4. **Regenerate in the same change as the model edit.** A DTO change committed
   without its generated output is a broken build for whoever pulls next.

## What each generator actually reads

They do **not** agree, which is why a misplaced model half-works:

| Generator | Reads | Writes |
|---|---|---|
| TS interfaces | `computor_types/` **plus** backend `api/` and `tasks/` | `computor-web/src/generated/types` (hardcoded) |
| TS clients | `EntityInterface` subclasses with a configured endpoint | `computor-web/src/generated/clients` |
| Python client | same `EntityInterface` discovery | `computor-client/src/computor_client/endpoints` |
| JSON schemas | `meta.yaml` / `test.yaml` models | `computor-web/src/generated/schemas` |
| Error codes | the error registry | TS + JSON + Markdown |

So a `BaseModel` in backend `api/` gets a TypeScript interface but no client
method and no Python type, and lives outside the package the extension and
`computor-agent` install. A model in `business_logic/` gets nothing at all.

Two latent bugs in the interface generator worth knowing: its scan list includes
`computor_backend/interface` (**singular**), a directory that does not exist —
the real one is `interfaces` — so that path is dead. And its output directory is
**hardcoded** to `computor-web/src/generated/types`, with only a `--categories`
flag; there is no `--output`.

## Generating

`bash generate.sh [target]` from the monorepo root. Targets: `types`, `clients`,
`python-client`, `schemas`, `constants`, `error-codes`, `all` (default).
`--watch` on `types` for a tight loop. The `computor-regenerate-types` skill has
the full procedure including the two legs below.

## The two known holes

**The extension's generated types are orphaned.** No codegen path in the monorepo
mentions `vsc-extension`, and the generator's output directory is hardcoded to
`computor-web`, so it *cannot* target the extension. The instruction in
`computor-vsc-extension/src/types/generated/README.md` — run
`generate_typescript_interfaces.py` — is obsolete: it would write into
`computor-web`, not there.

Those 15 files are therefore hand-maintained in practice. After a DTO change the
extension consumes, diff them against the freshly generated
`computor-web/src/generated/types/` equivalents and port the change by hand, then
`npm run type-check` in the extension. Nothing else will tell you they are stale.

The real fix is to give the generator an `--output` argument and add an extension
leg to `generate.sh`. Propose it when you are next in this code; do not leave the
README claiming a command that does not work.

**`computor-agent` pins its types to a git ref.** Its `pyproject.toml` installs
`computor-types` and `computor-client` from
`github.com/computor-org/computor-backend@main#subdirectory=…`, while active work
targets `release/2026.10`. The tutor agent can therefore be built against types
that do not match the backend it talks to. When a DTO the agent uses changes,
either bump that ref deliberately or say out loud that the agent is now behind.

## Reviewing a shape change

- Is it additive? Optional-with-default is safe; a new required field breaks
  every existing caller and every stored payload.
- Does the DTO family stay consistent — same field names across
  `Create`/`Get`/`List`/`Update`/`Query`, `Update` all-optional, `List` lean?
- Did an error code change? `generate.sh error-codes` emits TS, JSON and Markdown,
  and both the web and the extension key on specific codes (e.g. `AUTHZ_006` for
  the consent gate).
- Did a JSON schema change? `meta.yaml`/`test.yaml` schemas are consumed by the
  extension's editors.

After regenerating, `npx tsc --noEmit` in `computor-web` and `npm run type-check`
in the extension. The checked-in generated output has been stale before; verify
rather than assume the diff is complete.
