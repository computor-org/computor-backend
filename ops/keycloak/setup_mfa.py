#!/usr/bin/env python3
"""Reconcile mandatory TOTP for Computor administrators and managers (issues#485).

Keycloak side of the admin-MFA requirement; dry-run unless --apply when run by
hand. The one-shot keycloak-idp-setup container calls configure() on every
boot when KEYCLOAK_ADMIN_MFA=true.

What it reconciles, idempotently:

* realm role ``computor-mfa-required``. The backend grants it to every human
  holding ``_admin`` or a global manager role and revokes it when the last such
  role goes (business_logic/admin_mfa.py). The ``administrators`` group also
  carries it, because group members are bootstrapped to ``_admin`` on login.
* a browser flow ``computor-browser-mfa`` (a copy of the bound browser flow)
  with a conditional subflow "user has computor-mfa-required -> OTP Form". The
  copied "user configured" 2FA subflow gets a negated role condition, so role
  holders see exactly one OTP prompt and everyone else keeps today's
  behaviour (OTP only when they enrolled one voluntarily).
* a reset-credentials flow ``computor-reset-mfa`` (a copy of the bound one): a
  role holder must enter the current OTP to finish an e-mail password reset,
  and the "Reset OTP" step (which deletes the authenticator after a reset) is
  skipped for role holders. Otherwise control of the mailbox alone would let
  anyone enrol a new authenticator.
* both copies are edited while unbound, record the flow they were copied from
  (for --rollback) and are bound together only once both are complete. An
  interrupted run is resumed by the next one; the bound flows are never edited,
  except for the amr maxAge of an OTP step (one in-place PUT, see
  FlowEditor.configure_execution).
* the CONFIGURE_TOTP required action is enabled.
* ``amr`` and ``acr`` protocol mappers on the backend client, so the ID token
  carries evidence of the second factor. The backend withholds elevated roles
  from SSO sessions whose ID token lacks ``otp`` in ``amr``. The OTP steps keep
  that evidence for the realm's longest SSO session lifespan, so it survives
  SSO-cookie logins and token refreshes of the session the code was entered in.

Stdlib only, like setup_identity_providers.py.
"""
import argparse
import json
import os
import re
import shlex
import urllib.parse
from pathlib import Path

from setup_identity_providers import _request, get_admin_token

ROLE = 'computor-mfa-required'
ROLE_DESCRIPTION = ('Must sign in with a one-time code (TOTP). Managed by the Computor backend '
                    'for holders of _admin and global manager roles; do not assign by hand.')
BROWSER_FLOW = 'computor-browser-mfa'
RESET_FLOW = 'computor-reset-mfa'
BROWSER_SUBFLOW = 'computor-mfa-required-otp'
RESET_SUBFLOW = 'computor-mfa-reset-otp'
ADMIN_GROUP = 'administrators'
# Keycloak's oidc-amr-mapper emits, for every execution completed in the user
# session, the ``default.reference.value`` of that execution's config, and
# nothing for executions without one (verified against 26.7.4: plain OTP logins
# yield ``"amr": []``). The role-gated OTP executions therefore carry ``otp``.
#
# It emits a reference only until completion time + ``default.reference.maxAge``
# has passed (AmrUtils.isAmrValid; a missing value counts as 0). A maxAge of 0
# kept the code valid for the second it was entered: the next SSO-cookie login
# or refresh-token grant dropped it, and administrators lost their rights
# minutes after signing in (AUTHZ_007 on computor.at, 2026-10-29). The evidence
# has to last as long as the session it was entered for, so maxAge is the
# realm's longest SSO session lifespan.
DEFAULT_SSO_MAX_LIFESPAN = 36000  # Keycloak's default ssoSessionMaxLifespan (10 h)


