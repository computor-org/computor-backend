# Self-Update

One-click system updates from the admin UI (**System → Updates**), or from the
CLI (`./computor.sh update`). The system compares its running git commit with
the tip of a configured repository branch; an admin can then trigger an update
that serves a maintenance page, checks out and builds the new version, restarts
the stack, and automatically rolls back code if the new version fails its health
check. A Keycloak version change needs explicit recovery instead: Keycloak
database migrations cannot be undone by reverting its image.

## Configuration (.env)

```bash
UPDATE_ENABLED=true                # opt-in; adds the updater sidecar in prod
SYSTEM_REPO_URL=https://github.com/computor-org/computor-backend.git
SYSTEM_REPO_BRANCH=main            # branch this deployment tracks
SYSTEM_REPO_TOKEN=                 # only for private repos (see Security)
# UPDATE_GIT_FORCE=true            # allow `git reset --hard` on a dirty tree
```

The availability *check* works everywhere (also in dev). The update *executor*
is production-only: in dev the API and frontend run on the host, so there is
nothing the updater could restart — the UI shows the check but the button stays
disabled.

## How an update runs

Triggering (`POST /system/update`, admin-only) only queues a request in Redis;
the **updater sidecar** (a small always-on container with the docker socket and
the repo bind-mounted) picks it up and launches a detached **runner** container
*outside* the compose project — so stopping/recreating stack services can never
kill the process driving the update. The runner executes `ops/lib/update.sh`:

1. **preflight** — refuse if recovery is pending, or on a dirty working tree
   (unless `UPDATE_GIT_FORCE`).
2. **fetch + checkout** — `git fetch $SYSTEM_REPO_URL $SYSTEM_REPO_BRANCH`,
   checkout `FETCH_HEAD`. Then `docker compose config -q` against the *new*
   tree: a broken compose config (e.g. a new required variable missing from
   your `.env`) aborts here, **before any downtime**, and reverts the checkout.
3. **build** — all images are built while the old version is still serving.
4. **maintenance** — Redis maintenance flag + Traefik catch-all to the static
   maintenance page; every service stops except `traefik`, `static-server`,
   `redis`, `socket-proxy`, and the `updater` itself.
5. **Keycloak guard** — refuse a downgrade. For an upgrade, verify Keycloak has
   stopped, take a host-persistent database dump, and persist a recovery marker
   before the new version can migrate the database.
6. **start + health check** — `compose up -d` (migrations run on API boot),
   then the API and frontend are polled for up to 5 minutes each. A Keycloak
   upgrade also checks Keycloak readiness and the resulting schema version.
7. **success** — recovery state is cleared, maintenance ends, state `success`.
   **Failure** → **automatic rollback**: checkout of the previous commit,
   rebuild (cache-fast), restart, health check → state `rolled_back`. If even
   the rollback fails, the maintenance page **stays up**, state is `failed`,
   and the error in the UI / `./computor.sh update status` tells you how to
   recover (typically `./computor.sh maintenance exit prod` after fixing).
   After a Keycloak upgrade, code rollback is refused and **explicit recovery**
   is required instead.

Progress is written to Redis (`update:state`, `update:log`), so the admin page
can narrate the run even while the API itself is down (the page keeps polling
and resumes automatically).

## Scheduled updates

`POST /system/update/schedule` (admin-only, also on the admin page) stores a
one-shot schedule in Redis; `DELETE /system/update/schedule` cancels it. The
**sidecar** fires it: each 30 s loop iteration it compares `date -u +%s`
against the stored epoch and, when due, performs exactly the manual trigger's
enqueue (lock → `update:state` → `update:queue`). The API pre-computes
`scheduled_at_epoch` so the sidecar never parses ISO datetimes.

Redis keys:

- `update:schedule` — hash: `scheduled_at` (ISO8601), `scheduled_at_epoch`,
  `scheduled_by`, `scheduled_by_name`, `created_at`. No TTL; persists until
  fired or cancelled. Re-posting replaces it.
- `update:schedule:claimed` — transient: the sidecar claims a due schedule via
  atomic `RENAME`, so a concurrent cancel and a firing sidecar can never both
  win.
- `update:schedule:result` — hash (TTL 7 days): `outcome`
  (`fired` | `missed` | `skipped_lock`), `scheduled_at`, `resolved_at`,
  `detail` — shown on the admin page so an absent admin sees what happened.

Semantics:

- **Already up to date at fire time** — fires anyway; the run short-circuits
  with "Already up to date" before entering maintenance (zero downtime).
- **Missed window** — if the system was down at the scheduled time, the update
  still fires up to 60 min late (`SCHEDULE_GRACE_SECONDS` in
  `docker/updater/watch.sh`); beyond that the schedule resolves as `missed` —
  never a surprise update long after the window the admin picked.
- **Lock held at fire time** — resolves as `skipped_lock`, no retry loop.
- **Countdown reminders** — the API's reminder loop watches `update:schedule`
  alongside `maintenance:schedule` and broadcasts the same
  `maintenance:reminder` WebSocket events (30/20/10/5/4/3/2/1 min before).
