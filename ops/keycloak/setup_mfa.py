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
* the bound reset-credentials flow: a role holder must enter the current OTP
  to finish an e-mail password reset, and the "Reset OTP" step (which deletes
  the authenticator after a reset) is skipped for role holders. Otherwise
  control of the mailbox alone would let anyone enrol a new authenticator.
* the CONFIGURE_TOTP required action is enabled.
* ``amr`` and ``acr`` protocol mappers on the backend client, so the ID token
  carries evidence of the second factor. The backend withholds elevated roles
  from SSO sessions whose ID token lacks ``otp`` in ``amr``.

Stdlib only, like setup_identity_providers.py.
"""
import argparse
import json
import os
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
AMR_OTP = {'default.reference.value': 'otp', 'default.reference.maxAge': '0'}
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


class FlowEditor:
    def __init__(self, kc, alias):
        self.kc, self.alias = kc, alias

    def executions(self):
        return self.kc.request('GET', '/authentication/flows/' + _q(self.alias) + '/executions')

    def set_requirement(self, execution, requirement):
        if execution.get('requirement') != requirement:
            self.kc.request('PUT', '/authentication/flows/' + _q(self.alias) + '/executions',
                            dict(execution, requirement=requirement))

    def add_execution(self, parent_alias, provider, requirement, config=None):
        before = {e['id'] for e in self.executions()}
        self.kc.request('POST', '/authentication/flows/' + _q(parent_alias) + '/executions/execution',
                        {'provider': provider})
        added = next(e for e in self.executions() if e['id'] not in before)
        self.set_requirement(added, requirement)
        if config is not None:
            self.kc.request('POST', '/authentication/executions/' + added['id'] + '/config',
                            {'alias': f'{parent_alias}-{provider}-{added["id"][:8]}', 'config': config})
        return added

    def add_subflow(self, parent_alias, alias, description):
        self.kc.request('POST', '/authentication/flows/' + _q(parent_alias) + '/executions/flow',
                        {'alias': alias, 'type': 'basic-flow', 'provider': 'registration-page-form',
                         'description': description})
        added = next(e for e in self.executions() if e.get('authenticationFlow') and e.get('displayName') == alias)
        self.set_requirement(added, 'CONDITIONAL')
        return added

    def ensure_mfa(self, parent_index, subflow_alias, factor_provider, existing_factor_providers):
        """Under the subflow at ``parent_index`` (None = top level): add the
        role-gated OTP subflow and exclude role holders from the existing
        conditional subflows that contain one of ``existing_factor_providers``."""
        executions = self.executions()
        if parent_index is None:
            parent_alias, siblings = self.alias, [e for e in executions if e['level'] == 0]
        else:
            parent_alias, siblings = executions[parent_index]['displayName'], children(executions, parent_index)
        ours = None
        for sibling in siblings:
            if not sibling.get('authenticationFlow') or sibling.get('requirement') != 'CONDITIONAL':
                continue
            index = next(i for i, e in enumerate(executions) if e['id'] == sibling['id'])
            kids = children(executions, index)
            conditions = [c for c in (_role_condition(self.kc, k) for k in kids) if c]
            if (ROLE, False) in conditions:
                ours = sibling
            elif any(k.get('providerId') in existing_factor_providers for k in kids):
                if (ROLE, True) not in conditions:
                    self.add_execution(sibling['displayName'], 'conditional-user-role', 'REQUIRED',
                                       {'condUserRole': ROLE, 'negate': 'true'})
        if ours is None:
            ours = self.add_subflow(parent_alias, subflow_alias,
                                    f'One-time code for holders of the {ROLE} realm role')
            self.add_execution(ours['displayName'], 'conditional-user-role', 'REQUIRED',
                               {'condUserRole': ROLE, 'negate': 'false'})
            self.add_execution(ours['displayName'], factor_provider, 'REQUIRED', dict(AMR_OTP))
            return
        executions = self.executions()
        index = next(i for i, e in enumerate(executions) if e['id'] == ours['id'])
        self.set_requirement(executions[index], 'CONDITIONAL')
        factor = next((k for k in children(executions, index) if k.get('providerId') == factor_provider), None)
        if factor is None:
            self.add_execution(ours['displayName'], factor_provider, 'REQUIRED', dict(AMR_OTP))
            return
        self.set_requirement(factor, 'REQUIRED')
        if not factor.get('authenticationConfig'):
            self.kc.request('POST', '/authentication/executions/' + factor['id'] + '/config',
                            {'alias': f'{ours["displayName"]}-amr-{factor["id"][:8]}', 'config': dict(AMR_OTP)})
            return
        path = '/authentication/config/' + factor['authenticationConfig']
        current = self.kc.request('GET', path)
        if any(current.get('config', {}).get(k) != v for k, v in AMR_OTP.items()):
            self.kc.request('PUT', path, dict(current, config={**current.get('config', {}), **AMR_OTP}))


def _bound_copy(kc, settings, key, default, target):
    """Alias of a non-built-in flow bound as ``key``, copying a built-in one."""
    current = settings.get(key) or default
    flows = {f['alias']: f for f in kc.request('GET', '/authentication/flows')}
    if current in flows and not flows[current].get('builtIn'):
        return current
    if target not in flows:
        kc.request('POST', '/authentication/flows/' + _q(current) + '/copy', {'newName': target})
    return target


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
    kc = Client(base, realm, token)
    settings = kc.request('GET', '')
    plan = {'role': ROLE, 'browserFlow': settings.get('browserFlow'),
            'resetCredentialsFlow': settings.get('resetCredentialsFlow'), 'client': client_id,
            'applied': apply}
    if not apply:
        return plan
    role = ensure_role(kc)
    plan['administratorsGroupMapped'] = ensure_group_role(kc, role)
    ensure_required_action(kc)

    browser = _bound_copy(kc, settings, 'browserFlow', 'browser', BROWSER_FLOW)
    editor = FlowEditor(kc, browser)
    executions = editor.executions()
    forms = next((i for i, e in enumerate(executions) if e.get('authenticationFlow') and any(
        k.get('providerId') in ('auth-username-password-form', 'auth-username-form')
        for k in children(executions, i))), None)
    if forms is None:
        raise RuntimeError(f'Cannot locate the username/password subflow of {browser!r}')
    editor.ensure_mfa(forms, BROWSER_SUBFLOW, 'auth-otp-form',
                      ('auth-otp-form', 'conditional-user-configured', 'conditional-credential'))

    reset = _bound_copy(kc, settings, 'resetCredentialsFlow', 'reset credentials', RESET_FLOW)
    FlowEditor(kc, reset).ensure_mfa(None, RESET_SUBFLOW, 'auth-otp-form', ('reset-otp',))

    ensure_client_mappers(kc, client_id)
    kc.request('PUT', '', {'browserFlow': browser, 'resetCredentialsFlow': reset})
    stored = kc.request('GET', '')
    if stored.get('browserFlow') != browser or stored.get('resetCredentialsFlow') != reset:
        raise RuntimeError('MFA flow bindings did not persist')
    plan.update(browserFlow=browser, resetCredentialsFlow=reset)
    return plan


def _remove_mfa_executions(kc, alias):
    """Delete the role-gated subflow and the negated role conditions from ``alias``."""
    editor = FlowEditor(kc, alias)
    for execution in editor.executions():
        condition = _role_condition(kc, execution)
        if condition == (ROLE, True):
            kc.request('DELETE', '/authentication/executions/' + execution['id'])
    executions = editor.executions()
    for index, execution in enumerate(executions):
        if execution.get('authenticationFlow') and any(
                _role_condition(kc, k) == (ROLE, False) for k in children(executions, index)):
            kc.request('DELETE', '/authentication/executions/' + execution['id'])
            return


def rollback(base, realm, token):
    """Undo configure(): rebind the built-in browser flow and strip the reset-flow gates.

    Deleting only the role is NOT a rollback: Keycloak's conditional-user-role
    returns false for an unknown role even when negated (26.7.4 bytecode), which
    would silently switch off the OTP prompt for voluntarily enrolled users too.
    The role, the unbound computor-browser-mfa copy and the token mappers stay;
    they are inert. Pending CONFIGURE_TOTP actions stay too (other policies,
    such as the mail team's, set them); remove them per user if unwanted.
    """
    kc = Client(base, realm, token)
    settings = kc.request('GET', '')
    changes = {}
    flows = {f['alias']: f for f in kc.request('GET', '/authentication/flows')}
    for key, ours, builtin in (('browserFlow', BROWSER_FLOW, 'browser'),
                               ('resetCredentialsFlow', RESET_FLOW, 'reset credentials')):
        bound = settings.get(key) or builtin
        if bound == ours:
            changes[key] = builtin
        elif bound in flows and not flows[bound].get('builtIn'):
            _remove_mfa_executions(kc, bound)  # a copy made by someone else, edited in place
    if changes:
        kc.request('PUT', '', changes)
    stored = kc.request('GET', '')
    return {'browserFlow': stored.get('browserFlow'), 'resetCredentialsFlow': stored.get('resetCredentialsFlow')}


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
                        help='rebind the built-in browser flow and remove the reset-flow gates')
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
