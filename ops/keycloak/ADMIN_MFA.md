# Mandatory TOTP for administrators and managers

computor-org/issues#485. Every human account that holds `_admin` or any other
global role except `_workspace_user` (`_user_manager`, `_organization_manager`,
`_example_manager`, `_git_manager`, `_service_manager`, `_workspace_maintainer`,
custom roles) must sign in with a one-time code. Ordinary users keep password
sign-in.

## How it works

- `KEYCLOAK_ADMIN_MFA` switches it on. The prod Keycloak overlay defaults it
  to `true` for both `keycloak-idp-setup` and `uvicorn`; dev leaves it off.
- On every boot `keycloak-idp-setup` runs `setup_mfa.py`. It creates the
  realm role `computor-mfa-required` (also mapped to the `administrators`
  group) and binds the browser flow `computor-browser-mfa`, so holders of the
  role must enter an OTP and holders without one must enrol. It also makes
  role holders enter their OTP to finish an e-mail password reset, and it adds
  `amr`/`acr` mappers to the `computor-backend` client.
- The backend keeps the role in step with the database: a full reconcile at
  startup, a targeted sync after every `user_role` change and at each SSO
  login of an elevated user. Holders without an OTP credential get the
  `CONFIGURE_TOTP` required action. The role is removed when the last
  elevated role goes.
- The backend withholds elevated roles from SSO sessions whose ID token has
  no `otp` in `amr`. Those users keep ordinary access and get `AUTHZ_007`
  ("sign out and sign in again with your code") on admin actions. API tokens
  (`ctp_*`, `X-API-Token`) and service accounts are not affected.

## Enrolling

1. Sign in as usual. Keycloak shows "Mobile Authenticator Setup". Scan the QR
   code with FreeOTP, Google Authenticator or Microsoft Authenticator, then
   enter the code.
2. Sign out and sign in again with password and code. The enrolment login
   carries no OTP evidence, so admin rights start with the second sign-in.

Sessions that existed before the rollout lose their elevated rights at once.
Their holders sign out and sign in again.

Check who still has to enrol (read-only):

```bash
cd /opt/computor/backend
python3 ops/keycloak/setup_mfa.py --env .env --status
```

## Lost authenticator

A master-realm administrator resets it. The master realm and its console are
allowlisted at nginx and need their own second factor.

1. Admin console → realm `computor` → Users → the user → Credentials → delete
   the `otp` credential.
2. Required user actions → add "Configure OTP". A restart of the backend or
   the user's next sign-in also sets it.
3. Confirm the person's identity outside e-mail before you do this. E-mail
   reset does not remove the authenticator of a role holder: it asks for the
   code.

## Break-glass

- One admin locked out, another admin available: use "Lost authenticator".
- No master-realm admin usable: create a temporary master admin with
  `docker exec -it computor-keycloak /opt/keycloak/bin/kc.sh bootstrap-admin user --username breakglass`
  (Keycloak 26.7 command; it prompts for a password and writes to the same
  Postgres). This has not been rehearsed against a running server. If it
  clashes with the running server, stop `computor-keycloak` and run the
  same command in a one-off container from the same image and environment.
  Then follow "Lost authenticator" and delete the temporary admin.
- Keycloak itself down: an existing `ctp_*` API token of an admin still
  works, because API tokens are not MFA-gated. Treat such tokens as
  break-glass credentials: keep them few, short-lived, and revoke them after
  use.

## Turning it off (rollback)

```bash
cd /opt/computor/backend
python3 ops/keycloak/setup_mfa.py --env .env --rollback   # rebinds the built-in browser flow, removes reset-flow gates
echo KEYCLOAK_ADMIN_MFA=false >> .env
./computor.sh up prod -d                                   # recreates uvicorn without the gate
```

Do not just delete the realm role. Keycloak's role condition is false for an
unknown role even when negated, so the OTP prompt would also stop for users
who enrolled voluntarily. Rollback leaves the role, the unbound flow copy, the
token mappers, enrolled authenticators and pending "Configure OTP" actions in
place. Remove those actions per user if unwanted; other policies such as
the mail team's OTP set them too. Re-applying is idempotent.

## Limits

- Logins through a brokered identity provider skip the browser flow's OTP
  step. Such users get no elevated rights, because there is no `otp` in
  `amr`. Elevated users should sign in with password and code.
- Isolated test: `uv run --project computor-backend python ops/keycloak/test_mfa_live.py`
  (Keycloak 26.7.4 in Docker; login, enrolment, OTP, e-mail reset, sync,
  rollback).
