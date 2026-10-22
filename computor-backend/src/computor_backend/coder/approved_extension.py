"""The Computor extension version this backend approves for its workspaces.

``approved_extension.json`` pins one GitHub release of computor-vscode by
version and sha256. Each backend branch carries its own pin, so the instance
deployed from it follows that extension line (main: 2027.3.x,
release/2026.10: 2026.10.x). Bump it with ``ops/coder/pin-extension.py``.

At startup the backend makes sure the pinned release is in its own extension
registry: it downloads the release VSIX once, refuses it unless the sha256
matches the pin, and publishes it through the registry's publish endpoint.
Workspaces install the newest non-yanked registry version in place
(ops/coder/templates/README.md, "Extension updates"). A version an admin has
yanked stays yanked.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import re
import urllib.request
from pathlib import Path

PIN_FILE = Path(__file__).with_name("approved_extension.json")
RELEASE_URL = "https://github.com/computor-org/computor-vscode/releases/download/v{version}/computor-{version}.vsix"


def load_pin(path: Path | None = None) -> dict:
    path = path or PIN_FILE
    pin = json.loads(path.read_text())
    if pin.get("extension") != "computor-org.computor":
        raise ValueError(f"{path.name}: extension must be computor-org.computor")
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(pin.get("version", ""))):
        raise ValueError(f"{path.name}: version must be a release version x.y.z")
    if not re.fullmatch(r"[0-9a-f]{64}", str(pin.get("sha256", ""))):
        raise ValueError(f"{path.name}: sha256 must be 64 lowercase hex digits")
    return pin


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


async def ensure_approved_extension() -> str:
    """Publish the pinned release into the registry unless it is there already."""
    from fastapi import UploadFile

    from computor_backend.api.extensions import publish_extension_version
    from computor_backend.database import get_db_session
    from computor_backend.model.extension import Extension, ExtensionVersion
    from computor_backend.permissions.principal import Principal
    from computor_backend.services.storage_service import get_storage_service

    pin = load_pin()
    publisher, name = pin["extension"].split(".", 1)
    version = pin["version"]
    with get_db_session() as db:
        present = (
            db.query(ExtensionVersion.id)
            .join(Extension, Extension.id == ExtensionVersion.extension_id)
            .filter(Extension.publisher == publisher, Extension.name == name,
                    ExtensionVersion.version == version)
            .first()
        )
    if present:
        return f"{pin['extension']} {version} already in the registry"

    vsix = await asyncio.to_thread(_download, RELEASE_URL.format(version=version))
    digest = hashlib.sha256(vsix).hexdigest()
    if digest != pin["sha256"]:
        raise ValueError(f"{pin['extension']} {version}: download sha256 {digest} does not match the pin")
    with get_db_session() as db:
        await publish_extension_version(
            pin["extension"],
            version=version,
            engine_range=None,
            file=UploadFile(io.BytesIO(vsix), filename=f"computor-{version}.vsix"),
            display_name=None,
            description=None,
            permissions=Principal(is_admin=True),
            db=db,
            storage_service=get_storage_service(),
        )
    return f"{pin['extension']} {version} approved (sha256 {digest})"