def amr_max_age(settings):
    """Seconds an entered code stays in ``amr``: the realm's longest SSO session lifespan."""
    spans = [settings.get('ssoSessionMaxLifespan'), settings.get('ssoSessionMaxLifespanRememberMe')]
    return max([int(span) for span in spans if span] or [DEFAULT_SSO_MAX_LIFESPAN])


def amr_otp(max_age):
    return {'default.reference.value': 'otp', 'default.reference.maxAge': str(max_age)}


# Keycloak 26.7 masks these values when a config is read back (GET returns
# MASKED for both), so they can be written but not compared. The config's alias
# records the maxAge it was written with instead (FlowEditor.config_alias).
MASKED = '**********'
MAPPERS = (
    ('amr', 'oidc-amr-mapper',
     {'id.token.claim': 'true', 'access.token.claim': 'true', 'introspection.token.claim': 'true'}),
    ('acr loa level', 'oidc-acr-mapper',
     {'id.token.claim': 'true', 'access.token.claim': 'true', 'introspection.token.claim': 'true'}),
)


def _q(value):
    return urllib.parse.quote(value, safe='')


class Client:
    def __init__(self, base, realm, token):
        self.root = base.rstrip('/') + '/admin/realms/' + _q(realm)
        self.token = token

    def request(self, method, path, body=None, allow=()):
        status, result = _request(method, self.root + path, token=self.token, json_body=body)
        if status in allow:
            return None
        if status not in (200, 201, 204):
            raise RuntimeError(f'{method} {path.split("?")[0]} failed: HTTP {status} {result}')
        return result


def children(executions, parent):
    """Direct children of the execution at index ``parent`` (depth-first list)."""
    level = executions[parent]['level']
    found = []
    for execution in executions[parent + 1:]:
        if execution['level'] <= level:
            break
        if execution['level'] == level + 1:
            found.append(execution)
    return found


def _role_condition(kc, execution):
    """(role, negate) of a conditional-user-role execution, or None."""
    if execution.get('providerId') != 'conditional-user-role' or not execution.get('authenticationConfig'):
        return None
    config = kc.request('GET', '/authentication/config/' + execution['authenticationConfig']).get('config', {})
    return config.get('condUserRole'), str(config.get('negate', 'false')).lower() == 'true'


def _is_ours(execution, conditions, suffix):
    """Whether a subflow execution is the role-gated OTP subflow ``suffix``.

    Recognised by its stable alias (``<flow> <suffix>``; Keycloak prefixes the
    aliases of copied subflows the same way) or, for subflows made by earlier
    revisions, by the positive role condition inside it.
    """
    name = execution.get('displayName') or ''
    return bool(execution.get('authenticationFlow')) and (
        name == suffix or name.endswith(' ' + suffix) or (ROLE, False) in conditions)


def _unconfigured_role_condition(kids):
    """A conditional-user-role left without config by an interrupted run."""
    return next((k for k in kids if k.get('providerId') == 'conditional-user-role'
                 and not k.get('authenticationConfig')), None)


class Gate:
    """Where one flow gets its role-gated OTP step.

    ``parent`` picks the subflow that receives it from the execution list
    (None: the top level of the flow). Conditional subflows next to it that
    contain one of ``factors`` get a negated role condition, so role holders
    are asked for one code, not two.
    """

    def __init__(self, suffix, factor, factors, parent=None):
        self.suffix, self.factor, self.factors, self.parent = suffix, factor, factors, parent


def _username_password_forms(executions):
    index = next((i for i, e in enumerate(executions) if e.get('authenticationFlow') and any(
        k.get('providerId') in ('auth-username-password-form', 'auth-username-form')
        for k in children(executions, i))), None)
    if index is None:
        raise RuntimeError('Cannot locate the username/password subflow of the browser flow')
    return index


BROWSER_GATE = Gate(BROWSER_SUBFLOW, 'auth-otp-form',
                    ('auth-otp-form', 'conditional-user-configured', 'conditional-credential'),
                    parent=_username_password_forms)
RESET_GATE = Gate(RESET_SUBFLOW, 'auth-otp-form', ('reset-otp',))


