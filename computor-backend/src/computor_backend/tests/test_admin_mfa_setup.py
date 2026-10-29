"""ops/keycloak/setup_mfa.py survives interruption at every admin API call (issues#485).

An in-memory Keycloak admin API (flows, executions, configs, bindings) stands in
for the server. Each test interrupts configure() or rollback() at one call,
either before the request reaches the server or after it was applied with the
response lost, and then checks:

* the bound flows always behave either exactly as before or exactly as fully
  configured, judged by an independent evaluator of Keycloak's conditional
  flows (who is asked for which code), never in between;
* a plain re-run of configure() reaches the same realm as an uninterrupted run;
* rollback() after any interruption restores the original realm, with no
  copies, subflows or conditions left behind;
* bound flows are never edited.

The live counterpart is ops/keycloak/test_mfa_live.py.
"""

import copy
import importlib.util
import itertools
import json
import sys
import urllib.parse
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "ops/keycloak"))
_spec = importlib.util.spec_from_file_location("setup_mfa_under_test", REPO / "ops/keycloak/setup_mfa.py")
setup_mfa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(setup_mfa)

ROLE = "computor-mfa-required"
ROOT = "/admin/realms/test"


class Interrupted(ConnectionError):
    pass


class FakeKeycloak:
    """The admin endpoints setup_mfa.py uses, with Keycloak's uniqueness rules."""

    def __init__(self, legacy=False):
        self.ids = itertools.count(1)
        self.flows, self.execs, self.configs = {}, {}, {}
        self.realm = {"browserFlow": "browser", "resetCredentialsFlow": "reset credentials",
                      "ssoSessionMaxLifespan": 36000, "ssoSessionMaxLifespanRememberMe": 0}
        self.roles, self.group_roles = {}, []
        self.totp_action = {"alias": "CONFIGURE_TOTP", "enabled": False}
        self.mappers = []
        self.calls, self.writes, self.fail_at, self.fail_after = 0, 0, None, False
        self.bound_edits = []
        self._builtin_flows()
        if legacy:
            self._legacy_flows()

    # -- fixture ---------------------------------------------------------------
    def _id(self):
        return f"{next(self.ids):08d}-0000"

    def _flow(self, alias, top=True, builtin=False, description=None):
        fid = self._id()
        self.flows[fid] = {"id": fid, "alias": alias, "description": description, "providerId": "basic-flow",
                           "topLevel": top, "builtIn": builtin, "executions": []}
        return fid

    def _exec(self, parent, requirement, provider=None, subflow=None, config=None):
        eid = self._id()
        cid = None
        if config is not None:
            cid = self._id()
            self.configs[cid] = {"id": cid, "alias": f"cfg-{cid}", "config": dict(config)}
        self.execs[eid] = {"id": eid, "requirement": requirement, "provider": provider, "flowId": subflow,
                           "config": cid, "parent": parent}
        self.flows[parent]["executions"].append(eid)
        return eid

    def _builtin_flows(self):
        browser = self._flow("browser", builtin=True)
        self._exec(browser, "ALTERNATIVE", "auth-cookie")
        forms = self._flow("forms", top=False, builtin=True)
        self._exec(browser, "ALTERNATIVE", subflow=forms)
        self._exec(forms, "REQUIRED", "auth-username-password-form")
        two_factor = self._flow("Browser - Conditional 2FA", top=False, builtin=True)
        self._exec(forms, "CONDITIONAL", subflow=two_factor)
        self._exec(two_factor, "REQUIRED", "conditional-user-configured")
        self._exec(two_factor, "ALTERNATIVE", "auth-otp-form")
        reset = self._flow("reset credentials", builtin=True)
        for provider in ("reset-credentials-choose-user", "reset-credential-email", "reset-password"):
            self._exec(reset, "REQUIRED", provider)
        otp = self._flow("Reset - Conditional OTP", top=False, builtin=True)
        self._exec(reset, "CONDITIONAL", subflow=otp)
        self._exec(otp, "REQUIRED", "conditional-user-configured")
        self._exec(otp, "REQUIRED", "reset-otp")

    def _legacy_flows(self):
        """computor.at's shape: custom browser and reset flows are bound."""
        browser = self._flow("legacy browser")
        self._exec(browser, "ALTERNATIVE", "auth-cookie")
        forms = self._flow("legacy forms", top=False)
        self._exec(browser, "ALTERNATIVE", subflow=forms)
        self._exec(forms, "REQUIRED", "auth-username-password-form")
        otp = self._flow("legacy conditional otp", top=False)
        self._exec(forms, "CONDITIONAL", subflow=otp)
        self._exec(otp, "REQUIRED", "conditional-user-configured")
        self._exec(otp, "REQUIRED", "auth-otp-form")
        self._copy(self._by_alias("reset credentials"), "legacy reset")
        self.realm = {"browserFlow": "legacy browser", "resetCredentialsFlow": "legacy reset"}

    # -- model helpers ---------------------------------------------------------
    def _by_alias(self, alias):
        return next((f for f in self.flows.values() if f["alias"] == alias), None)

    def _top(self, fid):
        """Top-level flow containing flow ``fid``."""
        while not self.flows[fid]["topLevel"]:
            fid = next(e["parent"] for e in self.execs.values() if e["flowId"] == fid)
        return self.flows[fid]

    def _touch(self, fid):
        top = self._top(fid)
        if top["alias"] in (self.realm["browserFlow"], self.realm["resetCredentialsFlow"]):
            self.bound_edits.append(top["alias"])

    def _copy(self, source, new_name, top=True):
        fid = self._flow(new_name, top=top, description=source["description"])
        for eid in source["executions"]:
            e = self.execs[eid]
            sub = None
            if e["flowId"]:
                sub = self._copy(self.flows[e["flowId"]], f"{new_name} {self.flows[e['flowId']]['alias']}", top=False)
            config = self.configs[e["config"]]["config"] if e["config"] else None
            self._exec(fid, e["requirement"], e["provider"], sub, config)
        return fid

    def _delete_exec(self, eid):
        e = self.execs.pop(eid)
        self.flows[e["parent"]]["executions"].remove(eid)
        if e["config"]:
            self.configs.pop(e["config"], None)
        if e["flowId"]:
            self._delete_flow(e["flowId"])

    def _delete_flow(self, fid):
        for eid in list(self.flows[fid]["executions"]):
            self._delete_exec(eid)
        del self.flows[fid]

    def _listing(self, fid, level=0):
        out = []
        for index, eid in enumerate(self.flows[fid]["executions"]):
            e = self.execs[eid]
            rep = {"id": eid, "requirement": e["requirement"], "level": level, "index": index, "priority": index}
            if e["flowId"]:
                rep.update(authenticationFlow=True, displayName=self.flows[e["flowId"]]["alias"], flowId=e["flowId"])
            else:
                rep.update(providerId=e["provider"], displayName=e["provider"])
            if e["config"]:
                rep["authenticationConfig"] = e["config"]
            out.append(rep)
            if e["flowId"]:
                out.extend(self._listing(e["flowId"], level + 1))
        return out

    # -- HTTP ------------------------------------------------------------------
    def request(self, method, url, token=None, json_body=None):
        self.calls += 1
        failing = self.fail_at == self.calls
        if failing and not self.fail_after:
            raise Interrupted(f"injected failure before call {self.calls}: {method} {url}")
        self.writes += method != "GET"
        result = self._handle(method, url, copy.deepcopy(json_body))
        if failing:
            raise Interrupted(f"injected failure after call {self.calls}: {method} {url}")
        return result

    def _handle(self, method, url, body):
        parsed = urllib.parse.urlsplit(url)
        assert parsed.path.startswith(ROOT), url
        parts = [urllib.parse.unquote(p) for p in parsed.path[len(ROOT):].split("/") if p]
        query = dict(urllib.parse.parse_qsl(parsed.query))
        key = (method, tuple(p if i % 2 == 0 else "*" for i, p in enumerate(parts)))
        if parts == []:
            if method == "GET":
                return 200, dict(self.realm, realm="test")
            for k in ("browserFlow", "resetCredentialsFlow"):
                if k in body:
                    if self._by_alias(body[k]) is None:
                        return 400, {"error": "unknown flow"}
                    self.realm[k] = body[k]
            return 204, None
        head = parts[0]
        if head == "roles":
            if method == "POST":
                self.roles[body["name"]] = dict(body, id="role-" + body["name"])
                return 201, None
            name = parts[1]
            if name not in self.roles:
                return 404, {"error": "not found"}
            if len(parts) == 3:
                return 200, []
            return 200, self.roles[name]
        if head == "groups":
            if len(parts) == 1:
                return 200, [{"id": "g1", "name": "administrators"}]
            if method == "GET":
                return 200, list(self.group_roles)
            self.group_roles.extend(body)
            return 204, None
        if head == "clients":
            if len(parts) == 1:
                return 200, [{"id": "c1", "clientId": query.get("clientId")}]
            if method == "GET":
                return 200, copy.deepcopy(self.mappers)
            if method == "POST":
                self.mappers.append(dict(body, id=self._id()))
                return 201, None
            mapper = next(m for m in self.mappers if m["id"] == parts[4])
            mapper.update(body)
            return 204, None
        assert head == "authentication", url
        sub = parts[1]
        if sub == "required-actions":
            if method == "GET":
                return 200, dict(self.totp_action)
            self.totp_action.update(body)
            return 204, None
        if sub == "config":
            config = self.configs.get(parts[2])
            if config is None:
                return 404, {"error": "config not found"}
            if method == "GET":  # Keycloak 26.7 masks the amr reference values
                shown = copy.deepcopy(config)
                shown["config"] = {k: "**********" if k.startswith("default.reference.") else v
                                   for k, v in shown["config"].items()}
                return 200, shown
            owner = next(e for e in self.execs.values() if e["config"] == parts[2])
            self._touch(owner["parent"])
            config["alias"] = body["alias"]  # Keycloak takes the alias of a PUT as well
            config["config"] = dict(body["config"])
            return 204, None
        if sub == "executions":
            eid = parts[2]
            if eid not in self.execs:
                return 404, {"error": "execution not found"}
            self._touch(self.execs[eid]["parent"])
            if method == "DELETE":
                self._delete_exec(eid)
                return 204, None
            assert parts[3] == "config" and method == "POST"
            if any(c["alias"] == body["alias"] for c in self.configs.values()):
                return 409, {"errorMessage": "Authenticator config alias already exists"}
            cid = self._id()
            self.configs[cid] = {"id": cid, "alias": body["alias"], "config": dict(body["config"])}
            self.execs[eid]["config"] = cid
            return 201, None
        assert sub == "flows", url
        if len(parts) == 2:
            if method == "GET":
                return 200, [{k: v for k, v in f.items() if k != "executions"}
                             for f in self.flows.values() if f["topLevel"]]
            if self._by_alias(body["alias"]):
                return 409, {"errorMessage": "Flow already exists"}
            self._flow(body["alias"], description=body.get("description"))
            return 201, None
        target = parts[2]
        if len(parts) == 3:
            flow = self.flows.get(target)
            if flow is None:
                return 404, {"error": "flow not found"}
            if flow["builtIn"]:
                return 400, {"errorMessage": "Cannot update/delete built-in flow"}
            if method == "DELETE":
                if flow["alias"] in self.realm.values():
                    return 400, {"errorMessage": "Cannot delete flow, it is bound"}
                self._delete_flow(target)
                return 204, None
            flow["description"] = body.get("description")
            return 204, None
        flow = self._by_alias(target)
        if flow is None:
            return 404, {"error": "flow not found"}
        action = parts[3]
        if action == "copy":
            if self._by_alias(body["newName"]):
                return 409, {"errorMessage": "Flow already exists"}
            self._copy(flow, body["newName"])
            return 201, None
        if len(parts) == 4 and method == "GET":
            return 200, self._listing(flow["id"])
        self._touch(flow["id"])
        if len(parts) == 4:  # PUT requirement of any execution in this flow tree
            self.execs[body["id"]]["requirement"] = body["requirement"]
            return 204, None
        if parts[4] == "execution":
            self._exec(flow["id"], "DISABLED", body["provider"])
            return 201, None
        assert parts[4] == "flow"
        if self._by_alias(body["alias"]):
            return 409, {"errorMessage": "New flow alias name already exists"}
        sub_id = self._flow(body["alias"], top=False, description=body.get("description"))
        self._exec(flow["id"], "DISABLED", subflow=sub_id)
        return 201, None

    # -- oracle ------------------------------------------------------------------
    def prompts(self, binding, roles, has_otp):
        """Codes Keycloak would ask for in the bound ``binding`` flow.

        Independent of setup_mfa.py: walks the flow tree with Keycloak's rules
        for CONDITIONAL subflows (all their conditions must hold) and returns
        the code steps reached, with the amr reference they would record.
        """
        return self._walk(self._by_alias(self.realm[binding])["id"], roles, has_otp)

    def _condition(self, e, roles, has_otp):
        if e["provider"] == "conditional-user-configured":
            return has_otp
        if e["provider"] == "conditional-user-role":
            if not e["config"]:
                return False
            config = self.configs[e["config"]]["config"]
            held = config.get("condUserRole") in roles
            return held != (config.get("negate") == "true")
        raise AssertionError(e)

    def _walk(self, fid, roles, has_otp):
        found = []
        for eid in self.flows[fid]["executions"]:
            e = self.execs[eid]
            if e["requirement"] == "DISABLED":
                continue
            if e["flowId"]:
                if e["requirement"] == "CONDITIONAL":
                    conditions = [self.execs[c] for c in self.flows[e["flowId"]]["executions"]
                                  if (self.execs[c]["provider"] or "").startswith("conditional-")
                                  and self.execs[c]["requirement"] != "DISABLED"]
                    if not conditions or not all(self._condition(c, roles, has_otp) for c in conditions):
                        continue
                found.extend(self._walk(e["flowId"], roles, has_otp))
            elif e["provider"] in ("auth-otp-form", "reset-otp"):
                reference = self.configs[e["config"]]["config"].get("default.reference.value") if e["config"] else None
                found.append((e["provider"], reference))
        return found

    def behaviour(self):
        people = {"holder+otp": ({ROLE}, True), "holder": ({ROLE}, False),
                  "user+otp": (set(), True), "user": (set(), False)}
        return {(binding, who): tuple(self.prompts(binding, *people[who]))
                for binding in ("browserFlow", "resetCredentialsFlow") for who in people}

    def shape(self):
        """Every top-level flow as a nested (step, requirement, config) tree."""
        def tree(fid):
            out = []
            for eid in self.flows[fid]["executions"]:
                e = self.execs[eid]
                config = tuple(sorted(self.configs[e["config"]]["config"].items())) if e["config"] else None
                step = (self.flows[e["flowId"]]["alias"], tuple(tree(e["flowId"]))) if e["flowId"] else e["provider"]
                out.append((step, e["requirement"], config))
            return out
        return {f["alias"]: tree(f["id"]) for f in self.flows.values() if f["topLevel"]}


