#!/usr/bin/env python3
"""Reconcile optional Computor signup/recovery protection; dry-run unless --apply."""
import argparse
import json
import os
from pathlib import Path
import shlex
import urllib.parse

from setup_identity_providers import _request, get_admin_token

REGISTRATION = 'computor-registration-protected'
RESET = 'computor-reset-protected'
PROTECTED_ATTRIBUTES = ('computor.selfRegistered', 'computor.selfRegisteredAt', 'computor.lastLogin')
# Lifetime of the address-verification link in seconds. Keycloak's default for
# user-generated action tokens is 5 minutes, which a new learner who opens the
# mail later cannot meet (issues#478); a day leaves room for a delayed mail.
VERIFY_EMAIL_LIFESPAN = 86400
VERIFY_EMAIL_LIFESPAN_ATTRIBUTE = 'actionTokenGeneratedByUserLifespan.verify-email'


def canonical_gmail(address):
    local, sep, domain = (address or '').strip().rpartition('@')
    if not sep or domain.lower() != 'gmail.com':
        return None
    return local.lower().split('+', 1)[0].replace('.', '') + '@gmail.com'


class Client:
    def __init__(self, base, realm, token):
        self.base = base.rstrip('/')
        self.root = self.base + '/admin/realms/' + urllib.parse.quote(realm, safe='')
        self.token = token

    def request(self, method, path, body=None):
        status, result = _request(method, self.root + path, token=self.token, json_body=body)
        if status not in (200, 201, 204):
            raise RuntimeError(f'{method} {path.split("?")[0]} failed: HTTP {status}')
        return result


