"""Lena drafts of a unit description (computor-org/issues#559).

The backend builds the whole job input, so the Lena worker needs no course
access of its own: the unit's title and description and, for each assignment
under it, its title, content type and the student-visible assignment text
(``content/index*.md``, filtered like the student description download). No
submissions, messages, grades or names go into a job.
"""

import logging
import re
from typing import Optional

from sqlalchemy.orm import Session

from computor_backend.business_logic.student_description import (
    student_description_filename,
)
from computor_backend.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from computor_backend.model.course import Course, CourseContent, CourseContentKind
from computor_backend.permissions.core import check_course_permissions
from computor_backend.permissions.principal import Principal
from computor_backend.repositories.example_version_repo import ExampleVersionRepository
from computor_types.course_content_description_drafts import (
    DESCRIPTION_DRAFT_MAX_LANGUAGES,
    DescriptionDraftAssignment,
    DescriptionDraftInput,
    DescriptionDraftRequest,
)

logger = logging.getLogger(__name__)

# Bounds on what one job sends to the model.
MAX_ASSIGNMENTS = 60
MAX_TEXT_PER_ASSIGNMENT = 8000
MAX_TEXT_TOTAL = 40000
SHORTENED = "\n\n[shortened]"
FALLBACK_LANGUAGE = "en"

_DESCRIPTION_FILE = re.compile(
    r"(?:index|readme)(?:_(?P<lang>[a-z]{2})(?:[-_][a-z0-9]{2,8})?)?\.md", re.IGNORECASE
)


def get_unit_for_draft(content_id: str, permissions: Principal, db: Session) -> CourseContent:
    """The unit a lecturer may ask a draft for, or raise."""
    content = db.query(CourseContent).filter(CourseContent.id == str(content_id)).first()
    if content is None or content.archived_at is not None:
        raise NotFoundException(
            error_code="CONTENT_001",
            detail="Course content not found",
            context={"course_content_id": str(content_id)},
        )
    if check_course_permissions(permissions, Course, "_lecturer", db).filter(
        Course.id == content.course_id
    ).first() is None:
        raise ForbiddenException(
            detail="Only lecturers of this course can ask Lena for a description draft",
            context={"course_content_id": str(content_id)},
        )
    kind = db.query(CourseContentKind).filter(
        CourseContentKind.id == content.course_content_kind_id
    ).first()
    if content.is_submittable or kind is None or not kind.has_descendants:
        raise BadRequestException(
            detail="Description drafts are written for units, not for assignments",
            context={"course_content_id": str(content_id)},
        )
    return content


def _assignments_under(unit: CourseContent, db: Session) -> list[CourseContent]:
    """Assignments below the unit, in the order the course tree shows them."""
    descendants = (
        db.query(CourseContent)
        .filter(
            CourseContent.course_id == unit.course_id,
            CourseContent.path.descendant_of(unit.path),
            CourseContent.id != unit.id,
            CourseContent.archived_at.is_(None),
        )
        .all()
    )
    # Siblings are ordered by position, not by path; nested contents follow
    # the positions of every node above them.
    positions = {str(content.path): content.position for content in descendants}

    def tree_order(content: CourseContent) -> tuple:
        labels = str(content.path).split(".")
        return tuple(
            (positions.get(".".join(labels[:depth]), 0.0), labels[depth - 1])
            for depth in range(len(str(unit.path).split(".")) + 1, len(labels) + 1)
        )

    return sorted(
        (content for content in descendants if content.is_submittable),
        key=tree_order,
    )


def _description_language(filename: str) -> Optional[str]:
    match = _DESCRIPTION_FILE.fullmatch(filename)
    if match is None:
        return None
    return (match.group("lang") or "").lower()