ORIGINAL = {
    ("browserFlow", "holder+otp"): (("auth-otp-form", None),),
    ("browserFlow", "holder"): (),
    ("browserFlow", "user+otp"): (("auth-otp-form", None),),
    ("browserFlow", "user"): (),
    ("resetCredentialsFlow", "holder+otp"): (("reset-otp", None),),
    ("resetCredentialsFlow", "holder"): (),
    ("resetCredentialsFlow", "user+otp"): (("reset-otp", None),),
    ("resetCredentialsFlow", "user"): (),
}
CONFIGURED = {**ORIGINAL, **{
    # Role holders: exactly one code, recorded as amr "otp"; enrolment is forced.
    ("browserFlow", "holder+otp"): (("auth-otp-form", "otp"),),
    ("browserFlow", "holder"): (("auth-otp-form", "otp"),),
    # A role holder must give the code to reset and keeps the authenticator.
    ("resetCredentialsFlow", "holder+otp"): (("auth-otp-form", "otp"),),
    ("resetCredentialsFlow", "holder"): (("auth-otp-form", "otp"),),
}}


def _install(monkeypatch, fake):
    monkeypatch.setattr(setup_mfa, "_request", fake.request)


def _configure():
    return setup_mfa.configure("http://kc", "test", "token")


def _rollback():
    return setup_mfa.rollback("http://kc", "test", "token")


