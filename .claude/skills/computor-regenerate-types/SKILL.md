---
name: computor-regenerate-types
description: Regenerate the Computor generated code — TypeScript types and clients, the Python client, JSON schemas, constants and error codes — after changing a pydantic model in computor-types. Use whenever a DTO changes, or when generated output looks stale or disagrees with the backend.
---

# Regenerating Computor's generated code

Run from the **computor-fullstack root**. The venv is handled by the script.

```bash
bash generate.sh              # everything (default)
bash generate.sh types        # TS interfaces (+ error codes unless --no-error-codes)
bash generate.sh clients      # TS API clients
bash generate.sh python-client
bash generate.sh schemas      # meta.yaml / test.yaml JSON schemas
bash generate.sh constants
bash generate.sh error-codes
bash generate.sh types --watch
```

## After running, always

```bash
cd computor-web && npx tsc --noEmit
```

The checked-in generated output has been stale before. A clean `generate.sh` run
is not proof the result compiles.

## The two legs `generate.sh` does not cover

**1. The VS Code extension.** `computor-vsc-extension/src/types/generated/` is
**not** reachable by the generator — its output directory is hardcoded to
`computor-web`, and the README in that folder documents a command that no longer
does what it says. If the DTO you changed is consumed by the extension:

```bash
# diff the freshly generated web types against the extension's copy
diff computor-web/src/generated/types/<category>.ts \
     ../computor-vsc-extension/src/types/generated/<category>.ts
```

Port the change by hand, then in the extension repo:

```bash
npm run type-check
```

**2. `computor-agent`.** It installs `computor-types` and `computor-client` from
`github.com/computor-org/computor-backend@main`, not from your working tree. A
local regeneration does not reach it. If the agent consumes the changed shape,
either bump that ref in its `pyproject.toml` deliberately or state plainly that
the agent is now behind.

## Rules

- **Never hand-edit a file under a `generated/` directory** in `computor-web` or
  `computor-client` — it is overwritten on the next run. Wrong output means the
  source model or the generator is wrong.
- The extension's `src/types/generated/` is the one exception, because nothing
  regenerates it. Say so in the commit message when you edit it by hand.
- Commit the regenerated output **with** the model change. Splitting them leaves
  a broken build for whoever pulls in between.
- Adding an entity means adding its `EntityInterface` — the TS and Python client
  generators discover endpoints that way, so a DTO without one produces types
  but no client methods.

## Sanity checks

```bash
python scripts/check_forbidden_imports.py    # computor-types stays framework-free
python scripts/check_dto_location.py         # no API-facing model outside computor-types
git status --short computor-web/src/generated computor-client
```

If `git status` shows *nothing* after a model change, the generator did not see
your model — check it is exported from a module the generator scans, and that it
is reachable from an `EntityInterface`.