class FlowEditor:
    def __init__(self, kc, alias, amr_max_age=DEFAULT_SSO_MAX_LIFESPAN):
        self.kc, self.alias = kc, alias
        self.amr = amr_otp(amr_max_age)

    def executions(self):
        return self.kc.request('GET', '/authentication/flows/' + _q(self.alias) + '/executions')

    def set_requirement(self, execution, requirement):
        if execution.get('requirement') != requirement:
            self.kc.request('PUT', '/authentication/flows/' + _q(self.alias) + '/executions',
                            dict(execution, requirement=requirement))

    def config_alias(self, execution, config=None):
        """Alias of the config this script writes for ``execution``.

        An amr config's alias ends in its maxAge, so a config written with
        another maxAge (0 before 2026-10-29, or an older session lifespan)
        reads as foreign and is rewritten once.
        """
        alias = f'{self.alias}-{execution["providerId"]}-{execution["id"][:8]}'
        max_age = (config or {}).get('default.reference.maxAge')
        return alias if max_age is None else f'{alias}-amr{max_age}'

    def configure_execution(self, execution, config):
        """Give ``execution`` the values in ``config`` (create or merge its config).

        A masked value cannot be compared. It is trusted only in a config this
        script created (its alias; the POST sets alias and values at once) and
        rewritten otherwise. A rewritten amr config takes our alias, so the
        next run trusts it. In a bound flow that is one in-place PUT: it changes
        how long the evidence lasts, never who is asked for a code.
        """
        alias = self.config_alias(execution, config)
        if not execution.get('authenticationConfig'):
            self.kc.request('POST', '/authentication/executions/' + execution['id'] + '/config',
                            {'alias': alias, 'config': dict(config)})
            return
        path = '/authentication/config/' + execution['authenticationConfig']
        current = self.kc.request('GET', path)
        values = current.get('config', {})
        ours = current.get('alias') == alias
        if any(values.get(k) != v and not (ours and values.get(k) == MASKED) for k, v in config.items()):
            update = dict(current, config={**{k: v for k, v in values.items() if v != MASKED}, **config})
            if 'default.reference.maxAge' in config:
                update['alias'] = alias
            self.kc.request('PUT', path, update)

    def add_execution(self, parent_alias, provider, requirement, config=None):
        before = {e['id'] for e in self.executions()}
        self.kc.request('POST', '/authentication/flows/' + _q(parent_alias) + '/executions/execution',
                        {'provider': provider})
        added = next(e for e in self.executions() if e['id'] not in before)
        self.set_requirement(added, requirement)
        if config is not None:
            self.configure_execution(added, config)
        return added

    def add_subflow(self, parent_alias, alias, description):
        self.kc.request('POST', '/authentication/flows/' + _q(parent_alias) + '/executions/flow',
                        {'alias': alias, 'type': 'basic-flow', 'provider': 'registration-page-form',
                         'description': description})
        added = next(e for e in self.executions() if e.get('authenticationFlow') and e.get('displayName') == alias)
        self.set_requirement(added, 'CONDITIONAL')
        return added

    def layout(self, gate):
        """(parent alias, our subflow with its children or None, the other 2FA subflows)."""
        executions = self.executions()
        if gate.parent is None:
            parent_alias, siblings = self.alias, [e for e in executions if e['level'] == 0]
        else:
            index = gate.parent(executions)
            parent_alias, siblings = executions[index]['displayName'], children(executions, index)
        ours, others = None, []
        for sibling in siblings:
            if not sibling.get('authenticationFlow'):
                continue
            index = next(i for i, e in enumerate(executions) if e['id'] == sibling['id'])
            kids = children(executions, index)
            conditions = {k['id']: _role_condition(self.kc, k) for k in kids}
            if _is_ours(sibling, set(conditions.values()), gate.suffix):
                ours = ours or (sibling, kids, conditions)
            elif sibling.get('requirement') == 'CONDITIONAL' and any(
                    k.get('providerId') in gate.factors for k in kids):
                others.append((sibling, kids, conditions))
        return parent_alias, ours, others

    def _role_gate(self, kids, conditions, negate):
        """Child condition for ``(ROLE, negate)``, adopting one an interrupted run left unconfigured."""
        found = next((k for k in kids if conditions.get(k['id']) == (ROLE, negate)), None)
        return found or _unconfigured_role_condition(kids)

    def ensure_mfa(self, gate):
        """Add the role-gated OTP subflow and exclude role holders from the other 2FA subflows.

        Every step looks for what an earlier, possibly interrupted, run left
        behind (by alias or by provider inside our subflow) and completes it
        instead of adding a duplicate.
        """
        _, _, others = self.layout(gate)
        for sibling, kids, conditions in others:
            found = self._role_gate(kids, conditions, True)
            if found is None:
                self.add_execution(sibling['displayName'], 'conditional-user-role', 'REQUIRED',
                                   {'condUserRole': ROLE, 'negate': 'true'})
            else:
                self.set_requirement(found, 'REQUIRED')
                self.configure_execution(found, {'condUserRole': ROLE, 'negate': 'true'})
        parent_alias, ours, _ = self.layout(gate)
        if ours is None:
            self.add_subflow(parent_alias, f'{self.alias} {gate.suffix}',
                             f'One-time code for holders of the {ROLE} realm role')
            _, ours, _ = self.layout(gate)
        subflow, kids, conditions = ours
        self.set_requirement(subflow, 'CONDITIONAL')
        condition = self._role_gate(kids, conditions, False)
        if condition is None:
            self.add_execution(subflow['displayName'], 'conditional-user-role', 'REQUIRED',
                               {'condUserRole': ROLE, 'negate': 'false'})
        else:
            self.set_requirement(condition, 'REQUIRED')
            self.configure_execution(condition, {'condUserRole': ROLE, 'negate': 'false'})
        factor = next((k for k in kids if k.get('providerId') == gate.factor), None)
        if factor is None:
            self.add_execution(subflow['displayName'], gate.factor, 'REQUIRED', self.amr)
        else:
            self.set_requirement(factor, 'REQUIRED')
            self.configure_execution(factor, self.amr)

    def problems(self, gate):
        """What keeps the flow from enforcing the gate; empty when it is complete."""
        found = []
        _, ours, others = self.layout(gate)
        for sibling, kids, conditions in others:
            if not any(conditions.get(k['id']) == (ROLE, True) and k.get('requirement') == 'REQUIRED'
                       for k in kids):
                found.append(f'{self.alias}: {sibling["displayName"]!r} lacks the negated role condition')
        if ours is None:
            return found + [f'{self.alias}: role-gated OTP subflow missing']
        subflow, kids, conditions = ours
        if subflow.get('requirement') != 'CONDITIONAL':
            found.append(f'{self.alias}: {subflow["displayName"]!r} is not CONDITIONAL')
        if not any(conditions.get(k['id']) == (ROLE, False) and k.get('requirement') == 'REQUIRED' for k in kids):
            found.append(f'{self.alias}: {subflow["displayName"]!r} lacks the role condition')
        factor = next((k for k in kids if k.get('providerId') == gate.factor and k.get('requirement') == 'REQUIRED'),
                      None)
        if factor is None or not factor.get('authenticationConfig'):
            found.append(f'{self.alias}: {subflow["displayName"]!r} lacks a configured {gate.factor}')
        else:
            current = self.kc.request('GET', '/authentication/config/' + factor['authenticationConfig'])
            config = current.get('config', {})
            if any(config.get(k) not in (v, MASKED) for k, v in self.amr.items()):
                found.append(f'{self.alias}: {gate.factor} does not emit amr "otp"')
            elif MASKED in config.values() and current.get('alias') != self.config_alias(factor, self.amr):
                found.append(f'{self.alias}: {gate.factor} amr "otp" was not written for '
                             f'maxAge {self.amr["default.reference.maxAge"]}')
        return found


