"""Behavioral tests for the server-side GitHub issue-report bridge."""

import base64
import json
import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from computor_backend.issue_reports import config as issue_config
from computor_backend.issue_reports import health as issue_health
from computor_backend.issue_reports import service as issue_reports
from computor_backend.permissions.principal import Principal
from computor_types.issue_reports import IssueReportCreate


@contextmanager
def configured(**overrides):
    """Run the block with the issue-report environment set to known values."""
    env = {
        "GITHUB_ISSUE_REPORT_REPOSITORY": "computor-org/issues",
        "GITHUB_ISSUE_REPORT_TOKEN": "server-token",
        "GITHUB_ISSUE_REPORT_LABELS": "Testing",
        "GITHUB_ISSUE_REPORT_BRANCH": "main",
    }
    env.update(overrides)
    with patch.dict(os.environ, env, clear=False):
        issue_config.get_issue_report_settings.cache_clear()
        issue_health.reset_health()
        try:
            yield
        finally:
            issue_config.get_issue_report_settings.cache_clear()
            issue_health.reset_health()


class _Session:
    """Session stand-in that records the issue_report row the service writes.

    Only the four calls the service makes; ``refresh`` stands in for the
    ``uuid_generate_v4()`` server default, which needs a real database.
    """

    def __init__(self):
        self.added: list = []

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        return None

    def refresh(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()

    def get(self, model, key):
        return None

    @property
    def report(self):
        assert len(self.added) == 1, f"expected one issue_report row, got {len(self.added)}"
        return self.added[0]


class _Response:
    def __init__(self, payload: dict, status_code: int = 201):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class _Screenshot:
    content_type = "image/png"

    async def read(self, size: int = -1) -> bytes:
        return b"png bytes"[:size]


class _GitHubClient:
    def __init__(self, calls: list[dict]):
        self.calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def put(self, url, headers=None, json=None):
        self.calls.append({"method": "PUT", "url": url, "headers": headers, "json": json})
        return _Response(
            {"content": {"html_url": "https://github.com/computor-org/issues/blob/main/issue-reports/1/screenshot.png"}},
            201,
        )

    async def post(self, url, headers=None, json=None):
        self.calls.append({"method": "POST", "url": url, "headers": headers, "json": json})
        return _Response(
            {"number": 123, "html_url": "https://github.com/computor-org/issues/issues/123"},
            201,
        )


@pytest.mark.asyncio
async def test_submit_issue_report_creates_issue_and_redacts_context():
    calls: list[dict] = []
    payload = IssueReportCreate(
        title="Button is broken",
        description="The report button does nothing.",
        expected="A report should be submitted.",
        context={"access_token": "must-not-escape", "route": "/courses"},
    )

    with configured(GITHUB_ISSUE_REPORT_LABELS="Testing, Usability"), patch.object(
        issue_reports.httpx,
        "AsyncClient",
        lambda **kwargs: _GitHubClient(calls),
    ):
        session = _Session()
        result = await issue_reports.submit_issue_report(
            payload,
            Principal(user_id="user-1"),
            session,
            _Screenshot(),
        )

    assert result.issue_number == 123
    assert result.report_id
    # The tracker is private here, so the reporter gets no link into it.
    assert result.issue_url is None
    assert [call["method"] for call in calls] == ["PUT", "POST"]
    uploaded = calls[0]["json"]["content"]
    assert base64.b64decode(uploaded) == b"png bytes"
    issue_payload = calls[1]["json"]
    assert issue_payload["labels"] == ["Testing", "Usability"]
    assert "must-not-escape" not in issue_payload["body"]
    assert "[redacted]" in issue_payload["body"]
    assert calls[1]["headers"]["Authorization"] == "Bearer server-token"


@pytest.mark.asyncio
async def test_submit_issue_report_rejects_non_image_before_github_call():
    calls: list[dict] = []

    class _TextFile(_Screenshot):
        content_type = "text/plain"

    with configured(), patch.object(
        issue_reports.httpx,
        "AsyncClient",
        lambda **kwargs: _GitHubClient(calls),
    ), pytest.raises(issue_reports.IssueReportSubmissionError, match="Screenshot"):
        await issue_reports.submit_issue_report(
            IssueReportCreate(description="bad attachment"),
            Principal(user_id="user-1"),
            _Session(),
            _TextFile(),
        )

    assert calls == []


def test_issue_report_requires_explicit_server_configuration():
    with configured(GITHUB_ISSUE_REPORT_REPOSITORY="", GITHUB_ISSUE_REPORT_TOKEN=""), pytest.raises(
        issue_reports.IssueReportNotConfigured
    ):
        issue_reports._require_configuration()


def test_issue_report_requires_a_token_to_submit():
    """A repository alone is not enough — GitHub has no anonymous issue creation."""
    with configured(GITHUB_ISSUE_REPORT_TOKEN=""), pytest.raises(
        issue_reports.IssueReportNotConfigured, match="TOKEN"
    ):
        issue_reports._require_configuration()


# ---------------------------------------------------------------------------
# Repository parsing — any GitHub issues page is a legal target
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value,expected_full_name,expected_api_base",
    [
        ("computor-org/issues", "computor-org/issues", "https://api.github.com"),
        ("https://github.com/computor-org/issues", "computor-org/issues", "https://api.github.com"),
        (
            "https://github.com/computor-org/issues/issues",
            "computor-org/issues",
            "https://api.github.com",
        ),
        ("https://ghe.example.org/team/board", "team/board", "https://ghe.example.org/api/v3"),
    ],
)
def test_repository_accepts_any_github_issues_page(value, expected_full_name, expected_api_base):
    with configured(GITHUB_ISSUE_REPORT_REPOSITORY=value):
        settings = issue_config.get_issue_report_settings()
        assert settings.configured
        assert settings.reference.full_name == expected_full_name
        assert settings.api_base == expected_api_base


