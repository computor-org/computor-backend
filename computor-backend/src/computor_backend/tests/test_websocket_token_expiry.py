"""Unit tests for WebSocket credential expiry (computor-org/issues#257).

Before this, ``websocket/auth.py`` authenticated once at the handshake and
nothing ever revisited it. A socket therefore outlived the token that opened
it: HTTP started answering 401 while the connection sat there delivering
events, and the client only learned its session was gone from the next failed
request. Four things are pinned here:

1. **The handshake resolves an expiry** — from the API token's ``expires_at``
   or from the SSO session key's own Redis TTL, not from an assumed full
   ``SSO_SESSION_TTL`` (a socket may open against a session most of the way
   through its life).

2. **Re-resolution is non-refreshing and sliding-aware** — ``ttl``, never
   ``expire``, or a connection would keep its own session alive forever and
   the deadline would never arrive. A vanished key means the session ended.

3. **The watchdog closes with 4003**, not 4001. The two codes drive different
   client behaviour (silent refresh vs. ask the user to sign in), so they must
   be distinguishable without parsing a reason string.

4. **``system:reauth`` re-arms a live connection**, and refuses to swap the
   principal underneath subscriptions that were authorised against the
   original one.

Redis and the auth service are stubbed: what is under test is the expiry logic
itself, not that redis-py can read a TTL.
"""