# A copy's description records the flow it was copied from, so rollback can
# rebind exactly that flow even after the copy has been bound.
ORIGIN_TAG = 'computor-mfa-origin='
_ORIGIN_RE = re.compile(re.escape(ORIGIN_TAG) + r'("(?:[^"\\]|\\.)*")')


def _origin(flow):
    match = _ORIGIN_RE.search((flow or {}).get('description') or '')
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except ValueError:
        return None


def _top_flows(kc):
    return {f['alias']: f for f in kc.request('GET', '/authentication/flows')}


def prepare_copy(kc, settings, key, default, target):
    """(alias, origin) of our flow for binding ``key``, an unbound copy of the bound flow.

    The bound flow is never edited. A copy left by an interrupted run is resumed
    when it was taken from the flow that is still bound; a copy of anything else
    (or one whose origin record was not written) is deleted and taken again.
    When our copy is already bound, it is returned with its recorded origin.
    """
    bound = settings.get(key) or default
    flows = _top_flows(kc)
    if bound == target:
        origin = _origin(flows.get(target))
        return target, origin if origin and origin != target else default
    existing = flows.get(target)
    if existing is not None and _origin(existing) != bound:
        kc.request('DELETE', '/authentication/flows/' + existing['id'])
        existing = None
    if existing is None:
        kc.request('POST', '/authentication/flows/' + _q(bound) + '/copy', {'newName': target})
        copy = _top_flows(kc)[target]
        kc.request('PUT', '/authentication/flows/' + copy['id'],
                   dict({k: copy.get(k) for k in ('id', 'alias', 'providerId', 'topLevel', 'builtIn')},
                        description=f'{ORIGIN_TAG}{json.dumps(bound)} Admin MFA copy (issues#485); '
                                    'setup_mfa.py --rollback rebinds the origin.'))
    return target, bound