@pytest.mark.parametrize("value", ["", "   ", "not-a-repo", "owner/name/extra/bits", "https://"])
def test_malformed_repository_leaves_the_feature_off(value):
    with configured(GITHUB_ISSUE_REPORT_REPOSITORY=value):
        assert not issue_config.get_issue_report_settings().configured


def test_api_url_overrides_the_derived_base():
    with configured(GITHUB_ISSUE_REPORT_API_URL="https://ghe.example.org/api/v3/"):
        assert issue_config.get_issue_report_settings().api_base == "https://ghe.example.org/api/v3"


# ---------------------------------------------------------------------------
# Startup probe — public vs private is read from GitHub, not from config
# ---------------------------------------------------------------------------


class _ProbeClient:
    """Stub GitHub returning one canned repository response."""

    def __init__(self, status_code: int, payload: dict, seen: list[dict]):
        self._status_code = status_code
        self._payload = payload
        self._seen = seen

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, headers=None):
        self._seen.append({"url": url, "headers": headers})
        return _Response(self._payload, self._status_code)


@contextmanager
def github_says(status_code=200, payload=None, seen=None):
    client = _ProbeClient(status_code, payload or {}, seen if seen is not None else [])
    with patch.object(issue_health.httpx, "AsyncClient", lambda **kwargs: client):
        yield


@pytest.mark.asyncio
async def test_probe_reports_a_public_repository_as_usable_without_a_token():
    with configured(GITHUB_ISSUE_REPORT_TOKEN=""), github_says(
        payload={"private": False, "has_issues": True}
    ):
        health = await issue_health.probe_issue_reporting()

    assert health.available
    assert health.visibility == "public"


@pytest.mark.asyncio
async def test_probe_reports_a_private_repository_with_a_token_as_usable():
    seen: list[dict] = []
    with configured(), github_says(payload={"private": True, "has_issues": True}, seen=seen):
        health = await issue_health.probe_issue_reporting()

    assert health.available
    assert health.visibility == "private"
    assert seen[0]["headers"]["Authorization"] == "Bearer server-token"


@pytest.mark.asyncio
async def test_probe_disables_a_private_repository_with_no_token():
    """GitHub hides a private repo from an anonymous caller, so this is a 404."""
    with configured(GITHUB_ISSUE_REPORT_TOKEN=""), github_says(status_code=404):
        health = await issue_health.probe_issue_reporting()

    assert not health.available
    assert "GITHUB_ISSUE_REPORT_TOKEN" in health.reason


@pytest.mark.asyncio
async def test_probe_disables_a_repository_with_its_tracker_turned_off():
    with configured(), github_says(payload={"private": True, "has_issues": False}):
        health = await issue_health.probe_issue_reporting()

    assert not health.available
    assert "issue tracker disabled" in health.reason


@pytest.mark.asyncio
async def test_probe_disables_a_rejected_token():
    with configured(), github_says(status_code=401):
        health = await issue_health.probe_issue_reporting()

    assert not health.available
    assert "rejected" in health.reason


@pytest.mark.asyncio
async def test_probe_survives_an_unreachable_github():
    import httpx

    class _Boom:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, headers=None):
            raise httpx.ConnectError("no route to host")

    with configured(), patch.object(issue_health.httpx, "AsyncClient", lambda **kwargs: _Boom()):
        health = await issue_health.probe_issue_reporting()

    assert not health.available
    assert "unreachable" in health.reason


