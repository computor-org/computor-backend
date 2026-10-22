"""The extension pin each backend branch deploys, and its startup registration."""

import hashlib
import json
import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

from computor_backend.coder import approved_extension


def test_pin_is_well_formed():
    pin = approved_extension.load_pin()
    assert pin["extension"] == "computor-org.computor"


@pytest.mark.parametrize("change, message", [
    ({"version": "2027.3"}, "version"),
    ({"version": "2027.3.4-rc.1"}, "version"),
    ({"sha256": "30989B50" + "0" * 56}, "sha256"),
    ({"sha256": "abc"}, "sha256"),
    ({"extension": "someone.else"}, "extension"),
])
def test_malformed_pins_are_rejected(tmp_path, change, message):
    path = tmp_path / "approved_extension.json"
    path.write_text(json.dumps({**approved_extension.load_pin(), **change}))
    with pytest.raises(ValueError, match=message):
        approved_extension.load_pin(path)


@pytest.mark.skipif(not os.environ.get("COMPUTOR_NETWORK_TESTS"), reason="needs GitHub (COMPUTOR_NETWORK_TESTS=1)")
def test_pin_matches_its_github_release():
    script = next(p for p in Path(__file__).resolve().parents if (p / "ops").is_dir()) / "ops/coder/pin-extension.py"
    subprocess.run([sys.executable, str(script), "--check"], check=True, timeout=300)


class _Query:
    def __init__(self, row):
        self.row = row

    def __getattr__(self, name):
        return lambda *a, **k: self if name != "first" else self.row


@pytest.fixture
def registry(monkeypatch):
    """Stubs the DB lookup, the download and the publish endpoint."""
    import computor_backend.api.extensions as extensions_api
    import computor_backend.database as database
    import computor_backend.services.storage_service as storage

    state = {"present": None, "payload": b"", "published": [], "downloads": 0}

    class _Db:
        def query(self, *a):
            return _Query(state["present"])

    @contextmanager
    def session():
        yield _Db()

    def download(url):
        state["downloads"] += 1
        assert url.endswith(f"/v{pin['version']}/computor-{pin['version']}.vsix")
        return state["payload"]

    async def publish(identity, **kwargs):
        state["published"].append((identity, kwargs["version"], await kwargs["file"].read()))

    pin = approved_extension.load_pin()
    monkeypatch.setattr(database, "get_db_session", session)
    monkeypatch.setattr(extensions_api, "publish_extension_version", publish)
    monkeypatch.setattr(storage, "get_storage_service", lambda: None)
    monkeypatch.setattr(approved_extension, "_download", download)
    return state, pin


async def _ensure():
    return await approved_extension.ensure_approved_extension()


def test_present_pin_is_not_downloaded_again(registry):
    import asyncio
    state, pin = registry
    state["present"] = ("id",)
    assert "already in the registry" in asyncio.run(_ensure())
    assert state["downloads"] == 0 and state["published"] == []


def test_missing_pin_is_published_only_with_the_pinned_checksum(registry, monkeypatch, tmp_path):
    import asyncio
    state, pin = registry
    payload = b"a vsix"
    path = tmp_path / "approved_extension.json"
    path.write_text(json.dumps({**pin, "sha256": hashlib.sha256(payload).hexdigest()}))
    monkeypatch.setattr(approved_extension, "PIN_FILE", path)

    state["payload"] = b"tampered"
    with pytest.raises(ValueError, match="does not match the pin"):
        asyncio.run(_ensure())
    assert state["published"] == []

    state["payload"] = payload
    assert "approved" in asyncio.run(_ensure())
    assert state["published"] == [(pin["extension"], pin["version"], payload)]
