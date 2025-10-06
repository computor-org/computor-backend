"""Generate a Computor deployment config from legacy CSV exports.

This script reads the legacy organization/course CSV exports located in
``exports/`` and materialises a ``ComputorDeploymentConfig`` instance that
matches the refactored deployment schema in
``ctutor_backend.interface.deployments_refactored``.

Usage:

    python scripts/generate_deployment_from_exports.py \
        --exports-dir exports \
        --output deployment.generated.yaml

If ``--output`` is omitted the YAML will be printed to stdout.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if SRC_ROOT.exists():
    sys.path.insert(0, str(SRC_ROOT))

from ctutor_backend.interface.deployments_refactored import (
    ComputorDeploymentConfig,
    CourseContentConfig,
    CourseContentTypeConfig,
    GitLabConfig,
    HierarchicalCourseConfig,
    HierarchicalCourseFamilyConfig,
    HierarchicalOrganizationConfig,
)


EXPORT_PREFIXES = {
    "organizations": "organization",
    "course_families": "course_family",
    "courses": "course",
    "content_types": "course_content_type",
    "content_kinds": "course_content_kind",
    "contents": "course_content",
}


# Overrides for legacy naming patterns when constructing example identifiers.
COURSE_FAMILY_EXAMPLE_PREFIX = {
    "progphys": "pgph",
}

COURSE_EXAMPLE_PREFIX = {
    "2025.matlab": "mat",
    "matlab.2025": "mat",
    "2025.python": "py",
    "python.2025": "py",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--exports-dir",
        type=Path,
        default=Path("exports"),
        help="Directory containing the legacy CSV exports",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to write the resulting YAML (stdout when omitted)",
    )
    return parser.parse_args()


def _find_latest_csv(directory: Path, prefix: str) -> Path:
    pattern = f"{prefix}_*_export.csv"
    candidates = [
        path
        for path in directory.glob(pattern)
        if _is_timestamped_export(path.name, prefix)
    ]
    candidates.sort()
    if not candidates:
        raise FileNotFoundError(f"No CSV found for prefix '{prefix}' in {directory}")
    return candidates[-1]


def _is_timestamped_export(filename: str, prefix: str) -> bool:
    suffix = "_export.csv"
    if not filename.startswith(f"{prefix}_") or not filename.endswith(suffix):
        return False
    timestamp = filename[len(prefix) + 1 : -len(suffix)]
    return timestamp.isdigit()


def _load_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        rows: List[Dict[str, Any]] = []
        for raw_row in reader:
            row = {key: (value.strip() if value is not None else None) for key, value in raw_row.items()}
            rows.append(row)
        return rows


def _parse_json(value: Optional[str]) -> Dict[str, Any]:
    if not value:
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive path
        raise ValueError(f"Failed to decode JSON: {value}") from exc


def _parse_bool(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.lower() in {"1", "true", "t", "yes"}


def _safe_int(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def _safe_float(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _normalize_path_segment(segment: str) -> str:
    if not segment:
        return ""
    segment = re.sub(r"^\d+_", "", segment)
    segment = re.sub(r"[\s\-]+", "_", segment)
    segment = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", segment)
    segment = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", segment)
    segment = re.sub(r"_+", "_", segment)
    return segment.strip("_").lower()


def _slug_from_directory(directory: Optional[str]) -> Optional[str]:
    if not directory:
        return None
    segments = [seg for seg in directory.split("/") if seg]
    if not segments:
        return None
    last_segment = re.sub(r"^\d+_", "", segments[-1])
    slug = _normalize_path_segment(last_segment)
    return slug or None


def _canonical_course_path(path: str) -> str:
    return path


def _example_prefix_for_family(family_path: str) -> str:
    return COURSE_FAMILY_EXAMPLE_PREFIX.get(family_path, family_path)


def _example_prefix_for_course(course_path: str) -> str:
    canonical = _canonical_course_path(course_path)
    if canonical in COURSE_EXAMPLE_PREFIX:
        return COURSE_EXAMPLE_PREFIX[canonical]
    first_segment = canonical.split(".")[0]
    return first_segment[:3] if len(first_segment) > 3 else first_segment


def _build_gitlab_config(properties: Dict[str, Any]) -> Optional[GitLabConfig]:
    gitlab_raw = properties.get("gitlab")
    if not isinstance(gitlab_raw, dict):
        return None
    allowed_fields = GitLabConfig.model_fields.keys()
    filtered = {key: value for key, value in gitlab_raw.items() if key in allowed_fields}
    filtered.pop("full_path", None)
    return GitLabConfig(**filtered) if filtered else None


def _strip_gitlab(properties: Dict[str, Any]) -> Dict[str, Any]:
    if "gitlab" not in properties:
        return properties
    remainder = dict(properties)
    remainder.pop("gitlab", None)
    return remainder


def load_exports(exports_dir: Path) -> Dict[str, List[Dict[str, Any]]]:
    data: Dict[str, List[Dict[str, Any]]] = {}
    for key, prefix in EXPORT_PREFIXES.items():
        csv_path = _find_latest_csv(exports_dir, prefix)
        data[key] = _load_csv(csv_path)
    return data


def build_deployment(data: Dict[str, List[Dict[str, Any]]]) -> ComputorDeploymentConfig:
    org_rows = data["organizations"]
    family_rows = data["course_families"]
    course_rows = data["courses"]
    type_rows = data["content_types"]
    kind_rows = data["content_kinds"]
    content_rows = data["contents"]

    families_by_org: Dict[str, List[Dict[str, Any]]] = {}
    for row in family_rows:
        org_id = row.get("organization_id")
        if not org_id:
            continue
        families_by_org.setdefault(org_id, []).append(row)

    courses_by_family: Dict[str, List[Dict[str, Any]]] = {}
    for row in course_rows:
        family_id = row.get("course_family_id")
        if not family_id:
            continue
        courses_by_family.setdefault(family_id, []).append(row)

    content_types_by_course: Dict[str, List[Dict[str, Any]]] = {}
    content_types_by_id: Dict[str, Dict[str, Any]] = {}
    for row in type_rows:
        course_id = row.get("course_id")
        row_id = row.get("id")
        if not course_id or not row_id:
            continue
        content_types_by_course.setdefault(course_id, []).append(row)
        content_types_by_id[row_id] = row

    kind_meta = {row["id"]: row for row in kind_rows}

    contents_by_course: Dict[str, List[Dict[str, Any]]] = {}
    for row in content_rows:
        course_id = row.get("course_id")
        if not course_id:
            continue
        contents_by_course.setdefault(course_id, []).append(row)

    organizations: List[HierarchicalOrganizationConfig] = []

    for org_row in org_rows:
        org_properties = _parse_json(org_row.get("properties"))
        gitlab_cfg = _build_gitlab_config(org_properties)
        settings = _strip_gitlab(org_properties)

        course_families: List[HierarchicalCourseFamilyConfig] = []
        for family_row in families_by_org.get(org_row["id"], []):
            _ = _parse_json(family_row.get("properties"))  # legacy data unused
            family_settings = None

            courses: List[HierarchicalCourseConfig] = []
            for course_row in courses_by_family.get(family_row["id"], []):
                _ = _parse_json(course_row.get("properties"))  # legacy data unused
                course_settings = None

                course_path = course_row["path"] or ""
                canonical_path = _canonical_course_path(course_path)

                content_types_cfg = [
                    CourseContentTypeConfig(
                        slug=ctype_row["slug"],
                        title=ctype_row.get("title") or None,
                        description=ctype_row.get("description") or None,
                        color=ctype_row.get("color") or None,
                        kind=ctype_row.get("course_content_kind_id"),
                        properties=_strip_gitlab(_parse_json(ctype_row.get("properties"))) or None,
                    )
                    for ctype_row in content_types_by_course.get(course_row["id"], [])
                ]

                content_nodes = _build_course_contents(
                    contents_by_course.get(course_row["id"], []),
                    content_types_by_id,
                    kind_meta,
                    org_row.get("path") or "",
                    family_row.get("path") or "",
                    canonical_path,
                )

                course_cfg = HierarchicalCourseConfig(
                    name=course_row.get("title") or canonical_path,
                    path=canonical_path,
                    description=course_row.get("description") or None,
                    content_types=content_types_cfg or None,
                    contents=content_nodes,
                    settings=course_settings or None,
                )

                courses.append(course_cfg)

            family_cfg = HierarchicalCourseFamilyConfig(
                name=family_row.get("title") or family_row.get("path") or "Unnamed Family",
                path=family_row.get("path") or "",
                description=family_row.get("description") or None,
                settings=family_settings or None,
                courses=courses,
            )

            course_families.append(family_cfg)

        org_cfg = HierarchicalOrganizationConfig(
            name=org_row.get("title") or org_row.get("path") or "Unnamed Organization",
            path=org_row.get("path") or "",
            description=org_row.get("description") or None,
            settings=settings or None,
            course_families=course_families,
        )

        if gitlab_cfg is not None:
            org_cfg.gitlab = gitlab_cfg

        organizations.append(org_cfg)

    return ComputorDeploymentConfig(organizations=organizations)


def _build_course_contents(
    content_rows: List[Dict[str, Any]],
    content_types_by_id: Dict[str, Dict[str, Any]],
    kind_meta: Dict[str, Dict[str, Any]],
    org_path: str,
    family_path: str,
    course_path: str,
) -> List[CourseContentConfig]:
    if not content_rows:
        return []

    example_family = _example_prefix_for_family(family_path)
    example_course = _example_prefix_for_course(course_path)

    nodes: Dict[str, Dict[str, Any]] = {}

    sorted_rows = sorted(content_rows, key=lambda row: (_safe_float(row.get("position")) or 0.0, row.get("path") or ""))

    for row in sorted_rows:
        full_path = row.get("path") or ""
        ctype_id = row.get("course_content_type_id")
        type_row = content_types_by_id.get(ctype_id or "")
        if type_row is None:
            continue
        kind_row = kind_meta.get(type_row.get("course_content_kind_id")) or {}
        is_submittable = _parse_bool(kind_row.get("submittable"))

        directory = None
        properties_raw = _parse_json(row.get("properties"))
        gitlab_meta = properties_raw.get("gitlab") if isinstance(properties_raw, dict) else None
        if isinstance(gitlab_meta, dict):
            directory = gitlab_meta.get("directory")

        path_slug = _slug_from_directory(directory)
        if not path_slug and full_path:
            path_slug = _normalize_path_segment(full_path.split(".")[-1])

        node_data: Dict[str, Any] = {
            "path": path_slug,
            "content_type": type_row.get("slug"),
            "position": _safe_float(row.get("position")),
            "max_group_size": _safe_int(row.get("max_group_size")),
            "max_test_runs": _safe_int(row.get("max_test_runs")),
            "max_submissions": _safe_int(row.get("max_submissions")),
            "contents": [],
        }

        if is_submittable and path_slug:
            node_data["example_identifier"] = f"{org_path}.{example_family}.{example_course}.{path_slug}"


        nodes[full_path] = node_data

    roots: List[Dict[str, Any]] = []

    for full_path, node in nodes.items():
        parent_path = full_path.rsplit(".", 1)[0] if "." in full_path else None
        if parent_path and parent_path in nodes:
            nodes[parent_path]["contents"].append(node)
        else:
            roots.append(node)

    def _sort_key(node: Dict[str, Any]) -> tuple[float, str]:
        return (node.get("position") or 0.0, node.get("path") or "")

    def _convert(node_dict: Dict[str, Any]) -> CourseContentConfig:
        children = [_convert(child) for child in sorted(node_dict["contents"], key=lambda n: (n.get("position") or 0.0, n.get("path") or ""))]
        data = dict(node_dict)
        data["contents"] = children or None
        return CourseContentConfig(**{k: v for k, v in data.items() if v is not None})

    ordered_roots = sorted(roots, key=_sort_key)
    return [_convert(node) for node in ordered_roots]


def main() -> None:
    args = parse_args()
    exports_dir: Path = args.exports_dir
    data = load_exports(exports_dir)
    deployment = build_deployment(data)
    yaml_output = deployment.get_deployment()
    if args.output:
        args.output.write_text(yaml_output)
    else:
        print(yaml_output)


if __name__ == "__main__":
    main()
