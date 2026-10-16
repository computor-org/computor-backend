"""Verify real RSA signatures and reject algorithm/key confusion at the OIDC boundary."""
import base64
import hashlib
import hmac
import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from computor_backend.auth.keycloak import KeycloakAuthPlugin


@pytest.fixture
def verifier(monkeypatch):
    monkeypatch.delenv("KEYCLOAK_PUBLIC_URL", raising=False)
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key()))
    jwk.update(kid="test-key", alg="RS256", use="sig")
    plugin = KeycloakAuthPlugin()
    plugin.keycloak_config.client_id = "computor-backend"
    plugin.keycloak_config.server_url = "https://identity.example"
    plugin.keycloak_config.realm = "computor"
    plugin._oidc_config = {"issuer": "https://identity.example/realms/computor"}
    plugin._jwks = {"keys": [jwk]}
    claims = {"sub": "learner", "aud": "computor-backend",
              "iss": plugin._oidc_config["issuer"], "exp": int(time.time()) + 300}
    return plugin, private, claims


@pytest.mark.asyncio
async def test_valid_rs256_token(verifier):
    plugin, private, claims = verifier
    token = jwt.encode(claims, private, algorithm="RS256", headers={"kid": "test-key"})
    assert await plugin._verify_and_decode_token(token) == claims


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["aud", "iss", "exp", "kid", "signature"])
async def test_invalid_tokens_are_rejected(verifier, change):
    plugin, private, claims = verifier
    headers = {"kid": "test-key"}
    if change == "exp":
        claims["exp"] = int(time.time()) - 60
    elif change in ("aud", "iss"):
        claims[change] = "another-service"
    elif change == "kid":
        headers["kid"] = "unknown-key"
    elif change == "signature":
        private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jwt.encode(claims, private, algorithm="RS256", headers=headers)
    with pytest.raises(jwt.InvalidTokenError):
        await plugin._verify_and_decode_token(token)


@pytest.mark.asyncio
async def test_der_public_key_cannot_forge_hs256_token(verifier):
    plugin, private, claims = verifier
    def b64(data):
        return base64.urlsafe_b64encode(data).rstrip(b"=")
    header = b64(json.dumps({"alg": "HS256", "kid": "test-key"}).encode())
    payload = b64(json.dumps(claims).encode())
    signed = header + b"." + payload
    der = private.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    token = (signed + b"." + b64(hmac.new(der, signed, hashlib.sha256).digest())).decode()
    with pytest.raises(jwt.InvalidAlgorithmError):
        await plugin._verify_and_decode_token(token)
