"""Filesystem access to the deployed Coder template directories.

Backs the raw template editing + variable listing endpoints in
``api/coder.py``. All reads/writes target the DEPLOYED templates dir
(``${SYSTEM_DEPLOYMENT_PATH}/coder/templates``, mounted at
``CODER_TEMPLATES_DIR`` in containers) — the same files ``coder templates
push`` consumes — never the repo copy under ``ops/coder/templates``.

Customization contract (see computor.sh): a deployed template dir carrying a
``.computor-managed`` marker is re-synced from the repo on every startup.
Any edit through this module therefore REMOVES the marker, flipping the
template to operator-customized so startup stops clobbering it;
``restore_managed`` re-creates the marker, and the repo defaults return on
the next system restart.

Templates created through the API (``clone_template``) exist ONLY in the
deployed dir. computor.sh iterates the repo's template dirs, never the deployed
root, so such a dir is never visited — it carries no marker and ``cloned_from``
in its manifest marks it as created here (the only kind that may be deleted).
"""

import json
import os
import re
import shutil
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import hcl2

MANAGED_MARKER = ".computor-managed"

# Whitelist for raw editing: the template contract files only, no paths.
_FILE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

_MAX_FILE_BYTES = 512 * 1024

# Template KEY = directory name of a template created here: lowercase
# alphanumerics with inner hyphens, i.e. a Coder template name minus the
# "-workspace" suffix that is derived from it. 22 chars keeps the derived Coder
# name inside Coder's 32-char limit.
TEMPLATE_KEY_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
TEMPLATE_KEY_MAX_LEN = 22
CODER_TEMPLATE_SUFFIX = "-workspace"
IMAGE_NAME_PREFIX = "computor-workspace-"

# An icon is an absolute http(s) URL (the web UI renders it as an image) or one
# of Coder's built-in /icon/*.svg paths. Nothing else: no javascript:/data:
# URLs, no relative paths.
_ICON_RE = re.compile(r"^(?:https?://\S+|/icon/[A-Za-z0-9._-]+\.(?:svg|png))$")

# A clone is assembled in a dot-prefixed staging dir and renamed into place.
_STAGING_PREFIX = ".clone-"


class TemplateFileError(ValueError):
    """A template file operation failed validation (maps to 400)."""


class TemplateConflictError(ValueError):
    """A template name or image name is already taken (maps to 409)."""


def resolve_templates_root(templates_dir: str) -> Optional[str]:
    """Resolve the deployed templates directory, or None when unreachable.

    ``templates_dir`` (CODER_TEMPLATES_DIR, default ``/templates``) works in
    containers with the bind mount; the host-run dev backend falls back to
    ``$SYSTEM_DEPLOYMENT_PATH/coder/templates``.
    """
    candidates = [templates_dir]
    deployment_path = os.environ.get("SYSTEM_DEPLOYMENT_PATH", "")
    if deployment_path:
        candidates.append(os.path.join(deployment_path, "coder", "templates"))
    for candidate in candidates:
        if candidate and os.path.isdir(candidate):
            return candidate
    return None


def discover_templates(root: str) -> Dict[str, Dict[str, Any]]:
    """Template manifests keyed by directory name (same rule as the Temporal
    worker's discovery: a dir is a template iff it has template.json)."""
    templates: Dict[str, Dict[str, Any]] = {}
    for entry in sorted(os.listdir(root)):
        if entry.startswith("."):
            # The staging dir of an in-flight clone, or a stray dot-dir such
            # as Coder's own .coder/ — never a template.
            continue
        manifest_path = os.path.join(root, entry, "template.json")
        if os.path.isfile(manifest_path):
            try:
                with open(manifest_path, encoding="utf-8") as f:
                    manifest = json.load(f)
                manifest["dir_name"] = entry
                templates[entry] = manifest
            except (json.JSONDecodeError, OSError):
                continue
    return templates


def resolve_template_dir(root: str, name: str) -> Optional[Tuple[str, str]]:
    """Match ``name`` against dir name or coder_template_name.

    Returns (dir_name, absolute_path) or None.
    """
    for dir_name, manifest in discover_templates(root).items():
        if name in (dir_name, manifest.get("coder_template_name")):
            return dir_name, os.path.join(root, dir_name)
    return None


