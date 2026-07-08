"""Tests for the synchronous facade and the shared error handler."""
import httpx
import pytest

from computor_client import ComputorClient, SyncComputorClient
from computor_client.exceptions import (
    AuthorizationError,
    ComputorClientError,
    ConflictError,
    NotFoundError,
    raise_for_response,
)


def _resp(status, json=None, text=None, headers=None):
    kwargs = {"request": httpx.Request("GET", "http://x/y")}
    if json is not None:
        kwargs["json"] = json
    if text is not None:
        kwargs["text"] = text
    if headers is not None:
        kwargs["headers"] = headers
    return httpx.Response(status, **kwargs)


class TestRaiseForResponse:
    def test_2xx_is_noop(self):
        raise_for_response(_resp(200, json={"ok": True}))
        raise_for_response(_resp(204))

    @pytest.mark.parametrize(
        "status,exc",
        [(401, ComputorClientError), (403, AuthorizationError),
         (404, NotFoundError), (409, ConflictError)],
    )
    def test_maps_status(self, status, exc):
        with pytest.raises(exc) as ei:
            raise_for_response(_resp(status, json={"detail": "boom", "error_code": "E1"}))
        assert ei.value.status_code == status
        assert ei.value.error_code == "E1"

    def test_rate_limit_retry_after(self):
        from computor_client.exceptions import RateLimitError

        with pytest.raises(RateLimitError) as ei:
            raise_for_response(_resp(429, json={"detail": "slow"}, headers={"Retry-After": "7"}))
        assert ei.value.retry_after == 7

    def test_non_json_body(self):
        with pytest.raises(NotFoundError) as ei:
            raise_for_response(_resp(404, text="plain not found"))
        assert "plain not found" in str(ei.value)


class TestFromClient:
    def test_inherits_base_url_headers_timeout(self):
        c = ComputorClient(base_url="http://api.example/", headers={"X-API-Token": "tok"}, timeout=12.0)
        s = SyncComputorClient.from_client(c)
        assert s._client.base_url.host == "api.example"
        assert s._client.headers.get("x-api-token") == "tok"
        # merged defaults present
        assert s._client.headers.get("content-type") == "application/json"

    def test_token_auth_has_no_bearer(self):
        c = ComputorClient(base_url="http://x", headers={"X-API-Token": "tok"})
        # no session access token → no Authorization header
        assert "Authorization" not in c.auth_headers

    def test_context_manager_closes(self):
        with SyncComputorClient("http://x", headers={"X-API-Token": "t"}) as s:
            assert not s._client.is_closed
        assert s._client.is_closed