def _reference(monkeypatch, legacy):
    fake = FakeKeycloak(legacy)
    original_shape = fake.shape()
    _install(monkeypatch, fake)
    _configure()
    return fake, original_shape


@pytest.fixture(params=[False, True], ids=["builtin-flows", "legacy-custom-flows"])
def legacy(request):
    return request.param


def test_configure_enforces_and_is_idempotent(monkeypatch, legacy):
    fake, original_shape = _reference(monkeypatch, legacy)
    assert fake.behaviour() == CONFIGURED
    assert fake.bound_edits == []
    configured = fake.shape()
    assert {k: v for k, v in configured.items() if k in original_shape} == original_shape, \
        "configure() changed a flow it does not own"
    writes = fake.writes
    _configure()
    assert fake.shape() == configured
    assert fake.writes == writes, "a re-run of a configured realm must only read"


def _otp_configs(fake):
    """(alias, maxAge) of every config that records the amr reference ``otp``."""
    return sorted((c["alias"], c["config"].get("default.reference.maxAge")) for c in fake.configs.values()
                  if c["config"].get("default.reference.value") == "otp")


@pytest.mark.parametrize("lifespans, max_age", [
    ({}, "36000"),
    ({"ssoSessionMaxLifespan": 36000, "ssoSessionMaxLifespanRememberMe": 0}, "36000"),
    ({"ssoSessionMaxLifespan": 36000, "ssoSessionMaxLifespanRememberMe": 2592000}, "2592000"),
], ids=["keycloak-default", "no-remember-me-lifespan", "remember-me-longer"])
def test_otp_evidence_lasts_the_longest_sso_session(monkeypatch, lifespans, max_age):
    """With maxAge 0, amr "otp" lasted the second the code was entered (AUTHZ_007, 2026-10-29)."""
    fake = FakeKeycloak()
    for key in ("ssoSessionMaxLifespan", "ssoSessionMaxLifespanRememberMe"):
        fake.realm.pop(key)
    fake.realm.update(lifespans)
    _install(monkeypatch, fake)
    assert _configure()["amrMaxAge"] == int(max_age)
    configs = _otp_configs(fake)
    assert len(configs) == 2, configs
    assert all(age == max_age and alias.endswith("-amr" + max_age) for alias, age in configs), configs


