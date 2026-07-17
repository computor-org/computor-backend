"""Hierarchical re-arrangement of the student-template archive.

``GET /courses/{id}/template?hierarchical=true`` downloads the student-template
repo re-arranged to mirror the course_content tree: unit titles become parent
directories and the assignment title names the directory holding the
assignment's files (instead of the example identifier). Only files belonging
to a deployed assignment are kept; everything else in the repo is dropped.
"""
import io
import re
import zipfile
from typing import Dict, Iterable, List, Tuple
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from computor_backend.model.course import CourseContent

# Characters invalid in directory names on common filesystems (Windows is the
# strictest: no control chars, / \ : * ? " < > |, no trailing dots/spaces).
_FORBIDDEN_CHARS = re.compile(r'[\x00-\x1f/\\:*?"<>|]')


def _sanitize_segment(title: str | None, fallback: str) -> str:
    name = _FORBIDDEN_CHARS.sub(" ", title or "")
    name = " ".join(name.split())
    name = name.strip(". ")
    return name or fallback


def build_display_names(
    nodes: Iterable[Tuple[str, str | None, float]],
) -> Dict[str, str]:
    """Directory name for every course-content node, keyed by ltree path.

    ``nodes`` is ``(path, title, position)`` per content. Sibling collisions
    (two titles sanitizing to the same name, compared case-insensitively so
    the zip extracts safely on case-insensitive filesystems) get deterministic
    ``(2)``/``(3)`` suffixes in position order.
    """
    by_parent: Dict[str, List[Tuple[str, str | None, float]]] = {}
    for path, title, position in nodes:
        parent = path.rsplit(".", 1)[0] if "." in path else ""
        by_parent.setdefault(parent, []).append((path, title, position))

    display: Dict[str, str] = {}
    for siblings in by_parent.values():
        used: Dict[str, int] = {}
        for path, title, _pos in sorted(siblings, key=lambda n: (n[2], n[0])):
            leaf = path.rsplit(".", 1)[-1]
            name = _sanitize_segment(title, fallback=leaf)
            count = used.get(name.casefold(), 0)
            used[name.casefold()] = count + 1
            if count:
                name = f"{name} ({count + 1})"
            display[path] = name
    return display


def build_hierarchical_mapping(course_id: UUID | str, db: Session) -> Dict[str, List[str]]:
    """Map repo directory → target paths in the hierarchical archive.

    Repo directory is the deployment's directory in the student-template repo
    (``resolve_deployment_directory`` fallback chain); the target path joins
    the display names of the content's ancestors (units) and the assignment
    itself. Assignments without a resolvable repo directory are skipped —
    they have nothing in the template to relocate.
    """
    # Deferred: importing the tasks package registers all Temporal task
    # modules, which the pure helpers above must not depend on.
    from computor_backend.tasks.student_template.selection import (
        resolve_deployment_directory,
    )

    contents = (
        db.query(CourseContent)
        .filter(
            CourseContent.course_id == str(course_id),
            CourseContent.archived_at.is_(None),
        )
        .options(joinedload(CourseContent.deployment))
        .all()
    )
    display = build_display_names(
        (str(c.path), c.title, c.position) for c in contents
    )

    mapping: Dict[str, List[str]] = {}
    for content in contents:
        if not content.is_submittable or content.deployment is None:
            continue
        repo_dir = resolve_deployment_directory(content.deployment, persist=False)
        if not repo_dir:
            continue
        segments = str(content.path).split(".")
        target = "/".join(
            display.get(".".join(segments[: i + 1]), segments[i])
            for i in range(len(segments))
        )
        mapping.setdefault(repo_dir.strip("/"), []).append(target)
    return mapping


def remap_archive_to_hierarchy(zip_bytes: bytes, mapping: Dict[str, List[str]]) -> bytes:
    """Rewrite a git-server archive zip into the course-content hierarchy.

    Strips the provider's top-level wrapper directory (Forgejo ``repo/``,
    GitLab ``repo-branch-sha/``), relocates each mapped assignment directory
    to its target path(s), and drops everything unmapped.
    """
    source = zipfile.ZipFile(io.BytesIO(zip_bytes))
    entries = [info for info in source.infolist() if not info.is_dir()]

    first_components = {info.filename.split("/", 1)[0] for info in entries}
    wrapper = ""
    if len(first_components) == 1 and all("/" in info.filename for info in entries):
        wrapper = next(iter(first_components)) + "/"

    # Most specific repo dir first, in case one mapped dir prefixes another.
    ordered = sorted(mapping.items(), key=lambda kv: len(kv[0]), reverse=True)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as out:
        for info in entries:
            rel = info.filename[len(wrapper):]
            for repo_dir, targets in ordered:
                prefix = repo_dir + "/"
                if not rel.startswith(prefix):
                    continue
                rest = rel[len(prefix):]
                data = source.read(info)
                for target in targets:
                    new_info = zipfile.ZipInfo(f"{target}/{rest}", date_time=info.date_time)
                    new_info.external_attr = info.external_attr
                    out.writestr(new_info, data, compress_type=zipfile.ZIP_DEFLATED)
                break
    buffer.seek(0)
    return buffer.getvalue()
