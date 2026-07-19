"""Filesystem access to the deployed Coder template directories.

Backs the raw + guided template editing endpoints in ``api/coder.py``. All
reads/writes target the DEPLOYED templates dir (``${SYSTEM_DEPLOYMENT_PATH}/
coder/templates``, mounted at ``CODER_TEMPLATES_DIR`` in containers) — the
same files ``coder templates push`` consumes — never the repo copy under
``ops/coder/templates``.

Customization contract (see computor.sh): a deployed template dir carrying a
``.computor-managed`` marker is re-synced from the repo on every startup.
Any edit through this module therefore REMOVES the marker, flipping the
template to operator-customized so startup stops clobbering it;
``restore_managed`` re-creates the marker, and the repo defaults return on
the next system restart.

Guided editing is deliberately NOT a general HCL rewriter: it only replaces
(or inserts) the single-line ``default = …`` inside a ``variable "name"``
block, then re-parses the whole file with hcl2 and refuses to write anything
that no longer parses. Multi-line defaults are rejected — that's what the
raw editor is for.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import hcl2

MANAGED_MARKER = ".computor-managed"

# Whitelist for raw editing: the template contract files only, no paths.
_FILE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

_MAX_FILE_BYTES = 512 * 1024


class TemplateFileError(ValueError):
    """A template file operation failed validation (maps to 400)."""


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
# Guided variable editing
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


def _serialize_default(name: str, var_type: Optional[str], value: Any) -> str:
    """Render a new default as HCL source, coerced to the declared type."""
    if var_type == "bool" or isinstance(value, bool):
        if isinstance(value, str):
            if value.lower() in ("true", "false"):
                return value.lower()
            raise TemplateFileError(f"Variable '{name}' expects true or false.")
        return "true" if value else "false"
    if var_type == "number":
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return json.dumps(value)
        try:
            text = str(value).strip()
            return json.dumps(float(text) if "." in text else int(text))
        except (TypeError, ValueError) as e:
            raise TemplateFileError(f"Variable '{name}' expects a number.") from e
    # Strings (and untyped): JSON escaping is valid HCL string syntax.
    return json.dumps(str(value))


def _variable_block_span(text: str, name: str) -> Tuple[int, int]:
    """(start, end) offsets of the ``variable "name" { … }`` block body."""
    match = re.search(r'variable\s+"' + re.escape(name) + r'"\s*\{', text)
    if not match:
        raise TemplateFileError(f"Variable '{name}' not found.")
    depth = 0
    for i in range(match.end() - 1, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return match.end(), i
    raise TemplateFileError(f"Unbalanced braces in variable '{name}' block.")


def _rewrite_default(text: str, name: str, serialized: str) -> str:
    """Replace (or insert) the single-line default inside one variable block."""
    body_start, body_end = _variable_block_span(text, name)
    body = text[body_start:body_end]
    match = re.search(r"^([ \t]*default\s*=\s*)(.*)$", body, flags=re.MULTILINE)
    if match:
        old_value = match.group(2).strip()
        if old_value.startswith(("[", "{")) or old_value.endswith(("[", "{", "(")):
            raise TemplateFileError(
                f"Variable '{name}' has a multi-line default — "
                "edit it in the raw file editor."
            )
        new_body = body[:match.start()] + match.group(1) + serialized + body[match.end():]
    else:
        new_body = f"\n  default     = {serialized}" + body
    return text[:body_start] + new_body + text[body_end:]


def update_variable_defaults(template_dir: str, updates: Dict[str, Any]) -> None:
    """Apply new defaults for the given variables, validating each touched
    file re-parses before anything is written. Flips the dir to customized."""
    declared = {v["name"]: v for v in parse_template_variables(template_dir)}
    by_file: Dict[str, Dict[str, Any]] = {}
    for name, value in updates.items():
        info = declared.get(name)
        if info is None:
            raise TemplateFileError(f"Variable '{name}' is not declared in this template.")
        by_file.setdefault(info["file"], {})[name] = value

    # Rewrite + validate everything in memory first, then write all files.
    pending: List[Tuple[str, str]] = []
    for file_name, file_updates in by_file.items():
        path = os.path.join(template_dir, file_name)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for name, value in file_updates.items():
            serialized = _serialize_default(name, declared[name].get("type"), value)
            text = _rewrite_default(text, name, serialized)
        try:
            hcl2.loads(text)
        except Exception as e:
            raise TemplateFileError(
                f"Edit to {file_name} would produce invalid Terraform: {e}"
            ) from e
        pending.append((path, text))

    for path, text in pending:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    mark_customized(template_dir)
