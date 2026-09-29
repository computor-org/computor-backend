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
from computor_backend.utils.client_info import forwarded_allow_ips, trusted_client_ip
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
    monkeypatch.setenv("FORWARDED_ALLOW_IPS", "10.1.0.0/16")
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


def test_wildcard_proxy_trust_is_never_used(monkeypatch):
    monkeypatch.setenv("FORWARDED_ALLOW_IPS", "*")
    assert "*" not in forwarded_allow_ips()


@pytest.mark.parametrize("endpoint,limit", [
    ("lookup", invites_api.INVITE_LOOKUP_LIMIT),
    ("accept", invites_api.INVITE_ACCEPT_LIMIT),
])
def test_one_client_is_one_bucket_through_the_real_uvicorn_proxy_middleware(
    monkeypatch, endpoint, limit
):
    """Reviewer repro r3, through Uvicorn's ProxyHeadersMiddleware configured
    exactly as server.py configures it in production.

    The client controls only the leftmost X-Forwarded-For entries (nginx
    appends the real peer, Traefik its own hop). Rotating them must not
    create new rate buckets.
    """
    from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

    monkeypatch.delenv("FORWARDED_ALLOW_IPS", raising=False)
    cache, db = _Cache(), _missing_invite_db()
    statuses, identities = [], []

    async def app(scope, receive, send):
        request = Request(scope)
        identities.append(trusted_client_ip(request))
        try:
            if endpoint == "lookup":
                await invites_api.get_invite_public("absent", request=request, db=db, cache=cache)
            else:
                await invites_api.accept_invite("absent", InviteAccept(
                    given_name="P", family_name="T", email="p@example.test", password="x"),
                    request=request, db=db, cache=cache)
        except RateLimitException:
            statuses.append(429)
        except NotFoundException:
            statuses.append(404)

    middleware = ProxyHeadersMiddleware(app, trusted_hosts=forwarded_allow_ips())
    for index in range(limit + 1):
        headers = [
            (b"x-real-ip", b"198.51.100.7"),
            (b"x-forwarded-for", f"203.0.113.{index + 1}, 198.51.100.7, 172.18.0.1".encode()),
        ]
        scope = {"type": "http", "client": ("172.18.0.5", 1234), "headers": headers,
                 "method": "GET", "path": "/", "scheme": "https"}
        asyncio.run(middleware(scope, None, None))

    assert set(identities) == {"198.51.100.7"}
    assert statuses == [404] * limit + [429]