async def _assignment_texts(content: CourseContent, db: Session, storage_service) -> dict[str, str]:
    """Student-visible description texts of the assigned example, by language.

    The key is the two-letter code of ``index_<lang>.md`` and "" for a plain
    ``index.md``. The assigned version is used even before it is released:
    the lecturer is describing what the unit will contain. Anything that
    cannot be read yields no text rather than failing the draft.
    """
    deployment = content.deployment
    if (
        deployment is None
        or deployment.deployment_status == "unassigned"
        or not deployment.example_version_id
    ):
        return {}
    version = ExampleVersionRepository(db).get_with_relationships(str(deployment.example_version_id))
    if version is None or version.example is None or version.example.repository is None:
        return {}
    repository = version.example.repository
    if (
        repository.source_type not in {"minio", "s3"}
        or not version.storage_path
        or not repository.source_url
    ):
        return {}
    bucket = repository.source_url.split("/")[0]
    texts: dict[str, str] = {}
    try:
        objects = await storage_service.list_objects(
            bucket_name=bucket, prefix=version.storage_path.rstrip("/") + "/content/"
        )
        # index*.md before readme*.md when an example has both.
        objects = sorted(
            objects,
            key=lambda obj: (
                not obj.object_name.rsplit("/", 1)[-1].lower().startswith("index"),
                obj.object_name,
            ),
        )
        for obj in objects:
            filename = student_description_filename(version.storage_path, obj.object_name)
            # Top-level description files only; assets are no use to the model.
            if filename is None or "/" in filename:
                continue
            language = _description_language(filename)
            if language is None or language in texts:
                continue
            data = await storage_service.download_file(bucket_name=bucket, object_key=obj.object_name)
            texts[language] = data.decode("utf-8", errors="replace")
    except Exception as e:
        # Lena then writes from titles alone; say why in the log.
        logger.warning(
            "Description draft: assignment texts of %s unreadable (%s)",
            content.id, type(e).__name__,
        )
        return texts
    return texts


def _draft_languages(
    request: DescriptionDraftRequest, texts: list[dict[str, str]], course: Course
) -> list[str]:
    if request.languages:
        return request.languages
    found = sorted({language for by_language in texts for language in by_language if language})
    if len(found) > DESCRIPTION_DRAFT_MAX_LANGUAGES:
        # A job answers in at most this many languages; keep the course's own.
        found = sorted(found, key=lambda code: code != course.language_code)
        found = found[:DESCRIPTION_DRAFT_MAX_LANGUAGES]
    if found:
        return found
    return [course.language_code or FALLBACK_LANGUAGE]


def _pick_text(by_language: dict[str, str], languages: list[str]) -> tuple[str, Optional[str]]:
    """One text per assignment: the first draft language, else index.md, else any."""
    for language in languages:
        if language in by_language:
            return by_language[language], language
    if "" in by_language:
        return by_language[""], None
    for language in sorted(by_language):
        return by_language[language], language
    return "", None


def _shorten(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - len(SHORTENED))].rstrip() + SHORTENED


async def build_draft_input(
    unit: CourseContent,
    request: DescriptionDraftRequest,
    db: Session,
    storage_service,
) -> DescriptionDraftInput:
    assignments = _assignments_under(unit, db)[:MAX_ASSIGNMENTS]
    if not assignments:
        raise BadRequestException(
            detail="This unit has no assignments to describe",
            context={"course_content_id": str(unit.id)},
        )
    texts = [await _assignment_texts(content, db, storage_service) for content in assignments]
    course = unit.course
    languages = _draft_languages(request, texts, course)
    per_assignment = min(MAX_TEXT_PER_ASSIGNMENT, MAX_TEXT_TOTAL // len(assignments))

    items = []
    for content, by_language in zip(assignments, texts):
        text, text_language = _pick_text(by_language, languages)
        if not text:
            # No readable assignment text: the lecturer's own description of
            # the assignment is better than a bare title.
            text = content.description or ""
        content_type = content.course_content_type
        items.append(
            DescriptionDraftAssignment(
                title=content.title or str(content.path),
                content_type=content_type.title if content_type is not None else None,
                text=_shorten(text, per_assignment),
                text_language=text_language,
            )
        )

    return DescriptionDraftInput(
        unit_title=unit.title or str(unit.path),
        unit_description=unit.description or None,
        course_title=course.title if course is not None else None,
        languages=languages,
        instruction=request.instruction,
        assignments=items,
    )