- `POST /system/update/reset` clears runs, **not** schedules.
- Scheduling requires a live sidecar heartbeat (like the manual trigger), so a
  schedule that could never fire is rejected upfront.
- Clock assumption: the epoch is computed by the API and compared against the
  sidecar host's clock — same kernel clock in the single-host compose
  deployment. Multi-host would need NTP (out of scope).

## Rules for update-friendly changes

- **Migrations must be backward-compatible for one version.** Alembic upgrades
  run automatically on boot, but a rollback restores *code only, never the
  schema* — `alembic downgrade` is deliberately not automated. Ship additive
  migrations first; destructive ones a release later.
- **New compose variables need `:-` defaults.** The running `.env` is never
  regenerated by an update. A `${NEW_VAR:?}` in a compose file would fail the
  preflight (safe, but blocks the update) — use `${NEW_VAR:-default}` plus a
  template entry and a release note instead.
- **Keep the updater contract stable.** The sidecar image only knows
  `source ops/lib/common.sh + ops/lib/update.sh; cmd_update_exec prod` — an
  old watcher must be able to drive a new repo's scripts. Both files are
  sourced fully into memory before the run, so the mid-run checkout is safe.

## CLI

```bash
./computor.sh update check    # compare local HEAD vs. remote tip (read-only)
./computor.sh update status   # Redis state, lock, sidecar heartbeat, recent log
./computor.sh update run prod # full update from the host (no sidecar needed)
./computor.sh update recover prod restore  # restore pre-upgrade Keycloak DB/code
./computor.sh update recover prod keep-new # validate and keep a fixed new version
```

`POST /system/update/reset` (or clearing `update:lock` in Redis) recovers from
a run that died without cleaning up; the lock also expires on its own after
2 hours.

## Keycloak backups and recovery

`computor.sh up prod` prepares `${SYSTEM_DEPLOYMENT_PATH}/updater/` and its
`.host-persistent` sentinel. The detached runner bind-mounts that directory,
the Traefik dynamic configuration directory, and the maintenance page directory
at their host paths. A missing mount or unwritable state directory prevents the
Keycloak upgrade; backups and maintenance routes survive removal of the runner.

Pre-upgrade backups are gzip-compressed, database-only `pg_dump --create` SQL
under `updater/backups/keycloak/`, created with `umask 077`; inherited deployment
ACLs can also grant authorized operators access. They include Keycloak credentials
and personal data: retain them according to the deployment's
backup policy. They are not an off-host backup and do not cover the application
database, workspace data, or PostgreSQL cluster roles. The existing `keycloak`
database role is retained during recovery. Dumps are not automatically deleted.

The authoritative gate is `updater/recovery-required`; `update:recovery` in
Redis mirrors it. It is written **before** starting the new Keycloak, so killing
the runner during migration also leaves recovery required. While it exists,
another update (even at the same commit) and `maintenance exit` refuse, and
`up` preserves the maintenance route. Clearing the Redis update lock or losing
Redis state does not remove this gate.

After inspecting the update log, choose one recovery command:

- **`restore`** verifies the dump and stopped Keycloak, checks out the recorded
  pre-upgrade commit, drops and restores only the Keycloak database, and verifies
  the old schema version. Every SQL error aborts recovery. It then rebuilds and
  starts the old services. This discards Keycloak changes made after the dump.
- **`keep-new`** keeps the current checkout, which must use the recorded new
  Keycloak version. Commit any fix-forward changes first; recovery requires a
  clean tracked working tree. It rebuilds and starts that checkout.

Both require Keycloak readiness, the expected schema version, and healthy API
and frontend before clearing the gate and lifting maintenance. Any failure keeps
maintenance. Once a restore has started, `keep-new` refuses: retry `restore`
after fixing its cause, because a partial SQL restore must never be accepted
merely because HTTP health checks succeed. Do not remove the marker manually.
This restores Keycloak only; application migrations must still follow the
backward-compatibility rule above.

### Rollout prerequisite

Keep the production self-updater disabled until issue
[computor-org/issues#424](https://github.com/computor-org/issues/issues/424)
is resolved and this executor, watcher image, mounts, and host directories have
been deployed **while still using the current Keycloak version**. The running
executor is sourced before checkout, so an upgrade cannot install its own
backup/recovery protection. Do not simply enable an old sidecar and ask it to
update to this change. Until that prerequisite is met, use the manual Keycloak
runbook: maintenance, verified stop and dump, checkout, then `computor.sh up prod`.

## Security notes

- The updater mounts the **raw docker socket** (root-equivalent on the host);
  builds and compose orchestration cannot go through the read-only prod
  socket-proxy. Contained by: no published ports, no Traefik route, non-root
  user (socket via `group_add`), and the only actionable input is a Redis
  queue behind the admin-only API — the deployed branch always comes from
  `.env`, never from the queue payload.
- `SYSTEM_REPO_TOKEN` is passed to git through an inline credential helper
  reading it from the environment: it never appears in URLs, argv, logs, or
  API responses (stderr is scrubbed before it is stored).