def ensure_role(kc):
    role = kc.request('GET', '/roles/' + _q(ROLE), allow=(404,))
    if role is None:
        kc.request('POST', '/roles', {'name': ROLE, 'description': ROLE_DESCRIPTION})
        role = kc.request('GET', '/roles/' + _q(ROLE))
    return role


def ensure_group_role(kc, role):
    groups = kc.request('GET', '/groups?exact=true&search=' + _q(ADMIN_GROUP)) or []
    group = next((g for g in groups if g['name'] == ADMIN_GROUP), None)
    if group is None:
        return False
    mapped = kc.request('GET', '/groups/' + group['id'] + '/role-mappings/realm') or []
    if not any(r['name'] == ROLE for r in mapped):
        kc.request('POST', '/groups/' + group['id'] + '/role-mappings/realm', [role])
    return True


def ensure_required_action(kc):
    action = kc.request('GET', '/authentication/required-actions/CONFIGURE_TOTP')
    if not action.get('enabled'):
        kc.request('PUT', '/authentication/required-actions/CONFIGURE_TOTP', dict(action, enabled=True))


def ensure_client_mappers(kc, client_id):
    clients = kc.request('GET', '/clients?clientId=' + _q(client_id)) or []
    if not clients:
        raise RuntimeError(f'Client {client_id!r} not found; cannot add MFA evidence mappers')
    cid = clients[0]['id']
    existing = kc.request('GET', '/clients/' + cid + '/protocol-mappers/models') or []
    for name, mapper, config in MAPPERS:
        found = next((m for m in existing if m.get('protocolMapper') == mapper), None)
        if found is None:
            kc.request('POST', '/clients/' + cid + '/protocol-mappers/models',
                       {'name': name, 'protocol': 'openid-connect', 'protocolMapper': mapper, 'config': config})
        elif any(found.get('config', {}).get(k) != v for k, v in config.items()):
            kc.request('PUT', '/clients/' + cid + '/protocol-mappers/models/' + found['id'],
                       dict(found, config={**found.get('config', {}), **config}))


