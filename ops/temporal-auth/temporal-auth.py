#!/usr/bin/env python3
"""Signing key, key set and bearer tokens for Temporal's JWT authorizer
(ops/docker/docker-compose.temporal-auth.yaml).

    temporal-auth.py init DIR
        DIR/signing-key.pem  ES256 private key (keep it off the hosts, like the CA key)
        DIR/jwks.json        public key set -> TEMPORAL_AUTH_DIR on the Temporal host

    temporal-auth.py mint DIR SUBJECT PERMISSION... [--days N]
        Prints a token for TEMPORAL_API_KEY. PERMISSION is "<namespace>:<role>"
        with role read or write ("worker" grants nothing in Temporal 1.29).
        Example for a deployment with TEMPORAL_QUEUE_NAMESPACES=
        coder-tasks=computor-coder,testing*=computor-grading:
          control plane  default:write computor-coder:write computor-grading:write
          testing/matlab computor-grading:write
          coder worker   computor-coder:write

Only the Python standard library and cryptography are needed. Revoke every
token at once by running init in a fresh DIR and replacing jwks.json.
"""
import argparse
import base64
import hashlib
import json
import os
import sys
import time

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def public_jwk(key) -> dict:
    nums = key.public_key().public_numbers()
    jwk = {"crv": "P-256", "kty": "EC", "x": b64url(nums.x.to_bytes(32, "big")),
           "y": b64url(nums.y.to_bytes(32, "big"))}
    # RFC 7638 thumbprint as key id.
    kid = b64url(hashlib.sha256(json.dumps(jwk, sort_keys=True, separators=(",", ":")).encode()).digest())[:16]
    return {**jwk, "kid": kid, "use": "sig", "alg": "ES256"}


def load_key(directory: str):
    with open(os.path.join(directory, "signing-key.pem"), "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def cmd_init(directory: str) -> None:
    key_path = os.path.join(directory, "signing-key.pem")
    if os.path.exists(key_path):
        sys.exit(f"refusing to overwrite {key_path}")
    os.makedirs(directory, mode=0o700, exist_ok=True)
    key = ec.generate_private_key(ec.SECP256R1())
    fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                  serialization.NoEncryption()))
    with open(os.path.join(directory, "jwks.json"), "w") as f:
        json.dump({"keys": [public_jwk(key)]}, f, indent=1)
    print(f"wrote {key_path} and {os.path.join(directory, 'jwks.json')}")


def cmd_mint(directory: str, subject: str, permissions: list, days: int) -> None:
    for p in permissions:
        ns, _, role = p.rpartition(":")
        if not ns or role not in ("read", "write", "admin"):
            sys.exit(f"bad permission {p!r}: expected <namespace>:<read|write|admin>")
    key = load_key(directory)
    now = int(time.time())
    header = {"alg": "ES256", "typ": "JWT", "kid": public_jwk(key)["kid"]}
    claims = {"sub": subject, "permissions": permissions, "iat": now, "exp": now + days * 86400}
    signing_input = f"{b64url(json.dumps(header).encode())}.{b64url(json.dumps(claims).encode())}"
    r, s = decode_dss_signature(key.sign(signing_input.encode(), ec.ECDSA(hashes.SHA256())))
    print(f"{signing_input}.{b64url(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_init = sub.add_parser("init")
    p_init.add_argument("dir")
    p_mint = sub.add_parser("mint")
    p_mint.add_argument("dir")
    p_mint.add_argument("subject")
    p_mint.add_argument("permissions", nargs="+")
    p_mint.add_argument("--days", type=int, default=400)
    args = parser.parse_args()
    if args.cmd == "init":
        cmd_init(args.dir)
    else:
        cmd_mint(args.dir, args.subject, args.permissions, args.days)


if __name__ == "__main__":
    main()