def is_customized(template_dir: str) -> bool:
    """Operator-customized = the .computor-managed marker is absent."""
    return not os.path.exists(os.path.join(template_dir, MANAGED_MARKER))


def mark_customized(template_dir: str) -> None:
    """Drop the managed marker so computor.sh stops re-syncing this dir."""
    try:
        os.remove(os.path.join(template_dir, MANAGED_MARKER))
    except FileNotFoundError:
        pass


def restore_managed(template_dir: str) -> None:
    """Re-create the marker; repo defaults re-sync on the next system start."""
    with open(os.path.join(template_dir, MANAGED_MARKER), "w", encoding="utf-8"):
        pass


def _is_template_file(name: str) -> bool:
    if not _FILE_NAME_RE.match(name):
        return False
    return (
        name in ("Dockerfile", "template.json")
        or name.endswith(".tf")
        or name.endswith(".tftpl")
    )


def _safe_file_path(template_dir: str, file_name: str) -> str:
    if not _is_template_file(file_name):
        raise TemplateFileError(
            f"'{file_name}' is not an editable template file "
            "(allowed: *.tf, *.tftpl, template.json, Dockerfile)."
        )
    path = os.path.join(template_dir, file_name)
    # Belt and braces: the name regex already forbids separators.
    if os.path.dirname(os.path.realpath(path)) != os.path.realpath(template_dir):
        raise TemplateFileError(f"Invalid file name '{file_name}'.")
    return path


def list_template_files(template_dir: str) -> List[Dict[str, Any]]:
    """Editable files of a template with their contents."""
    files = []
    for entry in sorted(os.listdir(template_dir)):
        if not _is_template_file(entry):
            continue
        path = os.path.join(template_dir, entry)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8", errors="replace") as f:
            content = f.read(_MAX_FILE_BYTES)
        files.append({"name": entry, "content": content})
    return files


def validate_file_content(file_name: str, content: str) -> None:
    """Syntax-gate a file before writing. Raises TemplateFileError.

    The real correctness gate stays ``coder templates push`` (a server-side
    terraform plan); this only catches outright syntax errors early.
    """
    if len(content.encode("utf-8")) > _MAX_FILE_BYTES:
        raise TemplateFileError("File too large (max 512 KiB).")
    if file_name.endswith(".tf"):
        try:
            hcl2.loads(content)
        except Exception as e:
            raise TemplateFileError(f"Terraform syntax error: {e}") from e
    elif file_name == "template.json":
        try:
            manifest = json.loads(content)
        except json.JSONDecodeError as e:
            raise TemplateFileError(f"Invalid JSON: {e}") from e
        if not isinstance(manifest, dict) or not manifest.get("coder_template_name"):
            raise TemplateFileError(
                "template.json must be an object with a coder_template_name."
            )


def write_template_file(template_dir: str, file_name: str, content: str) -> None:
    """Validate and write one template file, flipping the dir to customized."""
    path = _safe_file_path(template_dir, file_name)
    if not os.path.isfile(path):
        raise TemplateFileError(f"'{file_name}' does not exist in this template.")
    validate_file_content(file_name, content)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    mark_customized(template_dir)


# ---------------------------------------------------------------------------
# Manifest + template lifecycle (clone / metadata / delete)
# ---------------------------------------------------------------------------


def read_manifest(template_dir: str) -> Dict[str, Any]:
    """The template's ``template.json`` as a dict. Raises TemplateFileError."""
    path = os.path.join(template_dir, "template.json")
    try:
        with open(path, encoding="utf-8") as f:
            manifest = json.load(f)
    except FileNotFoundError as e:
        raise TemplateFileError("template.json is missing.") from e
    except json.JSONDecodeError as e:
        raise TemplateFileError(f"template.json is not valid JSON: {e}") from e
    if not isinstance(manifest, dict):
        raise TemplateFileError("template.json must be a JSON object.")
    return manifest


