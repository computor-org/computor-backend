"""Behavioral tests for the server-side GitHub issue-report bridge."""

import base64
import json
import os
from contextlib import contextmanager
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
        result = await issue_reports.submit_issue_report(
            payload,
            Principal(user_id="user-1"),
            SimpleNamespace(get=lambda model, user_id: SimpleNamespace(email="tester@example.org")),
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
            SimpleNamespace(get=lambda model, user_id: None),
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