@pytest.mark.asyncio
async def test_a_repaired_configuration_recovers_without_a_restart():
    with configured():
        with github_says(status_code=401):
            assert not (await issue_health.ensure_probed()).available

        # Inside the TTL the verdict stands without touching GitHub again.
        seen: list[dict] = []
        with github_says(payload={"private": True, "has_issues": True}, seen=seen):
            assert not (await issue_health.ensure_probed()).available
            assert seen == []

        # Once it expires, the next request re-probes and finds the fixed token.
        issue_health._state = issue_health.replace(issue_health.current_health(), checked_at=0.0)
        with github_says(payload={"private": True, "has_issues": True}):
            assert (await issue_health.ensure_probed()).available


# ---------------------------------------------------------------------------
# Receipt privacy — a public tracker may be linked, a private one may not
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_public_tracker_may_be_linked_back_to_the_reporter():
    calls: list[dict] = []
    # httpx is one module shared by the probe and the service, so the two stubs
    # have to take turns rather than nest.
    with configured():
        with github_says(payload={"private": False, "has_issues": True}):
            assert (await issue_health.probe_issue_reporting()).is_public
        with patch.object(
            issue_reports.httpx, "AsyncClient", lambda **kwargs: _GitHubClient(calls)
        ):
            result = await issue_reports.submit_issue_report(
                IssueReportCreate(description="something broke"),
                Principal(user_id="user-1"),
                _Session(),
            )

    assert str(result.issue_url) == "https://github.com/computor-org/issues/issues/123"


@pytest.mark.asyncio
async def test_a_revoked_token_disables_the_feature_instead_of_failing_every_report():
    class _Rejecting(_GitHubClient):
        async def post(self, url, headers=None, json=None):
            self.calls.append({"method": "POST"})
            return _Response({"message": "Bad credentials"}, 401)

    with configured(), patch.object(
        issue_reports.httpx, "AsyncClient", lambda **kwargs: _Rejecting([])
    ), pytest.raises(issue_reports.IssueReportSubmissionError):
        issue_health._record(True, "", "private")
        await issue_reports.submit_issue_report(
            IssueReportCreate(description="something broke"),
            Principal(user_id="user-1"),
            _Session(),
        )

    assert not issue_health.current_health().available


# ---------------------------------------------------------------------------
# Endpoint gate — the route always exists, but only serves a working deployment
# ---------------------------------------------------------------------------


