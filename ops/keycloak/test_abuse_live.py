#!/usr/bin/env python3
"""Isolated PostgreSQL/Keycloak integration checks; no external SMTP or production access.

Build the provider first (see ops/README.md), then run this file. Only locally
available Docker images are used; temporary containers, network and realm are
removed on success and failure. Python's independent PBKDF2 solver exercises the
actual HTTP form handlers, not a mock or the Java library's own solver.
"""
import argparse
import base64
import concurrent.futures
import contextlib
import email
import email.policy
import hashlib
import html
import http.cookiejar
import json
import os
import queue
import re
import secrets
import socketserver
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
CALLBACK = 'http://127.0.0.1:1/abuse-test-complete'


def docker(*args, check=True):
    return subprocess.run(['docker', *args], check=check, text=True, capture_output=True).stdout.strip()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


class Forms(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.forms, self.current, self.challenge = [], None, None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == 'form':
            self.current = {'id': d.get('id'), 'action': d.get('action'), 'fields': {}, 'buttons': []}
            self.forms.append(self.current)
        elif tag == 'altcha-widget':
            self.challenge = json.loads(d.get('challengejson') or d.get('challenge'))
        elif self.current is not None and tag == 'input' and d.get('name'):
            if d.get('type') in ('submit', 'button'):
                self.current['buttons'].append(d['name'])
            else:
                self.current['fields'][d['name']] = d.get('value', '')
        elif self.current is not None and tag == 'button' and d.get('name'):
            self.current['buttons'].append(d['name'])

    def handle_endtag(self, tag):
        if tag == 'form':
            self.current = None

    def form(self, form_id):
        for form in self.forms:
            if form['id'] == form_id or (form_id == 'kc-terms-form' and 'accept' in form['buttons']):
                return form
        raise AssertionError(f'Missing {form_id}; found {[f["id"] for f in self.forms]}')


class Redirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, url):
        if url.startswith(CALLBACK):
            return None
        return super().redirect_request(req, fp, code, msg, headers, url)


class Browser:
    def __init__(self):
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()), Redirects())
        self.page = None

    def visit(self, url, fields=None):
        data = urllib.parse.urlencode(fields).encode() if fields is not None else None
        try:
            with self.opener.open(urllib.request.Request(url, data=data), timeout=30) as response:
                self.page = (response.url, response.read().decode(), False)
        except urllib.error.HTTPError as exc:
            location = exc.headers.get('Location', '')
            if exc.code in (302, 303) and location.startswith(CALLBACK):
                self.page = (location, '', 'code=' in location)
            else:
                body = exc.read().decode()
                if exc.code == 400:
                    self.page = (exc.url, body, False)
                else:
                    raise AssertionError(f'Browser HTTP {exc.code}: {body[:500]}') from None
        return self.page

    def submit(self, form_id, **changes):
        form = Forms(self.page[1]).form(form_id)
        fields = dict(form['fields'])
        fields.update(changes)
        return self.visit(urllib.parse.urljoin(self.page[0], form['action']), fields)


def proof(challenge, solve=True):
    """Official ALTCHA v2 binary password: nonce || unsigned big-endian counter."""
    params = challenge['parameters']
    require(params['algorithm'] == 'PBKDF2/SHA-256', 'Unexpected KDF')
    for counter in range(100000):
        derived = hashlib.pbkdf2_hmac('sha256', bytes.fromhex(params['nonce']) + counter.to_bytes(4, 'big'),
                                      bytes.fromhex(params['salt']), params['cost'], params['keyLength']).hex()
        if derived.startswith(params['keyPrefix']) == solve:
            payload = {'challenge': challenge, 'solution': {'counter': counter, 'derivedKey': derived, 'time': 0}}
            return base64.b64encode(json.dumps(payload).encode()).decode()
    raise AssertionError('Independent proof solver exhausted bounded counter space')


