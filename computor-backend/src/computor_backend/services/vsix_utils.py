"""Utility helpers for working with VSIX packages."""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from typing import Optional
from xml.etree import ElementTree as ET


@dataclass
class VsixMetadata:
    """Metadata extracted from a VSIX manifest."""

    publisher: str
    name: str
    version: str
    display_name: Optional[str]
    description: Optional[str]
    engine_range: Optional[str]


class VsixManifestError(ValueError):
    """Raised when the VSIX manifest cannot be parsed."""


_VSIX_MANIFEST_PATH = "extension.vsixmanifest"
_VSIX_NAMESPACE = {"ns": "http://schemas.microsoft.com/developer/vsx-schema/2011"}


def _find_dependency_version(root: ET.Element) -> Optional[str]:
    """Return the VS Code engine dependency range if present."""

    dependencies = root.findall(".//ns:Dependency", namespaces=_VSIX_NAMESPACE)
    for dependency in dependencies:
        dep_id = dependency.attrib.get("Id") or dependency.attrib.get("id")
        if dep_id and dep_id.lower() in {"microsoft.visualstudio.code", "vscode"}:
            version_attr = dependency.attrib.get("Version") or dependency.attrib.get("version")
            if version_attr:
                return version_attr
    return None


def parse_vsix_metadata(file_bytes: bytes) -> VsixMetadata:
    """Extract identity metadata from a VSIX package.

    Args:
        file_bytes: Raw VSIX archive bytes.

    Returns:
        VsixMetadata containing identity, version and optional fields.

    Raises:
        VsixManifestError: If the archive or manifest is invalid.
    """

    try:
        archive = zipfile.ZipFile(io.BytesIO(file_bytes))
    except zipfile.BadZipFile as exc:
        raise VsixManifestError("Uploaded file is not a valid VSIX archive") from exc

    try:
        with archive.open(_VSIX_MANIFEST_PATH) as manifest_file:
            tree = ET.parse(manifest_file)
    except KeyError as exc:
        raise VsixManifestError("VSIX manifest 'extension.vsixmanifest' not found") from exc
    except ET.ParseError as exc:
        raise VsixManifestError("VSIX manifest is not well-formed XML") from exc

    root = tree.getroot()

    identity = root.find(".//ns:Identity", namespaces=_VSIX_NAMESPACE)
    if identity is None:
        raise VsixManifestError("VSIX manifest is missing the Identity element")

    publisher = identity.attrib.get("Publisher") or identity.attrib.get("publisher")
    name = identity.attrib.get("Id") or identity.attrib.get("id")
    version = identity.attrib.get("Version") or identity.attrib.get("version")

    if not publisher or not name or not version:
        raise VsixManifestError("VSIX Identity must include Publisher, Id, and Version")

    display_name = root.findtext(".//ns:DisplayName", namespaces=_VSIX_NAMESPACE)
    description = root.findtext(".//ns:Description", namespaces=_VSIX_NAMESPACE)
    engine_range = _find_dependency_version(root)

    return VsixMetadata(
        publisher=publisher,
        name=name,
        version=version,
        display_name=display_name,
        description=description,
        engine_range=engine_range,
    )

