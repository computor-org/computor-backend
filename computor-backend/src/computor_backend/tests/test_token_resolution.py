"""Fallback-order tests for git_provider.token_resolution.

The three call sites deliberately differ in fallback order (org token vs
binding vs server); these tests pin that behavior.
"""
from types import SimpleNamespace
from unittest.mock import patch

from computor_backend.git_provider.token_resolution import (
    CoursePushCredentials,
    resolve_binding_token,
)


def _patch_decrypt():
    return patch(
        "computor_backend.git_provider.token_resolution.decrypt_secret",
        side_effect=lambda s: f"dec({s})",
    )


def test_binding_token_wins_over_server_token():
    binding = SimpleNamespace(token="b-tok")
    server = SimpleNamespace(token="s-tok", managed=True)
    with _patch_decrypt():
        assert resolve_binding_token(binding, server) == "dec(b-tok)"


def test_server_token_fallback():
    binding = SimpleNamespace(token=None)
    server = SimpleNamespace(token="s-tok", managed=False)
    with _patch_decrypt():
        assert resolve_binding_token(binding, server) == "dec(s-tok)"


def test_managed_only_skips_unmanaged_server_token():
    binding = SimpleNamespace(token=None)
    server = SimpleNamespace(token="s-tok", managed=False)
    with _patch_decrypt():
        assert resolve_binding_token(binding, server, managed_only_server_token=True) is None


def test_managed_only_accepts_managed_server_token():
    binding = SimpleNamespace(token=None)
    server = SimpleNamespace(token="s-tok", managed=True)
    with _patch_decrypt():
        assert (
            resolve_binding_token(binding, server, managed_only_server_token=True)
            == "dec(s-tok)"
        )


def test_no_tokens_returns_none():
    assert resolve_binding_token(SimpleNamespace(token=None), None) is None


def test_rewrite_to_reachable_swaps_origin_only():
    creds = CoursePushCredentials(
        token="t",
        server_type="forgejo",
        public_base="http://git.example.com",
        reachable_base="http://forgejo:3000",
    )
    assert (
        creds.rewrite_to_reachable("http://git.example.com/org/repo.git")
        == "http://forgejo:3000/org/repo.git"
    )
    # different origin: untouched
    assert (
        creds.rewrite_to_reachable("http://other.example.com/org/repo.git")
        == "http://other.example.com/org/repo.git"
    )


def test_rewrite_noop_when_bases_match():
    creds = CoursePushCredentials(
        token="t",
        server_type="gitlab",
        public_base="http://git.example.com",
        reachable_base="http://git.example.com",
    )
    url = "http://git.example.com/org/repo.git"
    assert creds.rewrite_to_reachable(url) == url