def configure(base, realm, token, secret, apply=True, backup=None, cost=10000, ttl=300):
    if len(secret) < 32:
        raise ValueError('CAPTCHA secret must contain at least 32 characters')
    if not 1000 <= cost <= 100000 or not 30 <= ttl <= 900:
        raise ValueError('CAPTCHA cost/TTL outside supported rollout bounds')
    kc = Client(base, realm, token)
    settings = kc.request('GET', '')
    storage = kc.request('GET', '/components?type=org.keycloak.storage.UserStorageProvider')
    if any(component.get('config', {}).get('enabled', ['true']) != ['false'] for component in storage):
        raise RuntimeError('Gmail uniqueness requires local persisted users; external user storage needs separate support')
    profile = kc.request('GET', '/users/profile')
    groups = {}
    first = 0
    while True:
        users = kc.request('GET', '/users?first=' + str(first) + '&max=100')
        for user in users:
            key = canonical_gmail(user.get('email'))
            if key:
                groups.setdefault(key, []).append(user['id'])
        first += len(users)
        if len(users) < 100:
            break
    collisions = sum(len(ids) > 1 for ids in groups.values())
    result = {'gmailCollisionGroups': collisions, 'registrationFlow': REGISTRATION,
              'resetCredentialsFlow': RESET, 'applied': apply}
    if not apply:
        return result
    providers = kc.request('GET', '/authentication/form-action-providers')
    authenticators = kc.request('GET', '/authentication/authenticator-providers')
    if not any(p['id'] == 'computor-registration-abuse' for p in providers) or not any(
            p['id'] == 'computor-reset-abuse' for p in authenticators):
        raise RuntimeError('Abuse provider JAR is not loaded; install it before binding flows')
    if backup:
        path = Path(backup)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump({'realm': settings, 'profile': profile}, stream, indent=2)
    for attribute in profile['attributes']:
        if attribute['name'] == 'email':
            attribute.setdefault('validations', {})['computor-gmail-unique'] = {}
    if not any(a['name'] == 'email' for a in profile['attributes']):
        raise RuntimeError('Realm profile has no email attribute')
    for name in PROTECTED_ATTRIBUTES:
        current = next((a for a in profile['attributes'] if a['name'] == name), None)
        if current is None:
            current = {'name': name, 'multivalued': False}
            profile['attributes'].append(current)
        current['permissions'] = {'view': ['admin'], 'edit': ['admin']}
    kc.request('PUT', '/users/profile', profile)

    def flow(alias, source):
        flows = kc.request('GET', '/authentication/flows')
        if not any(f['alias'] == alias for f in flows):
            kc.request('POST', '/authentication/flows/' + urllib.parse.quote(source, safe='') + '/copy',
                       {'newName': alias})
        return kc.request('GET', '/authentication/flows/' + alias + '/executions')

    registration = flow(REGISTRATION, settings.get('registrationFlow') or 'registration')
    reset = flow(RESET, settings.get('resetCredentialsFlow') or 'reset credentials')
    parent = next((e for e in registration if e.get('authenticationFlow') and
                   e.get('providerId') == 'registration-page-form'), None)
    if parent is None:
        # Keycloak versions may omit providerId in execution-info representations.
        parent = next((e for e in registration if e.get('authenticationFlow') and e.get('level') == 0), None)
    if parent is None:
        raise RuntimeError('Cannot locate registration form subflow')

    config = {'secret': secret, 'ttlSeconds': str(ttl), 'cost': str(cost)}

    def ensure_execution(alias, parent_alias, provider):
        path = '/authentication/flows/' + urllib.parse.quote(alias, safe='') + '/executions'
        executions = kc.request('GET', path)
        found = next((e for e in executions if e.get('providerId') == provider), None)
        if found is None:
            kc.request('POST', '/authentication/flows/' + urllib.parse.quote(parent_alias, safe='') +
                       '/executions/execution', {'provider': provider})
            found = next(e for e in kc.request('GET', path) if e.get('providerId') == provider)
        if found.get('requirement') != 'REQUIRED':
            kc.request('PUT', path, dict(found, requirement='REQUIRED'))
        if found.get('authenticationConfig'):
            cp = '/authentication/config/' + found['authenticationConfig']
            old = kc.request('GET', cp)
            if old.get('config') != config:
                kc.request('PUT', cp, dict(old, config=config))
        else:
            kc.request('POST', '/authentication/executions/' + found['id'] + '/config',
                       {'alias': provider + '-settings', 'config': config})
        return found

    ensure_execution(REGISTRATION, parent['displayName'], 'computor-registration-abuse')
    replacement = ensure_execution(RESET, RESET, 'computor-reset-abuse')
    reset_path = '/authentication/flows/' + RESET + '/executions'
    for execution in kc.request('GET', reset_path):
        if execution.get('providerId') == 'reset-credentials-choose-user' and execution['requirement'] != 'DISABLED':
            kc.request('PUT', reset_path, dict(execution, requirement='DISABLED'))
    for _ in range(len(reset) + 2):
        executions = kc.request('GET', reset_path)
        if executions[0]['id'] == replacement['id']:
            break
        kc.request('POST', '/authentication/executions/' + replacement['id'] + '/raise-priority')
    else:
        raise RuntimeError('Cannot place reset protection before outbound-mail executions')
    listeners = list(settings.get('eventsListeners') or [])
    if 'computor-registration-activity' not in listeners:
        listeners.append('computor-registration-activity')
    kc.request('PUT', '', {'registrationFlow': REGISTRATION, 'resetCredentialsFlow': RESET,
                          'eventsListeners': listeners,
                          'attributes': {VERIFY_EMAIL_LIFESPAN_ATTRIBUTE: str(VERIFY_EMAIL_LIFESPAN)}})
    stored = kc.request('GET', '')
    if stored.get('registrationFlow') != REGISTRATION or stored.get('resetCredentialsFlow') != RESET:
        raise RuntimeError('Protected flow bindings did not persist')
    if (stored.get('attributes') or {}).get(VERIFY_EMAIL_LIFESPAN_ATTRIBUTE) != str(VERIFY_EMAIL_LIFESPAN):
        raise RuntimeError('Verification link lifespan did not persist')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env')
    parser.add_argument('--base-url')
    parser.add_argument('--realm')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--backup')
    parser.add_argument('--restore', help='restore profile and flow bindings from a private rollout snapshot')
    args = parser.parse_args()
    if args.env:
        for line in Path(args.env).read_text().splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key, value = line.split('=', 1)
                parts = shlex.split(value, comments=False)
                os.environ[key.strip()] = parts[0] if parts else ''
    if os.environ.get('KEYCLOAK_ABUSE_PROTECTION') != 'true':
        raise SystemExit('Set KEYCLOAK_ABUSE_PROTECTION=true for the intended deployment')
    base = args.base_url or (('http://127.0.0.1:' + os.environ.get('KEYCLOAK_PORT', '8180') +
                            os.environ.get('KEYCLOAK_HTTP_RELATIVE_PATH', '/').rstrip('/')) if args.env else
                           (os.environ.get('KEYCLOAK_SERVER_URL_INTERNAL') or os.environ['KEYCLOAK_SERVER_URL']))
    realm = args.realm or os.environ.get('KEYCLOAK_REALM', 'computor')
    secret = os.environ.get('KEYCLOAK_ABUSE_SECRET', '')
    if not secret:
        raise SystemExit('Set persistent KEYCLOAK_ABUSE_SECRET (32+ random characters)')
    token = get_admin_token(base, os.environ.get('KEYCLOAK_ADMIN'), os.environ.get('KEYCLOAK_ADMIN_PASSWORD'))
    if args.restore:
        saved = json.loads(Path(args.restore).read_text())
        kc = Client(base, realm, token)
        kc.request('PUT', '', {key: saved['realm'][key] for key in
                              ('registrationFlow', 'resetCredentialsFlow', 'eventsListeners')})
        kc.request('PUT', '/users/profile', saved['profile'])
        print('Previous profile and authentication bindings restored.')
        return
    print(json.dumps(configure(base, realm, token, secret, apply=args.apply, backup=args.backup,
                               cost=int(os.environ.get('KEYCLOAK_ABUSE_COST', '10000')),
                               ttl=int(os.environ.get('KEYCLOAK_ABUSE_TTL', '300')))))


if __name__ == '__main__':
    main()