import asyncio
import datetime
from dataclasses import dataclass, field
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from computor_backend.websocket import auth as ws_auth
from computor_backend.websocket import handlers as ws_handlers
from computor_backend.websocket import router as ws_router
from computor_backend.websocket.auth import (
    WebSocketAuthError,
    WebSocketCredential,
    WS_CLOSE_AUTH_FAILED,
    WS_CLOSE_TOKEN_EXPIRED,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


@dataclass
class FakeWebSocket:
    """Records the close it was asked to perform."""

    closed_with: list = field(default_factory=list)

    async def close(self, code: int, reason: str = "") -> None:
        self.closed_with.append((code, reason))


@dataclass
class FakeConnection:
    """A Connection stand-in — the watchdog only touches these three fields."""

    principal: SimpleNamespace
    credential: object = None
    websocket: FakeWebSocket = field(default_factory=FakeWebSocket)


def _connection(credential=None, user_id="u-1") -> FakeConnection:
    return FakeConnection(principal=SimpleNamespace(user_id=user_id), credential=credential)


# ---------------------------------------------------------------------------
# 1. The handshake resolves an expiry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sso_expiry_comes_from_the_key_ttl_not_a_fresh_full_ttl():
    """A socket opening against a half-spent session must inherit what is left.

    The handshake does refresh the TTL (it is user activity like any request),
    so the deadline is a full TTL from *now* — the point of the assertion is
    that it is derived from the constant rather than from a guess, and that the
    session key is kept so the sliding TTL can be re-read later.
    """
    redis = AsyncMock()
    redis.get.return_value = '{"user_id": "u-1", "provider": "keycloak"}'

    principal = SimpleNamespace(user_id="u-1")
    before = _utcnow()

    with patch.object(ws_auth, "get_redis_client", AsyncMock(return_value=redis)), \
         patch.object(ws_auth, "get_db_session"), \
         patch.object(ws_auth.PrincipalBuilder, "build", return_value=principal):
        _, credential = await ws_auth._authenticate_sso_token("session-token")

    assert credential.kind == "sso"
    assert credential.session_key.startswith("sso_session:")
    expected = before + datetime.timedelta(seconds=ws_auth.SSO_SESSION_TTL)
    assert abs((credential.expires_at - expected).total_seconds()) < 5


@pytest.mark.asyncio
async def test_sso_auth_can_read_the_remaining_ttl_without_sliding_it():
    """The reauth path must not renew a session just because a socket asked.

    ``expire`` here would let a connection answer every expiry warning with the
    same token and never die — exactly the immortal-socket state this issue
    exists to end. A genuine refresh mints a new session with a full TTL of its
    own, so refusing to slide the old one costs nothing legitimate.
    """
    redis = AsyncMock()
    redis.get.return_value = '{"user_id": "u-1", "provider": "keycloak"}'
    redis.ttl.return_value = 120

    with patch.object(ws_auth, "get_redis_client", AsyncMock(return_value=redis)), \
         patch.object(ws_auth, "get_db_session"), \
         patch.object(ws_auth.PrincipalBuilder, "build", return_value=SimpleNamespace(user_id="u-1")):
        _, credential = await ws_auth._authenticate_sso_token("tok", refresh_session_ttl=False)

    redis.expire.assert_not_called()
    remaining = (credential.expires_at - _utcnow()).total_seconds()
    assert 110 < remaining <= 120


@pytest.mark.asyncio
async def test_api_token_expiry_is_read_from_the_token_cache():
    """``expires_at`` rides along in the cache the auth path just populated."""
    cached = SimpleNamespace(expires_at="2026-09-01T12:00:00+00:00")

    with patch(
        "computor_backend.permissions.api_token_cache.get_cached_token_data",
        AsyncMock(return_value=cached),
    ):
        expires_at = await ws_auth._api_token_expiry("ctp_" + "x" * 32)

    assert expires_at == datetime.datetime(2026, 9, 1, 12, 0, tzinfo=datetime.timezone.utc)


@pytest.mark.asyncio
async def test_api_token_without_expiry_is_left_unwatched():
    """A token minted without a deadline gets none invented for it."""
    cached = SimpleNamespace(expires_at=None)

    with patch(
        "computor_backend.permissions.api_token_cache.get_cached_token_data",
        AsyncMock(return_value=cached),
    ):
        assert await ws_auth._api_token_expiry("ctp_" + "x" * 32) is None


@pytest.mark.asyncio
async def test_unreadable_cache_leaves_the_connection_unwatched_not_closed():
    """A cache outage must not start closing healthy connections.

    Falling back to "no deadline known" is exactly the pre-#257 behaviour, and
    the HTTP path still enforces expiry — so this is never worse than before,
    whereas guessing a deadline would drop live sockets during a Redis blip.
    """
    with patch(
        "computor_backend.permissions.api_token_cache.get_cached_token_data",
        AsyncMock(side_effect=RuntimeError("redis down")),
    ):
        assert await ws_auth._api_token_expiry("ctp_" + "x" * 32) is None


# ---------------------------------------------------------------------------
# 2. Re-resolution is non-refreshing and sliding-aware
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sso_reresolution_reads_the_ttl_and_never_refreshes_it():
    """``expire`` here would make a connection immortal by keeping itself alive."""
    redis = AsyncMock()
    redis.ttl.return_value = 1800
    credential = WebSocketCredential(kind="sso", session_key="sso_session:abc")

    with patch.object(ws_auth, "get_redis_client", AsyncMock(return_value=redis)):
        expires_at = await ws_auth.current_credential_expiry(credential)

    redis.expire.assert_not_called()
    assert abs((expires_at - (_utcnow() + datetime.timedelta(seconds=1800))).total_seconds()) < 5


@pytest.mark.asyncio
async def test_vanished_sso_session_is_reported_as_expired():
    """Redis answers -2 for "no such key" — the session ended, or was signed out."""
    redis = AsyncMock()
    redis.ttl.return_value = -2
    credential = WebSocketCredential(kind="sso", session_key="sso_session:abc")

    with patch.object(ws_auth, "get_redis_client", AsyncMock(return_value=redis)):
        with pytest.raises(WebSocketAuthError) as excinfo:
            await ws_auth.current_credential_expiry(credential)

    assert excinfo.value.code == WS_CLOSE_TOKEN_EXPIRED


@pytest.mark.asyncio
async def test_sso_key_without_a_ttl_is_left_unwatched():
    """-1 means a key with no expiry: nothing to watch, so stop watching."""
    redis = AsyncMock()
    redis.ttl.return_value = -1
    credential = WebSocketCredential(kind="sso", session_key="sso_session:abc")

    with patch.object(ws_auth, "get_redis_client", AsyncMock(return_value=redis)):
        assert await ws_auth.current_credential_expiry(credential) is None


@pytest.mark.asyncio
async def test_api_token_reresolution_returns_its_fixed_deadline():
    """No Redis round-trip: an API token's ``expires_at`` does not move."""
    deadline = _utcnow() + datetime.timedelta(hours=1)
    credential = WebSocketCredential(kind="api_token", expires_at=deadline)

    assert await ws_auth.current_credential_expiry(credential) == deadline


# ---------------------------------------------------------------------------
# 3. The watchdog closes with 4003
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_watchdog_closes_an_expired_connection_with_its_own_code():
    connection = _connection(
        WebSocketCredential(kind="api_token", expires_at=_utcnow() - datetime.timedelta(seconds=1))
    )

    with patch.object(ws_router.manager, "send_to_connection", AsyncMock()) as send:
        await ws_router._watch_credential_expiry(connection)

    assert connection.websocket.closed_with == [(WS_CLOSE_TOKEN_EXPIRED, "Token expired")]
    assert send.await_args.args[1]["code"] == "TOKEN_EXPIRED"
    # 4001 means "your token was rejected" and asks the user for a new one;
    # this path must never borrow it, or a client that could have refreshed
    # silently would send the student to a sign-in prompt instead.
    assert WS_CLOSE_TOKEN_EXPIRED != WS_CLOSE_AUTH_FAILED


@pytest.mark.asyncio
async def test_watchdog_warns_once_before_the_deadline_then_closes():
    """The warning is what makes an in-place reauth possible at all."""
    connection = _connection(
        WebSocketCredential(
            kind="api_token",
            expires_at=_utcnow() + datetime.timedelta(seconds=2),
        )
    )
    sent = []

    async def _record(_conn, payload):
        sent.append(payload)

    with patch.object(ws_router.manager, "send_to_connection", _record), \
         patch.object(ws_router.asyncio, "sleep", AsyncMock()):
        await asyncio.wait_for(ws_router._watch_credential_expiry(connection), timeout=5)

    warnings = [p for p in sent if p["type"] == "system:auth_expiring"]
    assert len(warnings) == 1, "one warning per deadline, not one per poll"
    assert warnings[0]["seconds_remaining"] <= ws_router.EXPIRY_WARNING_LEAD_SECONDS
    assert connection.websocket.closed_with[-1][0] == WS_CLOSE_TOKEN_EXPIRED


@pytest.mark.asyncio
async def test_watchdog_stops_watching_a_credential_without_an_expiry():
    """No deadline, no timer — and no busy loop pretending there is one."""
    connection = _connection(WebSocketCredential(kind="api_token", expires_at=None))

    with patch.object(ws_router.manager, "send_to_connection", AsyncMock()):
        await asyncio.wait_for(ws_router._watch_credential_expiry(connection), timeout=5)

    assert connection.websocket.closed_with == []


@pytest.mark.asyncio
async def test_watchdog_picks_up_an_extended_deadline_without_restarting():
    """A successful reauth replaces the credential; the next wake must see it.

    This is the whole reason the loop re-reads ``connection.credential`` rather
    than closing over the deadline it started with.
    """
    connection = _connection(
        WebSocketCredential(kind="api_token", expires_at=_utcnow() + datetime.timedelta(seconds=5))
    )
    wakes = {"n": 0}

    async def _sleep(_seconds):
        wakes["n"] += 1
        if wakes["n"] == 1:
            # The client refreshed in the meantime.
            connection.credential = WebSocketCredential(
                kind="api_token", expires_at=_utcnow() + datetime.timedelta(seconds=5)
            )
        if wakes["n"] >= 3:
            # Now let it actually die, so the loop terminates.
            connection.credential = WebSocketCredential(
                kind="api_token", expires_at=_utcnow() - datetime.timedelta(seconds=1)
            )

    with patch.object(ws_router.manager, "send_to_connection", AsyncMock()), \
         patch.object(ws_router.asyncio, "sleep", _sleep):
        await asyncio.wait_for(ws_router._watch_credential_expiry(connection), timeout=5)

    assert wakes["n"] >= 3, "the extended deadline should have kept the loop alive"
    assert connection.websocket.closed_with[-1][0] == WS_CLOSE_TOKEN_EXPIRED


@pytest.mark.asyncio
async def test_watchdog_survives_a_redis_blip():
    """A failed re-read backs off; it does not take a healthy connection down."""
    connection = _connection(WebSocketCredential(kind="sso", session_key="sso_session:abc"))
    calls = {"n": 0}

    async def _expiry(_credential):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("redis down")
        return None  # second read succeeds and finds nothing to watch

    with patch.object(ws_router, "current_credential_expiry", _expiry), \
         patch.object(ws_router.manager, "send_to_connection", AsyncMock()), \
         patch.object(ws_router.asyncio, "sleep", AsyncMock()):
        await asyncio.wait_for(ws_router._watch_credential_expiry(connection), timeout=5)

    assert calls["n"] == 2
    assert connection.websocket.closed_with == []


# ---------------------------------------------------------------------------
# 4. system:reauth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reauth_replaces_the_credential_and_confirms_the_new_deadline():
    connection = _connection(
        WebSocketCredential(kind="sso", expires_at=_utcnow() + datetime.timedelta(seconds=10))
    )
    new_deadline = _utcnow() + datetime.timedelta(hours=1)
    fresh = WebSocketCredential(kind="sso", expires_at=new_deadline, session_key="sso_session:new")
    sent = []

    async def _record(_conn, payload):
        sent.append(payload)

    with patch.object(
        ws_handlers,
        "authenticate_websocket_token",
        AsyncMock(return_value=(SimpleNamespace(user_id="u-1"), fresh)),
    ), patch.object(ws_handlers.manager, "send_to_connection", _record):
        await ws_handlers.handle_reauth(connection, SimpleNamespace(token="new-token"))

    assert connection.credential is fresh
    assert sent[-1]["type"] == "system:reauthed"
    assert connection.websocket.closed_with == []


@pytest.mark.asyncio
async def test_reauth_never_slides_the_session_it_authenticates_against():
    """Pinned at the call site too: the handler must ask for a non-refreshing read."""
    connection = _connection(WebSocketCredential(kind="sso"))
    authenticate = AsyncMock(
        return_value=(SimpleNamespace(user_id="u-1"), WebSocketCredential(kind="sso"))
    )

    with patch.object(ws_handlers, "authenticate_websocket_token", authenticate), \
         patch.object(ws_handlers.manager, "send_to_connection", AsyncMock()):
        await ws_handlers.handle_reauth(connection, SimpleNamespace(token="new-token"))

    assert authenticate.await_args.kwargs["refresh_session_ttl"] is False


@pytest.mark.asyncio
async def test_reauth_refuses_to_change_identity_mid_connection():
    """Subscriptions were authorised against the principal that opened the socket.

    Accepting another user's token would hand them every channel the first user
    was already listening to, so a mismatch is a failed reauth, not a switch.
    """
    connection = _connection(WebSocketCredential(kind="sso"), user_id="u-1")
    sent = []

    async def _record(_conn, payload):
        sent.append(payload)

    with patch.object(
        ws_handlers,
        "authenticate_websocket_token",
        AsyncMock(return_value=(SimpleNamespace(user_id="u-2"), WebSocketCredential(kind="sso"))),
    ), patch.object(ws_handlers.manager, "send_to_connection", _record):
        await ws_handlers.handle_reauth(connection, SimpleNamespace(token="someone-elses"))

    assert connection.credential.expires_at is None  # unchanged, not swapped
    assert sent[-1]["code"] == "REAUTH_FAILED"
    assert connection.websocket.closed_with[-1][0] == WS_CLOSE_TOKEN_EXPIRED


@pytest.mark.asyncio
async def test_reauth_with_a_dead_token_closes_rather_than_lingering():
    connection = _connection(WebSocketCredential(kind="sso"))
    sent = []

    async def _record(_conn, payload):
        sent.append(payload)

    with patch.object(
        ws_handlers,
        "authenticate_websocket_token",
        AsyncMock(side_effect=WebSocketAuthError(WS_CLOSE_AUTH_FAILED, "Invalid or expired token")),
    ), patch.object(ws_handlers.manager, "send_to_connection", _record):
        await ws_handlers.handle_reauth(connection, SimpleNamespace(token="dead"))

    assert sent[-1]["code"] == "REAUTH_FAILED"
    assert connection.websocket.closed_with[-1][0] == WS_CLOSE_TOKEN_EXPIRED
