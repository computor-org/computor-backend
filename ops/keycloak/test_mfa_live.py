#!/usr/bin/env python3
"""Admin TOTP checks against an isolated Keycloak 26.7; no production access (issues#485).

Starts a throwaway Keycloak container on an internal Docker network, creates a
random test realm, applies setup_mfa.configure() twice, and drives the real
login pages with a cookie-keeping HTTP client and an independent RFC 6238 TOTP
implementation. The ID tokens it receives are fed to the backend's evidence
check (computor_backend/auth/mfa.py) so the backend gate is tested against what
Keycloak actually emits. When the backend package is importable (run with
``uv run --project computor-backend``) the backend's Keycloak role sync is
exercised against the same realm as well.

Run: uv run --project computor-backend python ops/keycloak/test_mfa_live.py
"""
import asyncio
import base64
import contextlib
import email
import email.policy
import hashlib
import hmac
import html
import importlib.util
import itertools
import json
import os
import queue
import re
import struct
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import setup_mfa
from test_abuse_live import (
    CALLBACK,
    SMTP,
    Browser,
    Forms,
    MailServer,
    docker,
    require,
)

BACKEND_SRC = HERE.parents[1] / 'computor-backend' / 'src'
SECRET = 'mfa-live-client-secret'
PASSWORD = 'Isolated-Test-Password-1'