def configure(base, realm, token, client_id='computor-backend', apply=True):
    """Reconcile the realm; safe to re-run after an interruption at any point.

    The MFA steps are built in unbound copies of the bound browser and
    reset-credentials flows. Both are bound in one realm update, and only after
    a read-back shows them complete, so an interrupted run never leaves a
    half-configured flow in use. A re-run resumes the copies.
    """
    kc = Client(base, realm, token)
    settings = kc.request('GET', '')
    max_age = amr_max_age(settings)
    plan = {'role': ROLE, 'browserFlow': settings.get('browserFlow'),
            'resetCredentialsFlow': settings.get('resetCredentialsFlow'), 'client': client_id,
            'amrMaxAge': max_age, 'applied': apply}
    if not apply:
        return plan
    role = ensure_role(kc)
    plan['administratorsGroupMapped'] = ensure_group_role(kc, role)
    ensure_required_action(kc)

    browser, _ = prepare_copy(kc, settings, 'browserFlow', 'browser', BROWSER_FLOW)
    reset, _ = prepare_copy(kc, settings, 'resetCredentialsFlow', 'reset credentials', RESET_FLOW)
    gates = ((FlowEditor(kc, browser, max_age), BROWSER_GATE), (FlowEditor(kc, reset, max_age), RESET_GATE))
    for editor, gate in gates:
        editor.ensure_mfa(gate)
    ensure_client_mappers(kc, client_id)

    missing = [problem for editor, gate in gates for problem in editor.problems(gate)]
    if missing:
        raise RuntimeError('MFA flows incomplete, left unbound: ' + '; '.join(missing))
    wanted = {'browserFlow': browser, 'resetCredentialsFlow': reset}
    if any(settings.get(key) != alias for key, alias in wanted.items()):
        kc.request('PUT', '', wanted)
    stored = kc.request('GET', '')
    if stored.get('browserFlow') != browser or stored.get('resetCredentialsFlow') != reset:
        raise RuntimeError('MFA flow bindings did not persist')
    plan.update(browserFlow=browser, resetCredentialsFlow=reset)
    return plan


def _mfa_execution(kc, executions):
    """First execution of ours in a flow: a negated role condition or a role-gated OTP subflow."""
    for index, execution in enumerate(executions):
        if _role_condition(kc, execution) == (ROLE, True):
            return execution
        if execution.get('authenticationFlow'):
            conditions = {_role_condition(kc, k) for k in children(executions, index)}
            if any(_is_ours(execution, conditions, suffix) for suffix in (BROWSER_SUBFLOW, RESET_SUBFLOW)):
                return execution
    return None


def _remove_mfa_executions(kc, alias):
    """Delete every role-gated subflow and negated role condition from ``alias``; returns the count."""
    editor, removed = FlowEditor(kc, alias), 0
    while True:
        execution = _mfa_execution(kc, editor.executions())
        if execution is None:
            return removed
        kc.request('DELETE', '/authentication/executions/' + execution['id'])
        removed += 1


