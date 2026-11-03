# Privacy notices (GDPR consent policy versions)

This directory holds the **privacy-notice / consent policy versions** that back
the consent gate (`computor-backend` `middleware/consent.py`). It sits parallel
to `data/deployments/`. On startup the backend publishes every version
directory here that is not yet in the database (write-once, so re-runs are a
no-op); `CONSENT_BOOTSTRAP_ENABLED=false` turns that off, and `CONSENT_DIR`
points it at another directory. A notice can also be published by an admin in
the web UI: **System → Privacy notices → Publish**.

Publishing calls `POST /consent/policy-versions` (admin), which uploads the Markdown
to MinIO (`policies/{version}/{lang}.md`) and inserts an **append-only** row.

## Layout

One directory per version. The directory name is the default version string.

```
data/consent/
  2026-07-05/
    policy.yaml        # optional metadata (see below)
    en.md              # the notice, one Markdown file per language ({lang}.md)
    de.md
```

### `policy.yaml` (all fields optional)

```yaml
# version: "2026-07-05"     # defaults to the directory name if omitted
effective_from: null         # null / omitted = becomes current immediately (now).
                             # An ISO datetime in the FUTURE schedules the version.
# languages: [en, de]        # defaults to every {lang}.md present in the directory
```

### Language files

Each `{lang}.md` is the full Markdown privacy notice for that language code
(`en.md`, `de.md`, …). At least one is required. `README.md` is ignored.

## Rules & cautions

- **Append-only / write-once.** A `version` can be published exactly once; the
  server rejects re-publishing an existing version. To change the text, publish
  a **new** version (e.g. bump the date). Users must re-consent after a bump.
- **Publishing gates users.** With `effective_from <= now`, every user who has
  not consented to the new version is redirected to `/consent` on their next
  request (within the ≤300 s cache TTL). Bump only for material changes.
- **Legal basis / wording** must match the policy text — see
  `docs/consent-gate.md` before publishing a version.