def load_mfa_module():
    spec = importlib.util.spec_from_file_location('backend_mfa', BACKEND_SRC / 'computor_backend' / 'auth' / 'mfa.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MFA = load_mfa_module()


def totp(secret, at=None, step=30, digits=6):
    """RFC 6238 over the raw secret bytes Keycloak keeps in the hidden totpSecret field."""
    counter = int((time.time() if at is None else at) // step)
    digest = hmac.new(secret.encode(), struct.pack('>Q', counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = (struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7FFFFFFF) % 10 ** digits
    return str(code).zfill(digits)


def fresh_window():
    """Wait for the start of a new 30 s window, so codes are never reused."""
    time.sleep(30 - time.time() % 30 + 0.5)


def claims(jwt):
    payload = jwt.split('.')[1]
    return json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)))


@contextlib.contextmanager
def isolated_keycloak():
    suffix = uuid.uuid4().hex[:10]
    network, kc = 'computor-mfa-test-' + suffix, 'computor-mfa-test-' + suffix + '-kc'
    smtp = None
    try:
        docker('network', 'create', '--internal', network)
        gateway = json.loads(docker('network', 'inspect', network))[0]['IPAM']['Config'][0]['Gateway']
        smtp = MailServer((gateway, 0), SMTP)
        smtp.received = queue.Queue()
        threading.Thread(target=smtp.serve_forever, daemon=True).start()
        docker('run', '-d', '--pull=never', '--name', kc, '--network', network,
               '-e', 'KC_BOOTSTRAP_ADMIN_USERNAME=admin', '-e', 'KC_BOOTSTRAP_ADMIN_PASSWORD=isolated-test',
               'quay.io/keycloak/keycloak:26.7.4', 'start-dev', '--http-host=0.0.0.0')
        address = json.loads(docker('inspect', kc))[0]['NetworkSettings']['Networks'][network]['IPAddress']
        base = 'http://' + address + ':8080'
        for _ in range(180):
            try:
                urllib.request.urlopen(base + '/realms/master', timeout=2).close()
                break
            except (OSError, urllib.error.URLError):
                require(json.loads(docker('inspect', kc))[0]['State']['Running'], 'Local Keycloak exited during startup')
                time.sleep(1)
        else:
            raise AssertionError('Local Keycloak did not start:\n' + docker('logs', kc)[-6000:])
        yield base, smtp, gateway
    except Exception:
        print('Local Keycloak diagnostics:\n' + docker('logs', '--tail', '65', kc, check=False), flush=True)
        raise
    finally:
        if smtp:
            smtp.shutdown()
            smtp.server_close()
        docker('rm', '-f', kc, check=False)
        docker('network', 'rm', network, check=False)


class Checks:
    def __init__(self, base, smtp, gateway, legacy):
        self.base, self.smtp, self.gateway, self.legacy = base, smtp, gateway, legacy
        self.realm = ('mfa-legacy-' if legacy else 'mfa-') + uuid.uuid4().hex[:8]
        self.root = '/admin/realms/' + self.realm
        self._token, self._token_at = None, 0.0
        self.checked, self.users, self.secrets = [], {}, {}

    @property
    def token(self):
        """Master admin token, renewed well inside admin-cli's 60 s lifespan."""
        if time.time() - self._token_at > 20:
            data = urllib.parse.urlencode({'grant_type': 'password', 'client_id': 'admin-cli', 'username': 'admin',
                                           'password': 'isolated-test'}).encode()
            with urllib.request.urlopen(self.base + '/realms/master/protocol/openid-connect/token', data,
                                        timeout=30) as res:
                self._token = json.loads(res.read())['access_token']
            self._token_at = time.time()
        return self._token

    def api(self, method, path, body=None, form=None):
        headers = {} if path.startswith('/realms/') else {'Authorization': 'Bearer ' + self.token}
        if form is not None:
            data = urllib.parse.urlencode(form).encode()
        elif body is not None:
            data = json.dumps(body).encode()
            headers['Content-Type'] = 'application/json'
        else:
            data = None
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=30) as res:
                raw = res.read()
                return res.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                return exc.code, json.loads(raw)
            except ValueError:
                return exc.code, raw.decode()[:500]

    def ok(self, label):
        self.checked.append(('legacy ' if self.legacy else '') + label)
        print('PASS ' + self.checked[-1], flush=True)

    # -- realm fixture -------------------------------------------------------
    def legacy_browser_flow(self):
        """computor.at's shape: pre-26.x browser flow (forms + OTP-if-configured), reset flow copy."""
        kc = setup_mfa.Client(self.base, self.realm, self.token)
        kc.request('POST', '/authentication/flows', {'alias': 'legacy browser', 'providerId': 'basic-flow',
                                                     'topLevel': True, 'builtIn': False})
        editor = setup_mfa.FlowEditor(kc, 'legacy browser')
        editor.add_execution('legacy browser', 'auth-cookie', 'ALTERNATIVE')
        kc.request('POST', '/authentication/flows/legacy%20browser/executions/flow',
                   {'alias': 'legacy forms', 'type': 'basic-flow', 'provider': 'registration-page-form'})
        forms = next(e for e in editor.executions() if e.get('displayName') == 'legacy forms')
        editor.set_requirement(forms, 'ALTERNATIVE')
        editor.add_execution('legacy forms', 'auth-username-password-form', 'REQUIRED')
        editor.add_subflow('legacy forms', 'legacy conditional otp', 'OTP if configured')
        editor.add_execution('legacy conditional otp', 'conditional-user-configured', 'REQUIRED')
        editor.add_execution('legacy conditional otp', 'auth-otp-form', 'REQUIRED')
        # Like setup_abuse.py's computor-reset-protected: a bound non-built-in copy.
        kc.request('POST', '/authentication/flows/reset%20credentials/copy', {'newName': 'legacy reset'})
        kc.request('PUT', '', {'browserFlow': 'legacy browser', 'resetCredentialsFlow': 'legacy reset'})

    def setup(self):
        status, _ = self.api('POST', '/admin/realms', {
            'realm': self.realm, 'enabled': True, 'resetPasswordAllowed': True,
            'smtpServer': {'host': self.gateway, 'port': str(self.smtp.server_address[1]),
                           'from': 'test@example.invalid', 'ssl': 'false', 'starttls': 'false', 'auth': 'false'}})
        require(status == 201, f'Failed to create isolated realm: {status}')
        status, _ = self.api('POST', self.root + '/clients', {
            'clientId': 'computor-backend', 'enabled': True, 'publicClient': False, 'secret': SECRET,
            'standardFlowEnabled': True, 'directAccessGrantsEnabled': False, 'redirectUris': [CALLBACK]})
        require(status == 201, 'Failed to create backend client')
        self.api('POST', self.root + '/groups', {'name': 'administrators'})
        for name in ('student', 'staff', 'voluntary', 'groupadmin', 'formerstaff'):
            status, _ = self.api('POST', self.root + '/users', {
                'username': name, 'email': name + '@example.invalid', 'enabled': True, 'emailVerified': True,
                'firstName': 'Integration', 'lastName': name,
                'credentials': [{'type': 'password', 'value': PASSWORD, 'temporary': False}]})
            require(status == 201, f'Create user {name} failed: {status}')
            self.users[name] = self.api('GET', self.root + '/users?exact=true&username=' + name)[1][0]['id']
        group = self.api('GET', self.root + '/groups?exact=true&search=administrators')[1][0]
        self.api('PUT', self.root + '/users/' + self.users['groupadmin'] + '/groups/' + group['id'])
        if self.legacy:
            self.legacy_browser_flow()
        self.before = self.flow_shape()
        first = setup_mfa.configure(self.base, self.realm, self.token)
        shape = self.shape = self.flow_shape()
        second = setup_mfa.configure(self.base, self.realm, self.token)
        require(first == second, f'configure() result changed on re-run: {first} vs {second}')
        require(self.flow_shape() == shape, 'configure() is not idempotent: flow executions changed on re-run')
        require(shape['browser'].count(('conditional-user-role', 'REQUIRED')) == 2 and
                shape['browser'][-1] == ('auth-otp-form', 'REQUIRED'), f'Unexpected browser flow: {shape}')
        self.ok('setup_mfa.configure() creates role, flows and mappers and is idempotent')

    def flow_shape(self):
        realm = self.api('GET', self.root)[1]
        shape = {}
        for key, name in (('browser', realm['browserFlow']), ('reset', realm['resetCredentialsFlow'])):
            executions = self.api('GET', self.root + '/authentication/flows/' + urllib.parse.quote(name, safe='') +
                                  '/executions')[1]
            shape[key] = [(e.get('providerId') or 'subflow', e['requirement']) for e in executions]
        client = self.api('GET', self.root + '/clients?clientId=computor-backend')[1][0]
        shape['mappers'] = sorted(m['protocolMapper'] for m in client.get('protocolMappers', []))
        return shape

    # -- backend role sync ---------------------------------------------------
    def apply(self, *names):
        """Make exactly ``names`` hold the role, the way the backend sync does it.

        Uses the backend's own apply_keycloak_membership() when the package is
        importable; otherwise an equivalent admin-API fallback (reported).
        """
        try:
            from computor_backend.auth.keycloak_admin import KeycloakAdminClient
            from computor_backend.business_logic import admin_mfa
        except ImportError:
            admin_mfa = None
        if admin_mfa is not None:
            os.environ.update(KEYCLOAK_SERVER_URL=self.base, KEYCLOAK_REALM=self.realm, KEYCLOAK_ADMIN='admin',
                              KEYCLOAK_ADMIN_PASSWORD='isolated-test', KEYCLOAK_AUTOMATION_CLIENT_ID='',
                              KEYCLOAK_AUTOMATION_CLIENT_SECRET='')
            summary = asyncio.run(admin_mfa.apply_keycloak_membership(
                {self.users[n] for n in names}, prune=True, kc=KeycloakAdminClient()))
            self.via = 'backend admin_mfa.apply_keycloak_membership'
            return summary
        role = self.api('GET', self.root + '/roles/' + setup_mfa.ROLE)[1]
        members = {u['id'] for u in self.api('GET', self.root + '/roles/' + setup_mfa.ROLE + '/users')[1]}
        for name in names:
            if self.users[name] not in members:
                self.api('POST', self.root + '/users/' + self.users[name] + '/role-mappings/realm', [role])
                self.api('PUT', self.root + '/users/' + self.users[name], {'requiredActions': ['CONFIGURE_TOTP']})
        for uid in members - {self.users[n] for n in names}:
            self.api('DELETE', self.root + '/users/' + uid + '/role-mappings/realm', [role])
        self.via = 'admin API fallback (backend package not importable)'
        return None

    def realm_roles(self, name):
        return [r['name'] for r in self.api('GET', self.root + '/users/' + self.users[name] + '/role-mappings/realm')[1]]

    # -- browser helpers -----------------------------------------------------
    def browser(self):
        browser = Browser()
        browser.visit(self.authorize_url())
        return browser

    def authorize_url(self):
        return self.base + '/realms/' + self.realm + '/protocol/openid-connect/auth?' + urllib.parse.urlencode({
            'client_id': 'computor-backend', 'redirect_uri': CALLBACK, 'response_type': 'code',
            'scope': 'openid', 'state': uuid.uuid4().hex})

    def password(self, browser, name):
        return browser.submit('kc-form-login', username=name, password=PASSWORD)

    def tokens(self, browser):
        url, _, done = browser.page
        require(done, f'Login did not complete; at {url}')
        code = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)['code'][0]
        status, body = self.api('POST', '/realms/' + self.realm + '/protocol/openid-connect/token', form={
            'grant_type': 'authorization_code', 'code': code, 'redirect_uri': CALLBACK,
            'client_id': 'computor-backend', 'client_secret': SECRET})
        require(status == 200, f'Code exchange failed: {status} {body}')
        return body

    def refresh(self, tokens):
        status, body = self.api('POST', '/realms/' + self.realm + '/protocol/openid-connect/token', form={
            'grant_type': 'refresh_token', 'refresh_token': tokens['refresh_token'],
            'client_id': 'computor-backend', 'client_secret': SECRET})
        require(status == 200, f'Refresh failed: {status} {body}')
        return body

    def reset(self, name):
        """Forgot password -> mail -> follow the action link."""
        browser = self.browser()
        link = next(link for link in re.findall(r'href="([^"]+)"', browser.page[1]) if '/reset-credentials?' in link)
        browser.visit(urllib.parse.urljoin(browser.page[0], html.unescape(link)))
        browser.submit('kc-reset-password-form', username=name)
        raw = self.smtp.received.get(timeout=30)
        message = email.message_from_bytes(raw, policy=email.policy.default)
        body = message.get_body(preferencelist=('plain',)) if message.is_multipart() else message
        action = next(u.rstrip('.,') for u in re.findall(r'https?://[^\s<>]+', body.get_content()) if 'action-token' in u)
        require(action.startswith(self.base + '/'), 'Mail action points outside isolated Keycloak')
        browser.visit(action)
        return browser

    def page_forms(self, browser):
        return [f['id'] for f in Forms(browser.page[1]).forms]

    def enroll(self, browser, name):
        page = browser.page[1]
        require('totpSecret' in page, f'{name}: expected the authenticator set-up page, got forms {self.page_forms(browser)}')
        secret = Forms(page).form('kc-totp-settings-form')['fields']['totpSecret']
        self.secrets[name] = secret
        browser.submit('kc-totp-settings-form', totp=totp(secret), userLabel='live-test')
        return browser

    def otp(self, browser, name, code=None):
        require('kc-otp-login-form' in self.page_forms(browser),
                f'{name}: expected the OTP page, got forms {self.page_forms(browser)}')
        return browser.submit('kc-otp-login-form', otp=code or totp(self.secrets[name]))

    def record(self, label, token_set):
        id_claims = claims(token_set['id_token'])
        evidence = MFA.has_mfa_evidence(id_claims)
        self.evidence[label] = {'amr': id_claims.get('amr'), 'acr': id_claims.get('acr'), 'mfa': evidence}
        return evidence

    # -- scenarios -----------------------------------------------------------
    def run_checks(self):
        self.evidence = {}

        browser = self.browser()
        self.password(browser, 'student')
        student = self.tokens(browser)
        require(not self.record('student password login', student), 'Student token unexpectedly carries MFA evidence')
        self.ok('ordinary user signs in with password only; no MFA evidence (no elevated rights to gate)')

        self.apply('staff', 'formerstaff')
        require(setup_mfa.ROLE in self.realm_roles('staff'), 'Role not granted')
        again = self.apply('staff', 'formerstaff')
        require(again is None or not any(again.values()), f'Sync is not idempotent: {again}')
        actions = self.api('GET', self.root + '/users/' + self.users['staff'])[1].get('requiredActions', [])
        require('CONFIGURE_TOTP' in actions, f'CONFIGURE_TOTP not set: {actions}')
        self.ok(f'role holder gets {setup_mfa.ROLE} and CONFIGURE_TOTP via {self.via}')

        browser = self.browser()
        self.password(browser, 'staff')
        self.enroll(browser, 'staff')
        enrolled = self.tokens(browser)
        self.record('enrolment login (password + CONFIGURE_TOTP)', enrolled)
        self.ok('role holder without authenticator is forced to enrol TOTP at sign-in')

        fresh_window()
        browser = self.browser()
        self.password(browser, 'staff')
        self.otp(browser, 'staff', code='000000' if totp(self.secrets['staff']) != '000000' else '111111')
        require('kc-otp-login-form' in self.page_forms(browser), 'Wrong OTP code was accepted')
        self.otp(browser, 'staff')
        staff = self.tokens(browser)
        require(self.record('password + OTP login', staff), f'No MFA evidence after OTP login: {self.evidence}')
        self.ok('role holder must enter a valid OTP exactly once; ID token amr carries the evidence')

        browser.visit(self.authorize_url())
        again = self.tokens(browser)
        require(self.record('SSO cookie re-authentication', again), 'MFA evidence lost on cookie SSO')
        require(self.record('refresh-token grant', self.refresh(staff)), 'MFA evidence lost on refresh')
        self.ok('evidence survives SSO-cookie re-authentication and refresh-token grants')

        fresh_window()
        browser = self.reset('staff')
        require('kc-otp-login-form' in self.page_forms(browser),
                f'E-mail reset of a role holder did not ask for the OTP: {self.page_forms(browser)}')
        self.otp(browser, 'staff')
        require('password-new' in Forms(browser.page[1]).forms[0]['fields'], 'No password update after OTP')
        browser.submit(Forms(browser.page[1]).forms[0]['id'], **{'password-new': PASSWORD, 'password-confirm': PASSWORD})
        require(self.record('e-mail reset + OTP', self.tokens(browser)), 'Reset login lacks OTP evidence')
        credentials = self.api('GET', self.root + '/users/' + self.users['staff'] + '/credentials')[1]
        require(any(c['type'] == 'otp' for c in credentials), 'E-mail reset removed the authenticator')
        self.ok('e-mail password reset of a role holder requires the current OTP and keeps the authenticator')

        browser = self.browser()
        self.password(browser, 'formerstaff')
        self.enroll(browser, 'formerstaff')
        self.tokens(browser)
        self.apply('staff')
        require(setup_mfa.ROLE not in self.realm_roles('formerstaff'), 'Role not revoked')
        require(setup_mfa.ROLE in self.realm_roles('staff'), 'Prune removed a current role holder')
        self.ok('revocation removes the role from former holders only')

        fresh_window()
        browser = self.browser()
        self.password(browser, 'formerstaff')
        self.otp(browser, 'formerstaff')
        self.record('former holder, voluntary authenticator', self.tokens(browser))
        self.ok('a user who keeps an enrolled authenticator is still asked for it once (pre-existing behaviour)')

        browser = self.browser()
        self.password(browser, 'groupadmin')
        require('totpSecret' in browser.page[1], 'administrators group member was not forced to enrol TOTP')
        self.ok('administrators group carries the role, so bootstrap admins must enrol too')

        realm = self.api('GET', self.root)[1]
        reset = self.api('GET', self.root + '/authentication/flows/' +
                         urllib.parse.quote(realm['resetCredentialsFlow'], safe='') + '/executions')[1]
        conditions = [setup_mfa._role_condition(setup_mfa.Client(self.base, self.realm, self.token), e)
                      for e in reset if e.get('providerId') == 'conditional-user-role']
        require(sorted(conditions) == [(setup_mfa.ROLE, False), (setup_mfa.ROLE, True)],
                f'Reset flow lacks the role gates: {conditions}')
        require(('auth-otp-form', 'REQUIRED') in [(e.get('providerId'), e['requirement']) for e in reset],
                'Reset flow does not require OTP for role holders')
        self.ok('reset-credentials flow requires OTP from role holders and keeps their authenticator (structure)')

        result = setup_mfa.rollback(self.base, self.realm, self.token)
        after = self.flow_shape()
        require({k: after[k] for k in ('browser', 'reset')} == {k: self.before[k] for k in ('browser', 'reset')},
                f'Rollback did not restore the original flows: {result}')
        browser = self.browser()
        self.password(browser, 'groupadmin')
        require(browser.page[2], 'After rollback a user without authenticator is still forced to enrol')
        fresh_window()
        browser = self.browser()
        self.password(browser, 'staff')
        self.otp(browser, 'staff')
        self.tokens(browser)
        self.ok('rollback restores the original flows; voluntary OTP still asked, nobody forced to enrol')
        setup_mfa.configure(self.base, self.realm, self.token)
        require(self.flow_shape() == self.shape, 'Re-applying after rollback differs from the first apply')
        self.ok('configure() after rollback reproduces the same realm state')

    # -- interruption ----------------------------------------------------------
    @contextlib.contextmanager
    def interrupted_at(self, call, after):
        """Make setup_mfa's ``call``-th admin request fail, before sending or after it was applied."""
        real, count = setup_mfa._request, [0]

        def flaky(*args, **kwargs):
            count[0] += 1
            if count[0] == call and not after:
                raise ConnectionError(f'injected failure before call {call}')
            result = real(*args, **kwargs)
            if count[0] == call:
                raise ConnectionError(f'injected failure after call {call}')
            return result

        setup_mfa._request = flaky
        try:
            yield count
        finally:
            setup_mfa._request = real

    def flows(self):
        return sorted(f['alias'] for f in self.api('GET', self.root + '/authentication/flows')[1])

    def bound_shape(self):
        shape = self.flow_shape()
        return {k: shape[k] for k in ('browser', 'reset')}

    def interruption_checks(self):
        """configure()/rollback() interrupted at every admin call against the real server."""
        setup_mfa.rollback(self.base, self.realm, self.token)
        before, before_flows = self.bound_shape(), self.flows()
        configured = {k: self.shape[k] for k in ('browser', 'reset')}
        with self.interrupted_at(0, False) as count:
            setup_mfa.configure(self.base, self.realm, self.token)
        total = count[0]
        setup_mfa.rollback(self.base, self.realm, self.token)
        for call in range(1, total + 1):
            for after in (False, True):
                with self.interrupted_at(call, after):
                    try:
                        setup_mfa.configure(self.base, self.realm, self.token)
                    except ConnectionError:
                        pass
                    else:
                        raise AssertionError(f'call {call} was not interrupted')
                state = self.bound_shape()
                require(state in (before, configured), f'call {call}: bound flows half-configured: {state}')
                if after:
                    setup_mfa.configure(self.base, self.realm, self.token)
                    require(self.bound_shape() == configured, f'call {call}: retry did not converge')
                setup_mfa.rollback(self.base, self.realm, self.token)
                require(self.bound_shape() == before and self.flows() == before_flows,
                        f'call {call}: rollback left {sorted(set(self.flows()) - set(before_flows))}')
        self.ok(f'configure() interrupted at each of its {total} admin calls never binds a partial flow; '
                'retry converges and rollback leaves no orphans')
        rollback_calls = None
        for call in itertools.count(1):
            setup_mfa.configure(self.base, self.realm, self.token)
            with self.interrupted_at(call, call % 2 == 0) as count:
                try:
                    setup_mfa.rollback(self.base, self.realm, self.token)
                except ConnectionError:
                    pass
                else:
                    rollback_calls = count[0]
            require(self.bound_shape() in (before, configured), f'rollback call {call}: half rolled back')
            setup_mfa.rollback(self.base, self.realm, self.token)
            require(self.bound_shape() == before and self.flows() == before_flows, f'rollback call {call}')
            if rollback_calls is not None:
                break
        self.ok(f'rollback() interrupted at each of its {rollback_calls} admin calls can be re-run')
        setup_mfa.configure(self.base, self.realm, self.token)
        require(self.flow_shape() == self.shape, 'configure() after the interruption runs differs')

    def run(self):
        try:
            self.setup()
            self.run_checks()
            self.interruption_checks()
            return {'realm': self.realm, 'legacy': self.legacy, 'checks': self.checked, 'evidence': self.evidence}
        finally:
            self.api('DELETE', self.root)


if __name__ == '__main__':
    with isolated_keycloak() as (base, smtp, gateway):
        results = [Checks(base, smtp, gateway, legacy=False).run(), Checks(base, smtp, gateway, legacy=True).run()]
    print(json.dumps({'liveKeycloakAdminMfa': 'passed', 'runs': results}, indent=2), flush=True)
