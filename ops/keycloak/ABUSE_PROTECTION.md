# Public signup and recovery protection

The optional Keycloak provider protects public registration and password recovery
with locally served ALTCHA proof of work and an empty honeypot. A user-profile
validator treats consumer Gmail dots and plus tags as one inbox, without changing
the stored delivery address. Normal sign-in and signed recovery-link continuation
keep their existing flow. The implementation targets local JPA users and refuses
provisioning when an external user-storage provider is enabled.

See [the provider contract](abuse-provider/README.md) for factory identifiers,
transactional uniqueness, challenge bounds and the explicit ALTCHA verification
repair. `googlemail.com` and custom-domain address normalization are outside the
current rule. Existing Gmail collisions are counted without logging addresses;
they are retained and prevent further registrations for that inbox.

## Build and verification

```bash
ops/keycloak/build_abuse.sh /tmp/computor-keycloak-providers
# The integration fixture has no external network or recipients.
docker pull quay.io/keycloak/keycloak:26.7.4
docker pull postgres:16.15
python3 ops/keycloak/test_abuse_live.py \
  --provider /tmp/computor-keycloak-providers/computor-keycloak-abuse.jar
```

The build uses a digest-pinned Java21/Maven toolchain and pinned direct dependencies.
Widget version 3.0.11 and its license are committed with SHA-256 provenance under
`data/keycloak/themes/computor/login/resources/js/altcha-manifest.json`. All widget
scripts are served from Keycloak; no runtime CDN or CAPTCHA service is required.

## Deployment

From a git-pinned checkout on the computor.at control host, stage the tested JAR
and run the targeted rollout:

```bash
ops/keycloak/deploy_abuse.sh /path/to/computor-keycloak-abuse.jar
```

This holds the existing deployment lock, takes a private Keycloak SQL export and
snapshots the env, theme and provider directories. It enables the optional compose
overlay, generates a persistent random `KEYCLOAK_ABUSE_SECRET` if absent, installs
the provider/theme, restarts only Keycloak, and reconciles the protected flows and
email validator twice. Snapshots and the source/JAR identity remain under
`$SYSTEM_DEPLOYMENT_PATH/keycloak-abuse-releases/`. Sync the updated private env
into the deployment's persisted redeploy state after a successful rollout.

`KEYCLOAK_ABUSE_COST` defaults to 10000 PBKDF2 iterations; challenge difficulty also
includes the signed solution prefix. `KEYCLOAK_ABUSE_TTL` defaults to 300 seconds.
The supported bounds are cost 1000–100000 and TTL 30–900. Measure browser delay
before raising cost, especially for slower phones. JavaScript is required for
signup/recovery; the form provides an explanation when it is disabled.

Normal `computor.sh up` builds/stages the provider and its idp-setup one-shot
reconciles policy when `KEYCLOAK_ABUSE_PROTECTION=true`. Other deployments leave
this flag false. Theme-only rollout does not install the provider or enable the
flows. The existing public policy/form verifier in computor-infra remains applicable;
a full signup test must also solve the challenge.

## Rollback

A failed targeted rollout restores saved flow bindings/profile before removing
the provider, then restores the prior theme/providers/env and starts Keycloak.
If config restoration fails, it retains the provider and env for manual recovery,
so active custom flows do not lose their implementation. Inspect the private
snapshot and service logs before continuing. The SQL export is a disaster-recovery
copy; routine rollback does not replace the database or lose newer user data.

For a later manual rollback, first run the saved checkout's `setup_abuse.py --env
.env --restore <release>/realm-before.json` while the provider is still available.
Then stop Keycloak, restore the saved physical theme/provider directory contents
and env, and recreate only Keycloak using the restored compose selection. Keep
its database in place, wait for health, and verify normal login and recovery.