def _client(cache=None):
    """A bare app carrying just the issue-report route, with auth and IO stubbed."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from computor_backend.api import issue_reports as issue_api
    from computor_backend.database import get_db
    from computor_backend.exceptions.error_handlers import register_exception_handlers
    from computor_backend.permissions.auth import get_current_principal
    from computor_backend.redis_cache import get_redis_client

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(issue_api.router, prefix="/issue-reports")
    app.dependency_overrides[get_current_principal] = lambda: Principal(user_id="user-1")
    app.dependency_overrides[get_db] = lambda: _Session()
    app.dependency_overrides[get_redis_client] = lambda: cache or _Cache()
    return TestClient(app, raise_server_exceptions=False)


class _Cache:
    """Redis stand-in with just the counters the rate limiter touches."""

    def __init__(self):
        self.counts: dict[str, int] = {}

    async def incr(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key, seconds):
        return True

    async def ttl(self, key):
        return 42


def test_endpoint_is_404_when_the_deployment_has_no_tracker():
    """The route is in the schema for a stable contract, but answers as absent."""
    with configured(GITHUB_ISSUE_REPORT_REPOSITORY="", GITHUB_ISSUE_REPORT_TOKEN=""):
        response = _client().post("/issue-reports", data={"description": "broken"})
    assert response.status_code == 404


def test_endpoint_is_404_when_a_public_tracker_needs_no_backend():
    with configured(GITHUB_ISSUE_REPORT_TOKEN=""):
        response = _client().post("/issue-reports", data={"description": "broken"})
    assert response.status_code == 404


def test_endpoint_is_503_when_the_probe_is_failing():
    with configured(), github_says(status_code=401):
        response = _client().post("/issue-reports", data={"description": "broken"})
    assert response.status_code == 503
    assert response.json()["error_code"] == "EXT_007"


def test_second_report_inside_the_window_is_rate_limited():
    cache = _Cache()
    calls: list[dict] = []
    with configured(), patch.object(
        issue_reports.httpx, "AsyncClient", lambda **kwargs: _GitHubClient(calls)
    ):
        issue_health._record(True, "", "private")
        client = _client(cache)
        first = client.post("/issue-reports", data={"description": "broken"})
        second = client.post("/issue-reports", data={"description": "still broken"})

    assert first.status_code == 201
    assert second.status_code == 429
    assert second.json()["error_code"] == "RATE_001"
    assert second.headers["Retry-After"] == "42"
    # The refused report never reached GitHub.
    assert len([call for call in calls if call["method"] == "POST"]) == 1


def test_rate_limit_can_be_switched_off():
    calls: list[dict] = []
    with configured(GITHUB_ISSUE_REPORT_RATE_LIMIT_COUNT="0"), patch.object(
        issue_reports.httpx, "AsyncClient", lambda **kwargs: _GitHubClient(calls)
    ):
        issue_health._record(True, "", "private")
        client = _client()
        assert client.post("/issue-reports", data={"description": "one"}).status_code == 201
        assert client.post("/issue-reports", data={"description": "two"}).status_code == 201


# ---------------------------------------------------------------------------
# The issue names nobody; the database holds the join
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_issue_body_never_identifies_the_reporter():
    calls: list[dict] = []
    session = _Session()
    with configured(), patch.object(
        issue_reports.httpx, "AsyncClient", lambda **kwargs: _GitHubClient(calls)
    ):
        result = await issue_reports.submit_issue_report(
            IssueReportCreate(
                description="something broke",
                context={"email": "tester@example.org", "route": "/courses"},
            ),
            Principal(user_id="1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed"),
            session,
        )

    body = calls[-1]["json"]["body"]
    assert "1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed" not in body
    assert "tester@example.org" not in body
    # The report id is the only handle a maintainer gets.
    assert result.report_id in body


@pytest.mark.asyncio
async def test_the_report_row_records_the_reporter_and_the_issue():
    calls: list[dict] = []
    session = _Session()
    with configured(), patch.object(
        issue_reports.httpx, "AsyncClient", lambda **kwargs: _GitHubClient(calls)
    ):
        result = await issue_reports.submit_issue_report(
            IssueReportCreate(description="something broke"),
            Principal(user_id="1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed"),
            session,
        )

    row = session.report
    assert str(row.id) == result.report_id
    assert row.user_id == "1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed"
    assert row.repository == "computor-org/issues"
    assert row.issue_number == 123
    assert row.issue_url == "https://github.com/computor-org/issues/issues/123"


@pytest.mark.asyncio
async def test_a_failed_submission_still_leaves_a_row():
    """The row is written before GitHub is called, so the attempt is traceable."""

    class _Rejecting(_GitHubClient):
        async def post(self, url, headers=None, json=None):
            return _Response({"message": "nope"}, 500)

    session = _Session()
    with configured(), patch.object(
        issue_reports.httpx, "AsyncClient", lambda **kwargs: _Rejecting([])
    ), pytest.raises(issue_reports.IssueReportSubmissionError):
        await issue_reports.submit_issue_report(
            IssueReportCreate(description="something broke"),
            Principal(user_id="1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed"),
            session,
        )

    row = session.report
    assert row.issue_number is None
    assert row.issue_url is None


# ---------------------------------------------------------------------------
# Admin lookup — the only route back from a report id to a person
# ---------------------------------------------------------------------------


class _LookupSession(_Session):
    """Session stand-in serving one issue_report row through a query chain."""

    def __init__(self, record):
        super().__init__()
        self.record = record

    def query(self, model):
        return self

    def filter(self, *args):
        return self

    def first(self):
        return self.record


def _lookup_client(record, principal):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from computor_backend.api import issue_reports as issue_api
    from computor_backend.database import get_db
    from computor_backend.exceptions.error_handlers import register_exception_handlers
    from computor_backend.permissions.auth import get_current_principal

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(issue_api.router, prefix="/issue-reports")
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_db] = lambda: _LookupSession(record)
    return TestClient(app, raise_server_exceptions=False)


def _stored_report():
    from computor_backend.model.issue_report import IssueReport

    record = IssueReport(
        user_id="1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed",
        repository="computor-org/issues",
        issue_number=123,
        issue_url="https://github.com/computor-org/issues/issues/123",
    )
    record.id = uuid.UUID("2c8e7d6a-5b4f-4e3d-9a2b-1c0d9e8f7a6b")
    record.submitted_at = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    record.user = SimpleNamespace(
        email="tester@example.org", given_name="Tes", family_name="Ter"
    )
    return record


def test_an_admin_can_resolve_a_report_to_its_reporter():
    record = _stored_report()
    principal = Principal(user_id="admin-1")
    principal.is_admin = True
    with configured():
        response = _lookup_client(record, principal).get(f"/issue-reports/{record.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["user_email"] == "tester@example.org"
    assert body["issue_url"] == "https://github.com/computor-org/issues/issues/123"


def test_a_non_admin_cannot_resolve_a_report():
    record = _stored_report()
    with configured():
        response = _lookup_client(record, Principal(user_id="user-1")).get(
            f"/issue-reports/{record.id}"
        )

    assert response.status_code == 403


def test_a_missing_report_is_a_404():
    principal = Principal(user_id="admin-1")
    principal.is_admin = True
    with configured():
        response = _lookup_client(None, principal).get(
            "/issue-reports/2c8e7d6a-5b4f-4e3d-9a2b-1c0d9e8f7a6b"
        )

    assert response.status_code == 404
