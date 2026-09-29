"""Public invite endpoints are throttled per client, and the client cannot pick its IP.

Reviewer repro: rotating a client-supplied ``Forwarded`` header let one TCP
peer make 31/31 status lookups, and ``GET /invites/{token}`` was not
throttled at all. The oracle is behavioural: which request gets the 429.
"""

import asyncio
from unittest.mock import MagicMock

import pytest
from starlette.requests import Request

from computor_backend.api import invites as invites_api
from computor_backend.exceptions import NotFoundException, RateLimitException
from computor_backend.utils.client_info import trusted_client_ip
from computor_types.invites import InviteAccept


def _request(peer: str, headers: dict | None = None) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    return Request({"type": "http", "client": (peer, 12345), "headers": raw,
                    "method": "GET", "path": "/"})


class _Cache:
    def __init__(self):
        self.data = {}

    async def incr(self, key):
        self.data[key] = self.data.get(key, 0) + 1
        return self.data[key]

    async def expire(self, key, seconds):
        return True


def _missing_invite_db():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    return db


def test_forwarding_headers_from_an_untrusted_peer_are_ignored():
    req = _request("203.0.113.9", {
        "X-Real-IP": "1.2.3.4", "X-Forwarded-For": "5.6.7.8", "Forwarded": "for=9.9.9.9",
    })
    assert trusted_client_ip(req) == "203.0.113.9"


def test_x_real_ip_is_used_only_behind_a_trusted_proxy():
    assert trusted_client_ip(_request("172.18.0.5", {"X-Real-IP": "198.51.100.7"})) == "198.51.100.7"
    assert trusted_client_ip(_request("172.18.0.5", {"X-Forwarded-For": "198.51.100.7"})) == "172.18.0.5"
    assert trusted_client_ip(_request("127.0.0.1", {"X-Real-IP": "not-an-ip"})) == "127.0.0.1"


def test_trusted_proxies_are_configurable(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "10.1.0.0/16")
    assert trusted_client_ip(_request("10.1.2.3", {"X-Real-IP": "198.51.100.7"})) == "198.51.100.7"
    assert trusted_client_ip(_request("172.18.0.5", {"X-Real-IP": "198.51.100.7"})) == "172.18.0.5"


def test_rotating_forwarded_headers_does_not_escape_the_lookup_limit():
    cache, db = _Cache(), _missing_invite_db()
    limit = invites_api.INVITE_LOOKUP_LIMIT
    for i in range(limit):
        req = _request("203.0.113.9", {"Forwarded": f"for=10.0.0.{i}",
                                       "X-Forwarded-For": f"10.1.0.{i}"})
        with pytest.raises(NotFoundException):
            asyncio.run(invites_api.get_invite_public("nope", request=req, db=db, cache=cache))
    req = _request("203.0.113.9", {"Forwarded": "for=10.9.9.9"})
    with pytest.raises(RateLimitException):
        asyncio.run(invites_api.get_invite_status("nope", request=req, db=db, cache=cache))
    # Another client is unaffected.
    with pytest.raises(NotFoundException):
        asyncio.run(invites_api.get_invite_public(
            "nope", request=_request("203.0.113.10"), db=db, cache=cache))


def test_invite_acceptance_is_throttled():
    cache, db = _Cache(), _missing_invite_db()
    payload = InviteAccept(given_name="A", family_name="B", email="a@example.test", password="x")
    for _ in range(invites_api.INVITE_ACCEPT_LIMIT):
        with pytest.raises(NotFoundException):
            asyncio.run(invites_api.accept_invite(
                "nope", payload, db=db, request=_request("203.0.113.9"), cache=cache))
    with pytest.raises(RateLimitException):
        asyncio.run(invites_api.accept_invite(
            "nope", payload, db=db, request=_request("203.0.113.9"), cache=cache))