def test_realm_configured_with_max_age_zero_is_repaired_once(monkeypatch, legacy):
    """A realm set up before the fix gets the maxAge in place: one PUT per OTP step, then reads only."""
    fake, _ = _reference(monkeypatch, legacy)
    configured = fake.shape()
    for config in fake.configs.values():
        if config["config"].get("default.reference.value") == "otp":
            config["config"]["default.reference.maxAge"] = "0"
            config["alias"] = config["alias"].rsplit("-amr", 1)[0]
    writes, fake.bound_edits = fake.writes, []
    _configure()
    assert fake.writes - writes == 2
    assert sorted(fake.bound_edits) == sorted([setup_mfa.BROWSER_FLOW, setup_mfa.RESET_FLOW])
    assert fake.shape() == configured and fake.behaviour() == CONFIGURED
    writes = fake.writes
    _configure()
    assert fake.writes == writes, "a re-run of a repaired realm must only read"


def _call_count(monkeypatch, legacy, action):
    fake = FakeKeycloak(legacy)
    _install(monkeypatch, fake)
    if action == "rollback":
        _configure()
        fake.calls = 0
        _rollback()
    else:
        _configure()
    return fake.calls


@pytest.mark.parametrize("after", [False, True], ids=["lost-request", "lost-response"])
def test_interrupted_configure_never_binds_a_partial_flow_and_resumes(monkeypatch, legacy, after):
    reference, _ = _reference(monkeypatch, legacy)
    expected = reference.shape()
    total = _call_count(monkeypatch, legacy, "configure")
    for k in range(1, total + 1):
        fake = FakeKeycloak(legacy)
        _install(monkeypatch, fake)
        fake.fail_at, fake.fail_after = k, after
        with pytest.raises(Interrupted):
            _configure()
        state = fake.behaviour()
        assert state in (ORIGINAL, CONFIGURED), f"call {k}: bound flows half-configured: {state}"
        assert fake.bound_edits == [], f"call {k}: edited bound flow(s) {fake.bound_edits}"
        fake.fail_at = None
        _configure()
        assert fake.behaviour() == CONFIGURED, f"call {k}: retry did not converge"
        assert fake.shape() == expected, f"call {k}: retry left a different realm"
        assert fake.bound_edits == []