def rollback(base, realm, token):
    """Undo configure(): rebind the original flows and remove what configure() made.

    Each binding that points at our copy goes back to the flow recorded in the
    copy (the built-in flow when there is no record). Then our copies are
    deleted, bound or not, including those an interrupted configure() left
    behind, and MFA steps that earlier revisions edited into other custom flows
    are stripped. Safe to re-run.

    Deleting only the role is NOT a rollback: Keycloak's conditional-user-role
    returns false for an unknown role even when negated (26.7.4 bytecode), which
    would silently switch off the OTP prompt for voluntarily enrolled users too.
    The role and the token mappers stay; they are inert. Pending CONFIGURE_TOTP
    actions stay too (other policies, such as the mail team's, set them);
    remove them per user if unwanted.
    """
    kc = Client(base, realm, token)
    settings = kc.request('GET', '')
    flows = _top_flows(kc)
    changes = {}
    for key, ours, builtin in (('browserFlow', BROWSER_FLOW, 'browser'),
                               ('resetCredentialsFlow', RESET_FLOW, 'reset credentials')):
        if (settings.get(key) or builtin) == ours:
            origin = _origin(flows.get(ours))
            changes[key] = origin if origin in flows and origin not in (BROWSER_FLOW, RESET_FLOW) else builtin
    if changes:
        kc.request('PUT', '', changes)
    stored = kc.request('GET', '')
    if stored.get('browserFlow') in (BROWSER_FLOW, RESET_FLOW) or \
            stored.get('resetCredentialsFlow') in (BROWSER_FLOW, RESET_FLOW):
        raise RuntimeError('Rollback did not rebind the original flows')
    deleted = []
    for alias in (BROWSER_FLOW, RESET_FLOW):
        if alias in flows:
            kc.request('DELETE', '/authentication/flows/' + flows[alias]['id'])
            deleted.append(alias)
    stripped = {}
    for alias, flow in _top_flows(kc).items():
        if not flow.get('builtIn'):
            count = _remove_mfa_executions(kc, alias)
            if count:
                stripped[alias] = count
    return {'browserFlow': stored.get('browserFlow'), 'resetCredentialsFlow': stored.get('resetCredentialsFlow'),
            'deletedFlows': deleted, 'strippedExecutions': stripped}


def status(base, realm, token):
    """Read-only: who holds the role and whether they have enrolled OTP."""
    kc = Client(base, realm, token)
    members = kc.request('GET', '/roles/' + _q(ROLE) + '/users?max=1000', allow=(404,)) or []
    report = []
    for user in members:
        credentials = kc.request('GET', '/users/' + user['id'] + '/credentials') or []
        report.append({'username': user['username'],
                       'otp': any(c.get('type') == 'otp' for c in credentials),
                       'requiredActions': user.get('requiredActions', [])})
    settings = kc.request('GET', '')
    return {'browserFlow': settings.get('browserFlow'), 'resetCredentialsFlow': settings.get('resetCredentialsFlow'),
            'directRoleMembers': report}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--env', help='read credentials from this .env file (host run)')
    parser.add_argument('--base-url')
    parser.add_argument('--realm')
    parser.add_argument('--apply', action='store_true', help='change the realm (default: print the plan)')
    parser.add_argument('--status', action='store_true', help='read-only report of role members and OTP state')
    parser.add_argument('--rollback', action='store_true',
                        help='rebind the original flows and delete the MFA flow copies')
    args = parser.parse_args()
    if args.env:
        for line in Path(args.env).read_text().splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key, value = line.split('=', 1)
                parts = shlex.split(value, comments=False)
                os.environ[key.strip()] = parts[0] if parts else ''
    base = args.base_url or (('http://127.0.0.1:' + os.environ.get('KEYCLOAK_PORT', '8180') +
                              os.environ.get('KEYCLOAK_HTTP_RELATIVE_PATH', '/').rstrip('/')) if args.env else
                             (os.environ.get('KEYCLOAK_SERVER_URL_INTERNAL') or os.environ['KEYCLOAK_SERVER_URL']))
    realm = args.realm or os.environ.get('KEYCLOAK_REALM', 'computor')
    token = get_admin_token(base, os.environ.get('KEYCLOAK_ADMIN'), os.environ.get('KEYCLOAK_ADMIN_PASSWORD'))
    if args.status:
        print(json.dumps(status(base, realm, token), indent=2))
        return
    if args.rollback:
        print(json.dumps(rollback(base, realm, token)))
        return
    print(json.dumps(configure(base, realm, token, os.environ.get('KEYCLOAK_CLIENT_ID', 'computor-backend'),
                               apply=args.apply)))


if __name__ == '__main__':
    main()
