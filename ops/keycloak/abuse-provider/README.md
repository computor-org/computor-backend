# Computor Keycloak abuse providers

Built against Keycloak 26.7.4 and Java 21. Build and run the unit tests with `mvn verify`.
The shaded `target/computor-keycloak-abuse.jar` includes ALTCHA 2.0.1 and a relocated
JSON library. Keycloak dependencies remain provided by the server.

The factories are:

- `computor-registration-abuse`: required registration FormAction, ordered after
  Registration User Creation. It validates ALTCHA proof of work and the empty
  `website` honeypot before the flow's success phase can create a user.
- `computor-reset-abuse`: replaces the reset flow's Choose User execution. The
  username and proof are submitted together before the stock user lookup and
  reset-email steps. Existing signed reset action tokens continue normally.
- `computor-gmail-unique`: add this validator to the user profile's `email`
  validations. Consumer `gmail.com` addresses compare without dots and `+tags`;
  their stored address is preserved. Other domains retain their own semantics.
- `computor-registration-activity`: enable this event listener to retain successful
  login times for self-registered users.

Both authentication executions require a shared random `secret` of at least 32
characters. Optional configuration: `ttlSeconds` (default 300, range 30–900) and
`cost` (default 10000, range 1000–100000 PBKDF2/SHA-256 iterations).

The theme receives `computorAltchaRequired` and `computorAltchaChallenge` (JSON),
and submits the widget's base64 response as `altcha`. Challenges contain the
root authentication session, browser tab and flow. The issued signature must
match the authentication-session note. Keycloak's single-use store atomically
consumes each challenge across cluster nodes; expiry and retries bound retained
state. Payload size is limited before decoding. Failed verification sends no
mail. A page retry issues a fresh challenge.

ALTCHA 2.0.1 re-derives submitted keys but does not enforce their challenge prefix
in its verification method. The provider explicitly verifies the nonempty prefix
before invoking the library. A regression test demonstrates and rejects the
otherwise valid, nonsolving key.

Gmail uniqueness takes a pessimistic write lock on the persisted realm row and
queries scalar email values directly from JPA. Keycloak holds this lock through
the enclosing user-profile mutation transaction, serializing concurrent signup
and email updates. It avoids stale user-cache decisions and requires no schema
migration or backfill. Existing duplicate inboxes are retained for explicit audit;
they block new aliases, while their existing owners may save unrelated profile
changes. This targets Keycloak's local JPA user storage; external user-storage
providers must supply equivalent enforcement before enabling public registration.

The registration action writes server provenance attributes
`computor.selfRegistered=true` and `computor.selfRegisteredAt` (creation timestamp
in milliseconds). The event listener sets `computor.lastLogin` after successful
login. Configure these attributes with admin-only editing permissions in the
user profile so clients cannot forge cleanup evidence.

Upstream API references: [Keycloak Server Developer Guide](https://www.keycloak.org/docs/latest/server_development/),
[ALTCHA Java library](https://github.com/altcha-org/altcha-lib-java).