@pytest.mark.parametrize("after", [False, True], ids=["lost-request", "lost-response"])
def test_rollback_after_interrupted_configure_restores_the_realm(monkeypatch, legacy, after):
    total = _call_count(monkeypatch, legacy, "configure")
    for k in range(1, total + 1):
        fake = FakeKeycloak(legacy)
        original_shape, original_binding = fake.shape(), dict(fake.realm)
        _install(monkeypatch, fake)
        fake.fail_at, fake.fail_after = k, after
        with pytest.raises(Interrupted):
            _configure()
        fake.fail_at = None
        _rollback()
        assert fake.realm == original_binding, f"call {k}: bindings not restored"
        assert fake.shape() == original_shape, f"call {k}: rollback left orphans"
        assert fake.behaviour() == ORIGINAL


@pytest.mark.parametrize("after", [False, True], ids=["lost-request", "lost-response"])
def test_interrupted_rollback_can_be_rerun(monkeypatch, legacy, after):
    total = _call_count(monkeypatch, legacy, "rollback")
    for k in range(1, total + 1):
        fake = FakeKeycloak(legacy)
        original_shape, original_binding = fake.shape(), dict(fake.realm)
        _install(monkeypatch, fake)
        _configure()
        fake.calls, fake.fail_at, fake.fail_after = 0, k, after
        with pytest.raises(Interrupted):
            _rollback()
        assert fake.behaviour() in (ORIGINAL, CONFIGURED), f"call {k}: half rolled back"
        fake.fail_at = None
        _rollback()
        assert fake.realm == original_binding and fake.shape() == original_shape, f"call {k}"


