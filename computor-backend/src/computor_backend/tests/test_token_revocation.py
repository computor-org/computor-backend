"""Revoking an API token must take effect immediately, not after 15 minutes.

A Principal built from an API token is cached under a key derived from the *raw*
token (permissions/auth.py:principal_cache_key), which the server no longer has
after minting - so revocation cannot delete that entry. Dropping only the token
cache therefore left the token authenticating for up to AUTH_CACHE_TTL.

The fix is a kill-switch keyed by the token hash, checked on the principal
cache-HIT path (mirroring the per-user ban flag).
"""

from unittest.mock import AsyncMock, patch

import pytest

from computor_backend.exceptions import UnauthorizedException
from computor_backend.permissions import api_token_cache
from computor_backend.permissions.api_token_cache import (
    REVOKED_FLAG_PREFIX,
    REVOKED_FLAG_TTL,
)
from computor_backend.permissions.auth import AUTH_CACHE_TTL, _get_cached_principal
from computor_backend.permissions.principal import Principal


TOKEN_HASH_HEX = "f" * 64
CACHE_KEY = "some-principal-cache-key"


class FakeRedis:
    """Minimal async Redis stand-in recording set/get/delete."""

    def __init__(self, values=None):
        self.values = dict(values or {})
        self.sets = []
        self.deleted = []

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, ex=None):
        self.values[key] = value
        self.sets.append((key, value, ex))

    async def delete(self, *keys):
        for key in keys:
            self.deleted.append(key)
            self.values.pop(key, None)


def _principal_json():
    return Principal(user_id="11111111-1111-1111-1111-111111111111", roles=["user"]).model_dump_json()


@pytest.mark.asyncio
async def test_revocation_raises_the_kill_switch_and_drops_the_token_cache():
    redis = FakeRedis()
    with patch("computor_backend.redis_cache.get_redis_client", AsyncMock(return_value=redis)):
        await api_token_cache.revoke_token_caches(TOKEN_HASH_HEX)

    assert f"api_token:auth:{TOKEN_HASH_HEX}" in redis.deleted
    flag_key = f"{REVOKED_FLAG_PREFIX}{TOKEN_HASH_HEX}"
    assert flag_key in redis.values
    assert redis.sets[-1][2] == REVOKED_FLAG_TTL


@pytest.mark.asyncio
async def test_cached_principal_is_rejected_for_a_revoked_token():
    """The regression: a warm principal cache must not outlive revocation."""
    redis = FakeRedis({
        CACHE_KEY: _principal_json(),
        f"{REVOKED_FLAG_PREFIX}{TOKEN_HASH_HEX}": "1",
    })
    with patch("computor_backend.permissions.auth.get_redis_client", AsyncMock(return_value=redis)), \
         patch("computor_backend.redis_cache.get_redis_client", AsyncMock(return_value=redis)), \
         patch("computor_backend.permissions.auth.is_user_banned_cached", AsyncMock(return_value=False)):
        with pytest.raises(UnauthorizedException):
            await _get_cached_principal(CACHE_KEY, TOKEN_HASH_HEX)


@pytest.mark.asyncio
async def test_cached_principal_still_served_for_a_live_token():
    redis = FakeRedis({CACHE_KEY: _principal_json()})
    with patch("computor_backend.permissions.auth.get_redis_client", AsyncMock(return_value=redis)), \
         patch("computor_backend.redis_cache.get_redis_client", AsyncMock(return_value=redis)), \
         patch("computor_backend.permissions.auth.is_user_banned_cached", AsyncMock(return_value=False)):
        principal = await _get_cached_principal(CACHE_KEY, TOKEN_HASH_HEX)

    assert principal is not None
    assert principal.user_id == "11111111-1111-1111-1111-111111111111"


@pytest.mark.asyncio
async def test_revocation_check_fails_open_on_redis_errors():
    """A Redis outage must not lock everyone out; the DB gate is the backstop."""
    boom = AsyncMock(side_effect=RuntimeError("redis down"))
    with patch("computor_backend.redis_cache.get_redis_client", boom):
        assert await api_token_cache.is_token_revoked(TOKEN_HASH_HEX) is False


@pytest.mark.asyncio
async def test_middleware_ignores_the_cache_for_a_revoked_token():
    from computor_backend.middleware import principal_lookup

    scope = {"headers": [(b"x-api-token", b"ctp_" + b"a" * 32)]}
    with patch.object(principal_lookup, "_check_principal_cache",
                      AsyncMock(return_value={"user_id": "u1"})), \
         patch.object(principal_lookup, "_api_token_revoked", AsyncMock(return_value=True)), \
         patch.object(principal_lookup, "_resolve_api_token_from_db", lambda token: None):
        assert await principal_lookup.resolve_principal_from_scope(scope) is None


def test_flag_outlives_the_principal_cache():
    """If AUTH_CACHE_TTL is ever raised past the flag TTL, the window reopens."""
    assert REVOKED_FLAG_TTL >= AUTH_CACHE_TTL
