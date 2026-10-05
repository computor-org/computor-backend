"""Anonymous learner-facing projection of public courses.

Issue #435: expose the pedagogical course tree and only description assets a
student is meant to read. Never expose repository layout, reference solutions,
hidden tests, submissions, or git credentials.

The functions here are provider/storage agnostic. They resolve database rows to
small immutable source records; the API performs asynchronous storage reads
after the SQLAlchemy session is closed.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import re
from typing import Iterable, Optional
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from computor_backend.business_logic.content_visibility import (
    ancestor_paths,
    student_visible_predicate,
)
from computor_backend.exceptions import NotFoundException
from computor_backend.model.course import Course, CourseContent
from computor_backend.model.deployment import CourseContentDeployment
from computor_backend.model.example import Example, ExampleVersion
from computor_backend.model.organization import Organization
from computor_types.custom_types import Ltree
from computor_types.public_learning import (
    PublicLearningContentSummary,
    PublicLearningCourseOutline,
)


_DESCRIPTION_RE = re.compile(
    r"^(?:index|README)(?:_([A-Za-z0-9-]+))?\.md$", re.IGNORECASE
)
_WELCOME_LEAVES = {
    "welcome",
    "start",
    "start_here",
    "getting_started",
    "introduction",
    "intro",
    "einfuehrung",
    "einfuhrung",
}


@dataclass(frozen=True)
class PublicContentSource:
    """Safe metadata needed to serve one learner-visible content item."""

    id: str
    course_id: str
    title: str
    description: Optional[str]
    path: str
    kind: str
    is_submittable: bool
    course_language: Optional[str]
    bucket_name: Optional[str]
    storage_path: Optional[str]


@dataclass(frozen=True)
class PublicAssetSource:
    """Storage location of one public description asset."""

    bucket_name: str
    object_key: str


def _public_course(db: Session, course_id: UUID | str) -> Course:
    """Return one anonymously readable course or opaque-404 it."""
    course = (
        db.query(Course)
        .join(Organization, Organization.id == Course.organization_id)
        .filter(
            Course.id == str(course_id),
            Course.public.is_(True),
            Course.archived_at.is_(None),
            Course.visible.isnot(False),
            Organization.archived_at.is_(None),
        )
        .first()
    )
    if course is None:
        raise NotFoundException(detail="Public course not found")
    return course


def _has_archived_ancestor(db: Session, content: CourseContent) -> bool:
    """Archived content hides its subtree from the anonymous reader."""
    paths = [Ltree(p) for p in ancestor_paths(str(content.path))]
    return (
        db.query(CourseContent.id)
        .filter(
            CourseContent.course_id == content.course_id,
            CourseContent.path.in_(paths),
            CourseContent.archived_at.isnot(None),
        )
        .first()
        is not None
    )


def _parent_path(path: str) -> Optional[str]:
    parent, separator, _ = path.rpartition(".")
    return parent if separator else None


def _ordered_contents(rows: Iterable[CourseContent]) -> list[CourseContent]:
    """Depth-first pedagogical order: sibling position then title/path."""
    rows = list(rows)
    by_parent: dict[Optional[str], list[CourseContent]] = defaultdict(list)
    paths = {str(row.path) for row in rows}
    for row in rows:
        path = str(row.path)
        parent = _parent_path(path)
        by_parent[parent if parent in paths else None].append(row)

    for siblings in by_parent.values():
        siblings.sort(
            key=lambda row: (
                float(row.position),
                (row.title or "").casefold(),
                str(row.path),
            )
        )

    ordered: list[CourseContent] = []

    def visit(parent: Optional[str]) -> None:
        for row in by_parent.get(parent, []):
            ordered.append(row)
            visit(str(row.path))

    visit(None)
    return ordered


def _is_welcome(row: CourseContent) -> bool:
    props = row.properties if isinstance(row.properties, dict) else {}
    if props.get("public_start") is True or props.get("welcome") is True:
        return True
    leaf = str(row.path).split(".")[-1].casefold()
    return leaf in _WELCOME_LEAVES


def load_public_course_outline(
    db: Session, course_id: UUID | str
) -> PublicLearningCourseOutline:
    """Anonymous course outline with only visible/released learner content."""
    course = _public_course(db, course_id)
    rows = (
        db.query(CourseContent)
        .options(joinedload(CourseContent.course_content_type))
        .filter(
            CourseContent.course_id == course.id,
            CourseContent.archived_at.is_(None),
            student_visible_predicate(),
        )
        .all()
    )
    rows = [row for row in rows if not _has_archived_ancestor(db, row)]
    ordered = _ordered_contents(rows)

    items = [
        PublicLearningContentSummary(
            id=str(row.id),
            title=row.title or str(row.path).split(".")[-1].replace("_", " ").title(),
            description=row.description,
            path=str(row.path),
            parent_path=_parent_path(str(row.path)),
            depth=max(0, len(str(row.path).split(".")) - 1),
            position=float(row.position),
            kind=row.course_content_kind_id,
            type_title=(
                row.course_content_type.title
                if row.course_content_type is not None
                else None
            ),
            color=(
                row.course_content_type.color
                if row.course_content_type is not None
                else None
            ),
            is_submittable=bool(row.is_submittable),
        )
        for row in ordered
    ]

    welcome = next((row for row in ordered if _is_welcome(row)), None)
    first_exercise = next((row for row in ordered if row.is_submittable), None)
    return PublicLearningCourseOutline(
        id=str(course.id),
        title=course.title or "Course",
        description=course.description,
        language_code=course.language_code,
        contents=items,
        welcome_content_id=str(welcome.id) if welcome is not None else None,
        first_exercise_id=(
            str(first_exercise.id) if first_exercise is not None else None
        ),
        exercise_count=sum(1 for row in ordered if row.is_submittable),
        unit_count=sum(1 for row in ordered if not row.is_submittable),
    )


def resolve_public_content_source(
    db: Session, content_id: UUID | str
) -> PublicContentSource:
    """Resolve one public item and, for assignments, its description storage."""
    row = (
        db.query(CourseContent)
        .options(
            joinedload(CourseContent.deployment)
            .joinedload(CourseContentDeployment.example_version)
            .joinedload(ExampleVersion.example)
            .joinedload(Example.repository),
            joinedload(CourseContent.course),
        )
        .join(Course, Course.id == CourseContent.course_id)
        .join(Organization, Organization.id == Course.organization_id)
        .filter(
            CourseContent.id == str(content_id),
            Course.public.is_(True),
            Course.archived_at.is_(None),
            Course.visible.isnot(False),
            Organization.archived_at.is_(None),
            CourseContent.archived_at.is_(None),
            student_visible_predicate(),
        )
        .first()
    )
    if row is None or _has_archived_ancestor(db, row):
        raise NotFoundException(detail="Public course content not found")

    bucket_name: Optional[str] = None
    storage_path: Optional[str] = None
    deployment = row.deployment
    version = deployment.example_version if deployment is not None else None
    if version is not None and version.example is not None:
        repository = version.example.repository
        if repository is not None and repository.source_url:
            bucket_name = repository.source_url.split("/")[0]
            storage_path = version.storage_path

    fallback = row.description
    if not fallback and version is not None:
        fallback = version.description

    return PublicContentSource(
        id=str(row.id),
        course_id=str(row.course_id),
        title=row.title or str(row.path).split(".")[-1].replace("_", " ").title(),
        description=fallback,
        path=str(row.path),
        kind=row.course_content_kind_id,
        is_submittable=bool(row.is_submittable),
        course_language=(
            row.course.language_code if row.course is not None else None
        ),
        bucket_name=bucket_name,
        storage_path=storage_path,
    )


def description_files(
    object_names: Iterable[str], storage_path: str
) -> dict[Optional[str], str]:
    """Map language to object key for public description Markdown files."""
    prefix = f"{storage_path.rstrip('/')}/content/"
    found: dict[Optional[str], str] = {}
    for object_name in object_names:
        if not object_name.startswith(prefix):
            continue
        relative = object_name[len(prefix):]
        if "/" in relative:
            continue
        match = _DESCRIPTION_RE.fullmatch(relative)
        if not match:
            continue
        language = match.group(1)
        language = language.casefold() if language else None
        current = found.get(language)
        if current is None or relative.casefold().startswith("index"):
            found[language] = object_name
    return found


def select_description_file(
    files: dict[Optional[str], str],
    requested_language: Optional[str],
    course_language: Optional[str],
) -> tuple[Optional[str], Optional[str]]:
    """Choose description language with deterministic fallbacks."""
    if not files:
        return None, None
    candidates = [
        requested_language.casefold() if requested_language else None,
        course_language.casefold() if course_language else None,
        "en",
        "de",
        None,
    ]
    seen: set[Optional[str]] = set()
    for language in candidates:
        if language in seen:
            continue
        seen.add(language)
        if language in files:
            return language, files[language]
    language = sorted(
        files,
        key=lambda value: (value is None, value or ""),
    )[0]
    return language, files[language]


def available_description_languages(
    files: dict[Optional[str], str]
) -> list[str]:
    return sorted(language for language in files if language is not None)


def validate_public_asset_path(asset_path: str) -> str:
    """Allow only learner-visible content/mediaFiles assets."""
    normalized = asset_path.replace("\\", "/").lstrip("/")
    parts = [part for part in normalized.split("/") if part]
    if (
        len(parts) < 2
        or parts[0] != "mediaFiles"
        or any(part in {".", ".."} for part in parts)
    ):
        raise NotFoundException(detail="Public asset not found")
    return "/".join(parts)


def resolve_public_asset_source(
    db: Session, content_id: UUID | str, asset_path: str
) -> PublicAssetSource:
    source = resolve_public_content_source(db, content_id)
    if not source.bucket_name or not source.storage_path:
        raise NotFoundException(detail="Public asset not found")
    safe_path = validate_public_asset_path(asset_path)
    return PublicAssetSource(
        bucket_name=source.bucket_name,
        object_key=f"{source.storage_path.rstrip('/')}/content/{safe_path}",
    )