def test_rollback_then_configure_reproduces_the_first_apply(monkeypatch, legacy):
    fake, _ = _reference(monkeypatch, legacy)
    first = fake.shape()
    _rollback()
    _configure()
    assert fake.shape() == first and fake.behaviour() == CONFIGURED


def test_rollback_strips_in_place_edits_of_earlier_revisions(monkeypatch):
    """The previous revision edited a bound custom flow in place; rollback finds those orphans."""
    fake = FakeKeycloak(legacy=True)
    original_shape = fake.shape()
    _install(monkeypatch, fake)
    reset = fake._by_alias("legacy reset")
    two_factor = next(fake.execs[e]["flowId"] for e in reset["executions"] if fake.execs[e]["flowId"])
    fake._exec(two_factor, "REQUIRED", "conditional-user-role", config={"condUserRole": ROLE, "negate": "true"})
    sub = fake._flow(setup_mfa.RESET_SUBFLOW, top=False)
    fake._exec(reset["id"], "CONDITIONAL", subflow=sub)
    fake._exec(sub, "REQUIRED", "conditional-user-role", config={"condUserRole": ROLE, "negate": "false"})
    fake._exec(sub, "REQUIRED", "auth-otp-form", config=setup_mfa.amr_otp(0))
    result = _rollback()
    assert result["strippedExecutions"] == {"legacy reset": 2}
    assert fake.shape() == original_shape


def test_stale_unbound_copy_of_another_flow_is_replaced(monkeypatch):
    """A leftover copy of a flow that is no longer bound is not resumed."""
    fake = FakeKeycloak()
    _install(monkeypatch, fake)
    _configure()
    _rollback()
    fake._copy(fake._by_alias("browser"), setup_mfa.BROWSER_FLOW)  # unmarked leftover
    fake._copy(fake._by_alias("browser"), "operator browser")
    fake.realm["browserFlow"] = "operator browser"
    _configure()
    flow = fake._by_alias(setup_mfa.BROWSER_FLOW)
    assert setup_mfa._origin({k: v for k, v in flow.items() if k != "executions"}) == "operator browser"
    assert fake.behaviour() == CONFIGURED
    _rollback()
    assert fake.realm["browserFlow"] == "operator browser"
    assert setup_mfa.BROWSER_FLOW not in fake.shape()