def write_manifest(template_dir: str, manifest: Dict[str, Any]) -> None:
    """Atomically replace ``template.json`` (write a sibling, then rename).

    The marker is left alone — the caller decides whether the write
    customizes the template. The ``dir_name`` key ``discover_templates``
    injects is never persisted.
    """
    payload = {k: v for k, v in manifest.items() if k != "dir_name"}
    path = os.path.join(template_dir, "template.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4)
        f.write("\n")
    os.replace(tmp, path)


def is_clone(manifest: Dict[str, Any]) -> bool:
    """Created through the API (``cloned_from`` set) — never repo-synced."""
    return bool(manifest.get("cloned_from"))


def validate_template_key(key: str) -> None:
    """Gate a new template's key (= its directory name). Raises TemplateFileError."""
    if not key or len(key) > TEMPLATE_KEY_MAX_LEN or not TEMPLATE_KEY_RE.match(key):
        raise TemplateFileError(
            f"Template key must be 1-{TEMPLATE_KEY_MAX_LEN} lowercase letters, "
            "digits or hyphens, starting and ending with a letter or digit."
        )
    if key.endswith(CODER_TEMPLATE_SUFFIX):
        raise TemplateFileError(
            f"Template key must not end in '{CODER_TEMPLATE_SUFFIX}' — that "
            "suffix is added automatically."
        )


def validate_icon(icon: Optional[str]) -> None:
    """Empty is fine; otherwise an absolute http(s) URL or a Coder /icon path."""
    if icon and not _ICON_RE.match(icon):
        raise TemplateFileError(
            "Icon must be an absolute http(s) URL or a Coder built-in "
            "/icon/<name>.svg path."
        )


def derive_template_identity(key: str) -> Dict[str, str]:
    """The dir name, Coder template name and image name a key expands to.

    Same convention as the shipped templates (``vscode`` -> ``vscode-workspace``
    / ``computor-workspace-vscode``), so ``naming.derive_workspace_name`` gives
    a clone's workspaces the key as their default name.
    """
    return {
        "dir_name": key,
        "coder_template_name": f"{key}{CODER_TEMPLATE_SUFFIX}",
        "image_name": f"{IMAGE_NAME_PREFIX}{key}",
    }


def _metadata_fields(
    display_name: str, description: Optional[str], icon: Optional[str]
) -> Dict[str, str]:
    """Cleared values are stored as ``""`` (not dropped) so the push pipeline's
    ``info.get("icon", "")`` clears the field in Coder as well."""
    return {
        "display_name": (display_name or "").strip(),
        "description": (description or "").strip(),
        "icon": (icon or "").strip(),
    }


def update_template_metadata(
    template_dir: str,
    *,
    display_name: str,
    description: Optional[str],
    icon: Optional[str],
) -> Dict[str, Any]:
    """Rewrite the manifest's display metadata, flipping the dir to customized.

    Customizing is a no-op for a clone (it has no marker) and, for a repo
    template, the same detachment from repo syncing any raw file edit causes.
    """
    validate_icon(icon)
    if not (display_name or "").strip():
        raise TemplateFileError("Display name must not be empty.")
    manifest = read_manifest(template_dir)
    manifest.update(_metadata_fields(display_name, description, icon))
    write_manifest(template_dir, manifest)
    mark_customized(template_dir)
    return manifest


def clone_template(
    root: str,
    source_dir_name: str,
    key: str,
    *,
    display_name: str,
    description: Optional[str],
    icon: Optional[str],
) -> Tuple[str, Dict[str, Any]]:
    """Copy a template dir into an independent new one named ``key``.

    The whole tree comes along (Terraform, Dockerfile, payload dirs) except
    the managed marker: a clone has no repo counterpart, so computor.sh never
    visits it, and a marker would only claim otherwise. The manifest is
    rewritten with the derived identity, the given display metadata, and
    ``cloned_from`` / ``created_at`` provenance; ``build_args_env`` and
    ``source_repos`` are inherited.

    Uniqueness is checked over dir names AND Coder names AND image names of
    every template on disk: ``resolve_template_dir`` and the push worker
    match a requested name against either identity, and a shared image name
    would make the clone's build overwrite its source's image.

    Assembly is atomic for every discoverer: files land in a dot-prefixed
    staging dir, the manifest is written last, and the dir is renamed into
    place — neither the catalog nor a concurrent push can see a half copy.

    Raises TemplateFileError (invalid input) or TemplateConflictError (a name
    or image is already taken). Returns ``(dir_name, manifest)``.
    """
    validate_template_key(key)
    validate_icon(icon)
    if not (display_name or "").strip():
        raise TemplateFileError("Display name must not be empty.")
    identity = derive_template_identity(key)

    source_dir = os.path.join(root, source_dir_name)
    source_manifest = read_manifest(source_dir)

    taken_names: set = set()
    taken_images: set = set()
    for dir_name, existing in discover_templates(root).items():
        taken_names.add(dir_name)
        if existing.get("coder_template_name"):
            taken_names.add(existing["coder_template_name"])
        if existing.get("image_name"):
            taken_images.add(existing["image_name"])
    if key in taken_names or identity["coder_template_name"] in taken_names:
        raise TemplateConflictError(
            f"A template named '{key}' ('{identity['coder_template_name']}') "
            "already exists."
        )
    if identity["image_name"] in taken_images:
        raise TemplateConflictError(
            f"Image name '{identity['image_name']}' is already used by another template."
        )
    dest = os.path.join(root, key)
    if os.path.lexists(dest):
        raise TemplateConflictError(
            f"Directory '{key}' already exists in the templates directory."
        )

    manifest = {k: v for k, v in source_manifest.items() if k != "dir_name"}
    manifest["coder_template_name"] = identity["coder_template_name"]
    manifest["image_name"] = identity["image_name"]
    manifest.update(_metadata_fields(display_name, description, icon))
    manifest["cloned_from"] = source_dir_name
    manifest["created_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    staging = os.path.join(root, f"{_STAGING_PREFIX}{key}-{uuid.uuid4().hex[:8]}")
    try:
        shutil.copytree(
            source_dir,
            staging,
            symlinks=True,
            ignore=shutil.ignore_patterns(MANAGED_MARKER, "template.json", "template.json.tmp"),
        )
        write_manifest(staging, manifest)
        os.rename(staging, dest)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    manifest["dir_name"] = key
    return key, manifest


def delete_template_dir(root: str, dir_name: str) -> None:
    """Remove a cloned template directory. Refuses anything not created here.

    ``template.json`` goes first, so the dir stops being a template for every
    discoverer (catalog, push worker) before the rest of the tree is torn
    down.
    """
    path = os.path.join(root, dir_name)
    if not is_clone(read_manifest(path)):
        raise TemplateFileError(
            "Only templates created here can be deleted; repo-shipped templates "
            "are removed from ops/coder/templates."
        )
    os.remove(os.path.join(path, "template.json"))
    shutil.rmtree(path)


# ---------------------------------------------------------------------------
# Declared variables (settings-override pick-list)
# ---------------------------------------------------------------------------


def _unquote(value: Any) -> Any:
    """python-hcl2 keeps the source quotes on strings ('"x"') — strip them."""
    if isinstance(value, str) and len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    return value


def parse_template_variables(template_dir: str) -> List[Dict[str, Any]]:
    """All ``variable`` blocks declared across the template's .tf files.

    Returns entries of shape
    ``{name, type, default, has_default, description, sensitive, file}``;
    the default of a sensitive variable is omitted (masked).
    """
    variables: List[Dict[str, Any]] = []
    for entry in sorted(os.listdir(template_dir)):
        if not entry.endswith(".tf"):
            continue
        path = os.path.join(template_dir, entry)
        try:
            with open(path, encoding="utf-8") as f:
                parsed = hcl2.load(f)
        except Exception:
            # Unparseable file (mid-edit?) — skip; raw editor still works.
            continue
        for block in parsed.get("variable", []):
            for raw_name, body in block.items():
                if not isinstance(body, dict):
                    continue
                sensitive = bool(body.get("sensitive", False))
                has_default = "default" in body
                variables.append({
                    "name": _unquote(raw_name),
                    "type": _unquote(body.get("type")),
                    "default": None if sensitive else _unquote(body.get("default")),
                    "has_default": has_default,
                    "description": _unquote(body.get("description")),
                    "sensitive": sensitive,
                    "file": entry,
                })
    return variables