class SMTP(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(15)
        self.wfile.write(b'220 isolated-test ESMTP\r\n')
        while True:
            line = self.rfile.readline()
            if not line:
                return
            command = line.split(b' ', 1)[0].strip().upper()
            if command == b'EHLO':
                self.wfile.write(b'250-isolated-test\r\n250 SIZE 1000000\r\n')
            elif command == b'DATA':
                self.wfile.write(b'354 send data\r\n')
                chunks = []
                while True:
                    part = self.rfile.readline()
                    if part == b'.\r\n':
                        break
                    if not part:
                        return
                    chunks.append(part[1:] if part.startswith(b'..') else part)
                self.server.received.put(b''.join(chunks))
                self.wfile.write(b'250 accepted\r\n')
            elif command == b'QUIT':
                self.wfile.write(b'221 bye\r\n')
                return
            else:
                self.wfile.write(b'250 ok\r\n')


class MailServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


@contextlib.contextmanager
def isolated_keycloak(provider=None):
    suffix = uuid.uuid4().hex[:10]
    network, db, kc = ['computor-abuse-test-' + suffix + tail for tail in ('', '-db', '-kc')]
    jars = [Path(provider).resolve()] if provider else list((HERE / 'abuse-provider/target').glob('*-all.jar'))
    if not jars:
        jars = [p for p in (HERE / 'abuse-provider/target').glob('*.jar') if not p.name.startswith('original-')]
    require(len(jars) == 1, 'Build the provider JAR before running integration tests')
    smtp = None
    try:
        docker('network', 'create', '--internal', network)
        gateway = json.loads(docker('network', 'inspect', network))[0]['IPAM']['Config'][0]['Gateway']
        smtp = MailServer((gateway, 0), SMTP)
        smtp.received = queue.Queue()
        threading.Thread(target=smtp.serve_forever, daemon=True).start()
        docker('run', '-d', '--pull=never', '--name', db, '--network', network,
               '-e', 'POSTGRES_DB=keycloak', '-e', 'POSTGRES_USER=keycloak', '-e', 'POSTGRES_PASSWORD=isolated-test', 'postgres:16.15')
        for _ in range(90):
            if 'accepting connections' in docker('exec', db, 'pg_isready', '-h', '127.0.0.1', '-U', 'keycloak', check=False):
                break
            time.sleep(1)
        else:
            raise AssertionError('Local PostgreSQL did not start')
        docker('run', '-d', '--pull=never', '--name', kc, '--network', network,
               '-e', 'KC_BOOTSTRAP_ADMIN_USERNAME=admin', '-e', 'KC_BOOTSTRAP_ADMIN_PASSWORD=isolated-test',
               '-e', 'KC_DB=postgres', '-e', f'KC_DB_URL=jdbc:postgresql://{db}:5432/keycloak',
               '-e', 'KC_DB_USERNAME=keycloak', '-e', 'KC_DB_PASSWORD=isolated-test',
               '-v', f'{jars[0]}:/opt/keycloak/providers/computor-abuse.jar:ro',
               '-v', f'{HERE.parents[1]}/data/keycloak/themes/computor:/opt/keycloak/themes/computor:ro',
               'quay.io/keycloak/keycloak:26.7.4', 'start-dev', '--http-host=0.0.0.0',
               '--spi-theme-static-max-age=-1', '--spi-theme-cache-themes=false', '--spi-theme-cache-templates=false')
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
        docker('rm', '-f', kc, db, check=False)
        docker('network', 'rm', network, check=False)


class Checks:
    def __init__(self, base, smtp, gateway):
        self.base, self.smtp, self.gateway = base, smtp, gateway
        self.realm = 'abuse-' + uuid.uuid4().hex[:10]
        self.root = '/admin/realms/' + self.realm
        self.token = None
        self.token = self.api('POST', '/realms/master/protocol/openid-connect/token', form={
            'grant_type': 'password', 'client_id': 'admin-cli', 'username': 'admin', 'password': 'isolated-test'})[1]['access_token']
        self.checked = []

    def api(self, method, path, body=None, form=None):
        headers = {'Authorization': 'Bearer ' + self.token} if self.token else {}
        if form is not None:
            data = urllib.parse.urlencode(form).encode()
        elif body is not None:
            data = json.dumps(body).encode()
            headers['Content-Type'] = 'application/json'
        else:
            data = None
        try:
            with urllib.request.urlopen(urllib.request.Request(self.base + path, data=data, headers=headers, method=method), timeout=30) as res:
                raw = res.read()
                return res.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                value = json.loads(raw)
            except ValueError:
                value = raw.decode()[:500]
            return exc.code, value

    def ok(self, label):
        self.checked.append(label)
        print('PASS ' + label, flush=True)

    def users(self, username=None):
        query = '?username=' + urllib.parse.quote(username) + '&exact=true' if username else '?max=1000'
        status, users = self.api('GET', self.root + '/users' + query)
        require(status == 200, f'Get users failed: {status}')
        return users

    def create(self, username, address, **extra):
        return self.api('POST', self.root + '/users', {'username': username, 'email': address, 'enabled': True,
                        'emailVerified': True, 'firstName': 'Integration', 'lastName': 'Test', **extra})

    def authorization_url(self, kind='registrations'):
        query = urllib.parse.urlencode({'client_id': 'integration', 'redirect_uri': CALLBACK, 'response_type': 'code',
                                         'scope': 'openid', 'state': uuid.uuid4().hex})
        return self.base + '/realms/' + self.realm + '/protocol/openid-connect/' + kind + '?' + query

    def browser(self, kind='registrations'):
        browser = Browser()
        browser.visit(self.authorization_url(kind))
        return browser

    def reset(self):
        browser = self.browser('auth')
        links = re.findall(r'href="([^"]+)"', browser.page[1])
        link = next(link for link in links if '/reset-credentials?' in link)
        browser.visit(urllib.parse.urljoin(browser.page[0], html.unescape(link)))
        return browser

    def signup(self, username, address, browser=None, payload=None, **extra):
        browser = browser or self.browser()
        challenge = Forms(browser.page[1]).challenge
        if payload is None:
            payload = proof(challenge)
        browser.submit('kc-register-form', username=username, email=address, firstName='Integration', lastName='Test', altcha=payload, **extra)
        return browser

    def no_mail(self):
        require(self.smtp.received.empty(), 'Unexpected SMTP message')

    def mail_link(self):
        raw = self.smtp.received.get(timeout=15)
        msg = email.message_from_bytes(raw, policy=email.policy.default)
        body = msg.get_body(preferencelist=('plain',)) if msg.is_multipart() else msg
        link = next(u.rstrip('.,') for u in re.findall(r'https?://[^\s<>]+', body.get_content()) if 'action-token' in u)
        require(link.startswith(self.base + '/'), 'Mail action points outside isolated Keycloak')
        return link

    def setup(self):
        status, _ = self.api('POST', '/admin/realms', {'realm': self.realm, 'enabled': True, 'registrationAllowed': True,
            'verifyEmail': True, 'resetPasswordAllowed': True, 'loginTheme': 'computor', 'duplicateEmailsAllowed': False,
            'smtpServer': {'host': self.gateway, 'port': str(self.smtp.server_address[1]), 'from': 'test@example.invalid',
                           'ssl': 'false', 'starttls': 'false', 'auth': 'false'}})
        require(status == 201, 'Failed to create isolated realm')
        self.api('POST', self.root + '/clients', {'clientId': 'integration', 'enabled': True, 'publicClient': True,
                 'standardFlowEnabled': True, 'redirectUris': [CALLBACK]})
        for alias in ('VERIFY_EMAIL', 'UPDATE_PASSWORD', 'TERMS_AND_CONDITIONS'):
            self.api('PUT', self.root + '/authentication/required-actions/' + alias, {'alias': alias, 'name': alias,
                'providerId': alias, 'enabled': True, 'defaultAction': True,
                'priority': {'TERMS_AND_CONDITIONS': 10, 'VERIFY_EMAIL': 20, 'UPDATE_PASSWORD': 30}[alias]})
        # Email-first registration removes the initial password authenticator.
        executions = self.api('GET', self.root + '/authentication/flows/registration/executions')[1]
        for execution in executions:
            if execution.get('providerId') == 'registration-password-action':
                self.api('PUT', self.root + '/authentication/flows/registration/executions', {**execution, 'requirement': 'DISABLED'})
        from setup_abuse import configure
        self.secret = secrets.token_hex(32)
        configure(self.base, self.realm, self.token, self.secret, apply=True, cost=1000)
        self.ok('isolated PostgreSQL realm configured with provider and email-first registration')

    def registration_checks(self):
        browser = self.browser()
        require('password' not in Forms(browser.page[1]).form('kc-register-form')['fields'], 'Initial signup unexpectedly asks password')
        require(Forms(browser.page[1]).challenge is not None, 'No live registration challenge')
        for label, payload, extra in [('missing proof', '', {}), ('forged proof', 'forged', {}),
                                      ('honeypot', None, {'website': 'https://spam.invalid'}),
                                      ('nonsolving but correctly derived proof', 'nonsolving', {})]:
            browser = self.browser()
            if payload == 'nonsolving':
                payload = proof(Forms(browser.page[1]).challenge, solve=False)
            name = 'rejected-' + uuid.uuid4().hex[:8]
            self.signup(name, name + '@example.invalid', browser, payload, **extra)
            require(not self.users(name), label + ' created account')
            Forms(browser.page[1]).form('kc-register-form')
            self.no_mail()
            self.ok('registration rejects ' + label + ' before account/mail')
        donor, target = self.browser(), self.browser()
        stolen = proof(Forms(donor.page[1]).challenge)
        name = 'cross-session'
        self.signup(name, name + '@example.invalid', target, stolen)
        require(not self.users(name), 'Cross-session proof accepted')
        self.no_mail()
        self.ok('registration rejects cross-session proof')
        browser = self.browser()
        saved_page = browser.page
        payload = proof(Forms(saved_page[1]).challenge)
        self.signup('full-signup', 'Full.Signup+Original@gmail.com', browser, payload)
        require(len(self.users('full-signup')) == 1, 'Valid proof failed to create user')
        self.no_mail()
        browser.submit('kc-terms-form', accept='Accept')
        browser.visit(self.mail_link())
        password = 'Live-Abuse-' + secrets.token_urlsafe(18) + '-9!'
        browser.submit('kc-passwd-update-form', **{'password-new': password, 'password-confirm': password})
        require(browser.page[2], 'Full signup did not reach OAuth code')
        user = self.users('full-signup')[0]
        require(user['emailVerified'] and user['email'].lower() == 'full.signup+original@gmail.com', 'Original address not preserved/verified')
        attrs = user.get('attributes', {})
        require(attrs.get('computor.selfRegistered') == ['true'], 'Registration provenance missing')
        require(attrs.get('computor.selfRegisteredAt') == [str(user['createdTimestamp'])], 'Registration timestamp provenance missing')
        require(int(attrs.get('computor.lastLogin', ['0'])[0]) >= user['createdTimestamp'], 'Successful login activity marker missing')
        browser.page = saved_page
        self.signup('replayed', 'replayed@example.invalid', browser, payload)
        require(not self.users('replayed'), 'Replayed registration proof accepted')
        self.no_mail()
        self.ok('valid proof, terms, captured verification email, password setup, original address, replay rejection')
        browser = self.browser('auth')
        require(Forms(browser.page[1]).challenge is None, 'Normal login contains proof challenge')
        browser.submit('kc-form-login', username='full-signup', password=password)
        require(browser.page[2], 'Normal login failed')
        self.ok('normal password login unchanged')
        self.signup('gmail-duplicate', 'f.u.l.l.s.i.g.n.u.p+Other@gmail.com')
        require(not self.users('gmail-duplicate'), 'Gmail dotted/tag alias duplicate created')
        self.no_mail()
        self.ok('public registration rejects Gmail dot and plus aliases')
        return password

    def gmail_checks(self):
        require(self.create('custom-a', 'first.last+tag@example.invalid')[0] == 201, 'Custom address rejected')
        require(self.create('custom-b', 'firstlast@example.invalid')[0] == 201, 'Custom domain was Gmail-normalized')
        require(self.create('admin-duplicate', 'fullsignup+admin@gmail.com')[0] in (400, 409), 'Admin Gmail duplicate accepted')
        other = self.users('custom-a')[0]
        status, _ = self.api('PUT', self.root + '/users/' + other['id'], {**other, 'email': 'full.signup+update@gmail.com'})
        require(status in (400, 409), 'Admin email update accepted Gmail duplicate')
        self.ok('admin create/update enforce Gmail uniqueness and leave custom domains distinct')
        password = 'Account-Update-' + secrets.token_urlsafe(18) + '-9!'
        require(self.api('PUT', self.root + '/users/' + other['id'] + '/reset-password',
                        {'type': 'password', 'value': password, 'temporary': False})[0] == 204, 'Set account-update fixture password')
        require(self.api('PUT', self.root + '/users/' + other['id'],
                        {**other, 'requiredActions': ['UPDATE_PROFILE']})[0] == 204, 'Set profile-update required action')
        browser = self.browser('auth')
        browser.submit('kc-form-login', username=other['username'], password=password)
        browser.submit('kc-update-profile-form', email='full.signup+account@gmail.com')
        Forms(browser.page[1]).form('kc-update-profile-form')
        require(self.users(other['username'])[0]['email'] == other['email'], 'Self-service profile email accepted Gmail duplicate')
        self.ok('self-service profile email changes reject existing Gmail alias')
        barrier = threading.Barrier(2)
        def race_create(args):
            barrier.wait()
            return self.create(*args)[0]
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            statuses = list(pool.map(race_create, [('race-a', 'R.ace+one@gmail.com'), ('race-b', 'Race+two@gmail.com')]))
        require(sorted(statuses)[0] == 201 and sum(s == 201 for s in statuses) == 1, f'Concurrent canonical creates not unique: {statuses}')
        require(self.create('update-a', 'update-a@example.invalid')[0] == 201 and self.create('update-b', 'update-b@example.invalid')[0] == 201, 'Race fixture failure')
        users = [self.users(name)[0] for name in ('update-a', 'update-b')]
        barrier = threading.Barrier(2)
        def race_update(args):
            user, address = args
            barrier.wait()
            return self.api('PUT', self.root + '/users/' + user['id'], {**user, 'email': address})[0]
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            statuses = list(pool.map(race_update, zip(users, ('RaceUpdate+a@gmail.com', 'R.aceUpdate+b@gmail.com'))))
        require(sum(s == 204 for s in statuses) == 1, f'Concurrent canonical email updates not unique: {statuses}')
        self.ok('concurrent Gmail creates and email changes serialize to one accepted account')
        prepared = []
        for name, address in [('public-race-a', 'PublicRace+one@gmail.com'), ('public-race-b', 'P.ublicRace+two@gmail.com')]:
            browser = self.browser()
            prepared.append((name, address, browser, proof(Forms(browser.page[1]).challenge)))
        barrier = threading.Barrier(2)
        def race_signup(args):
            barrier.wait()
            return self.signup(*args)
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            list(pool.map(race_signup, prepared))
        require(sum(len(self.users(name)) for name in ('public-race-a', 'public-race-b')) == 1,
                'Concurrent public signups created canonical Gmail duplicates')
        self.no_mail()
        self.ok('concurrent public signups accept only one canonical Gmail account before email')

    def reset_checks(self):
        for username in ('full-signup', 'unknown-user'):
            browser = self.reset()
            browser.submit('kc-reset-password-form', username=username, altcha='')
            Forms(browser.page[1]).form('kc-reset-password-form')
            self.no_mail()
        self.ok('known and unknown password reset require proof before mail')
        for label, changes in [('forged', {'altcha': 'forged'}), ('honeypot', {'website': 'filled'})]:
            browser = self.reset()
            fields = {'username': 'full-signup', 'altcha': proof(Forms(browser.page[1]).challenge), **changes}
            browser.submit('kc-reset-password-form', **fields)
            Forms(browser.page[1]).form('kc-reset-password-form')
            self.no_mail()
            self.ok('password reset rejects ' + label + ' before mail')
        browser = self.reset()
        browser.submit('kc-reset-password-form', username='unknown-user', altcha=proof(Forms(browser.page[1]).challenge))
        unknown_feedback = re.findall(r'<span[^>]*class="[^"]*kc-feedback-text[^"]*"[^>]*>(.*?)</span>', browser.page[1], re.S)
        require(bool(unknown_feedback), 'Unknown reset lacks generic feedback')
        self.no_mail()
        browser = self.reset()
        reset_page = browser.page
        payload = proof(Forms(reset_page[1]).challenge)
        browser.submit('kc-reset-password-form', username='f.u.l.l.s.i.g.n.u.p+recovery@gmail.com', altcha=payload)
        known_feedback = re.findall(r'<span[^>]*class="[^"]*kc-feedback-text[^"]*"[^>]*>(.*?)</span>', browser.page[1], re.S)
        require(known_feedback == unknown_feedback, 'Known and unknown reset outcomes disclose account existence')
        self.mail_link()
        self.ok('valid reset mails verified Gmail alias and unknown account gets same generic outcome')
        browser.page = reset_page
        browser.submit('kc-reset-password-form', username='full-signup', altcha=payload)
        self.no_mail()
        self.ok('replayed password reset cannot send a second email')

    def browser_checks(self):
        """Optional real widget smoke; imports Playwright only when requested."""
        from playwright.sync_api import sync_playwright
        address = urllib.parse.urlparse(self.base).hostname
        browser_base = 'http://computor-abuse.localhost:8080'
        with sync_playwright() as playwright:
            options = {'headless': True, 'args': ['--no-sandbox', '--host-resolver-rules=MAP computor-abuse.localhost ' + address]}
            if os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE'):
                options['executable_path'] = os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE']
            browser = playwright.chromium.launch(**options)
            try:
                for kind in ('registration', 'reset'):
                    context = browser.new_context()
                    page = context.new_page()
                    requests, errors = [], []
                    page.on('request', lambda request: requests.append(request.url))
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.goto(self.authorization_url('registrations' if kind == 'registration' else 'auth').replace(self.base, browser_base, 1), wait_until='networkidle')
                    if kind == 'reset':
                        page.locator('a[href*="/reset-credentials?"]').click()
                        page.wait_for_load_state('networkidle')
                    field = page.locator('input[name=altcha]')
                    field.wait_for(state='attached', timeout=90000)
                    page.wait_for_function('(field) => !!field.value', arg=field.element_handle(), timeout=90000)
                    value = field.input_value()
                    decoded = json.loads(base64.b64decode(value))
                    require('solution' in decoded and 'challenge' in decoded, 'Widget did not produce ALTCHA v2 proof')
                    require(not errors, 'Browser JavaScript errors: ' + str(errors))
                    foreign = [url for url in requests if not url.startswith(browser_base + '/') and not url.startswith(('blob:', 'data:'))]
                    require(not foreign, 'Widget requested external origins: ' + str(foreign))
                    require(any('altcha-3.0.11.min.js' in url for url in requests), 'Vendored widget script not loaded')
                    self.ok('actual browser ' + kind + ' widget solves proof using only same-origin assets')
                    context.close()
            finally:
                browser.close()

    def expiry_check(self):
        # Configure both execution configs to minimum real TTL; no signed payload tampering.
        from setup_abuse import configure
        configure(self.base, self.realm, self.token, self.secret, apply=True, cost=1000, ttl=30)
        browser = self.browser()
        challenge = Forms(browser.page[1]).challenge
        payload = proof(challenge)
        reset_browser = self.reset()
        reset_payload = proof(Forms(reset_browser.page[1]).challenge)
        delay = max(0, Forms(reset_browser.page[1]).challenge['parameters']['expiresAt'] - time.time() + 2)
        require(delay < 34, f'Challenge TTL configuration did not apply: {delay}')
        print('Waiting for actual challenge expiry (30 seconds)', flush=True)
        time.sleep(delay)
        self.signup('expired', 'expired@example.invalid', browser, payload)
        require(not self.users('expired'), 'Expired proof created account')
        self.no_mail()
        reset_browser.submit('kc-reset-password-form', username='full-signup', altcha=reset_payload)
        Forms(reset_browser.page[1]).form('kc-reset-password-form')
        self.no_mail()
        self.ok('actually expired signed registration and reset challenges rejected before account/mail')

    def run(self, browser=False):
        try:
            self.setup()
            self.registration_checks()
            self.gmail_checks()
            self.reset_checks()
            if browser:
                self.browser_checks()
            self.expiry_check()
            print(json.dumps({'liveKeycloakAbuse': 'passed', 'checks': self.checked, 'externalMailSent': 0}), flush=True)
        finally:
            self.api('DELETE', self.root)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', help='Built provider JAR (default: abuse-provider/target/*.jar)')
    parser.add_argument('--browser', action='store_true', help='Also verify real widget JavaScript with optional Python Playwright/Chromium')
    args = parser.parse_args()
    with isolated_keycloak(args.provider) as (base, smtp, gateway):
        Checks(base, smtp, gateway).run(browser=args.browser)
