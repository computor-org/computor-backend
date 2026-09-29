"""Public course catalog and student self-registration (issue #213).

Two operations, one security boundary. A course carries ``Course.public``;
when it is true the course is listed to every signed-in user and any of them
may create their *own* membership in it.

The boundary is that self-registration takes no role and no group from the
request. ``_student`` is written as a literal below and there is no code path
here that can produce anything else, so no amount of request shaping turns
this into privilege escalation. Everything past the membership row — student
profile, submission groups, repository provisioning — reuses the same
``course_member_post_create`` hook the lecturer-driven paths run, so a
self-registered student is indistinguishable from an imported one apart from
``properties["self_registered"]``.

Denials are 404, not 403: a course you may not join must not be
distinguishable from a course that does not exist. See exceptions/__init__.py
on ``PermissionDeniedAsNotFound``.
"""

import logging
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import exc, func
from sqlalchemy.orm import Session

from computor_backend.exceptions import (
    ConflictException,
    ForbiddenException,
    PermissionDeniedAsNotFound,
)
from computor_backend.model.course import Course, CourseGroup, CourseMember
from computor_backend.model.organization import Organization
from computor_backend.permissions.principal import Principal
from computor_types.courses import (
    CoursePublicCatalogEntry,
    CoursePublicList,
    CoursePublicQuery,
)

logger = logging.getLogger(__name__)

# Title of the group created when a public course has none at all. A student
# CourseMember must carry a course_group_id (CHECK constraint on
# course_member), so self-registration cannot proceed without one.
SELF_REGISTRATION_GROUP_TITLE = "default"


def _catalog_query(db: Session):
    """Courses that are open for self-registration, joined to their org.

    Neither an archived course nor a course under an archived organization
    may stay joinable, so the predicate lives here and both the catalog and
    the registration lookup use it.
    """
    return (
        db.query(Course, Organization.title)
        .join(Organization, Organization.id == Course.organization_id)
        .filter(
            Course.public.is_(True),
            Course.archived_at.is_(None),
            Organization.archived_at.is_(None),
        )
    )


def list_public_courses(
    params: Optional[CoursePublicQuery],
    permissions: Principal,
    db: Session,
) -> Tuple[list[CoursePublicList], int]:
    """One page of the public catalog, plus the unpaginated total."""
    query = _catalog_query(db)

    skip, limit = 0, 100
    if params is not None:
        if params.title is not None:
            query = query.filter(Course.title.ilike(f"%{params.title}%"))
        if params.language_code is not None:
            query = query.filter(Course.language_code == params.language_code)
        skip = params.skip or 0
        limit = params.limit or 100

    total = query.count()
    rows = (
        query.order_by(Course.title.asc(), Course.id.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    # Resolve "am I already in this course" for the page in one query rather
    # than per row, and without consulting the principal's cached claims
    # (those lag a fresh registration by up to AUTH_CACHE_TTL).
    page_ids = [str(course.id) for course, _ in rows]
    enrolled: set[str] = set()
    if page_ids:
        enrolled = {
            str(course_id)
            for (course_id,) in db.query(CourseMember.course_id).filter(
                CourseMember.user_id == permissions.get_user_id_or_throw(),
                CourseMember.course_id.in_(page_ids),
            )
        }

    # Seats for the capped courses on this page, again in one query.
    capped_ids = [
        str(course.id) for course, _ in rows if course.max_self_registrations is not None
    ]
    students: dict[str, int] = {}
    if capped_ids:
        students = {
            str(course_id): count
            for course_id, count in db.query(CourseMember.course_id, func.count())
            .filter(
                CourseMember.course_id.in_(capped_ids),
                CourseMember.course_role_id == "_student",
            )
            .group_by(CourseMember.course_id)
        }

    def _seats_left(course: Course) -> Optional[int]:
        if course.max_self_registrations is None:
            return None
        used = students.get(str(course.id), 0)
        return max(course.max_self_registrations - used, 0)

    # Built field by field on purpose: an explicit constructor is what
    # guarantees a future column on Course cannot leak into the catalog.
    items = []
    for course, organization_title in rows:
        seats_left = _seats_left(course)
        items.append(
            CoursePublicList(
                id=str(course.id),
                title=course.title,
                description=course.description,
                path=str(course.path),
                language_code=course.language_code,
                organization_title=organization_title,
                enrolled=str(course.id) in enrolled,
                seats_left=seats_left,
                full=seats_left == 0,
            )
        )
    return items, total


# Upper bound for the anonymous catalog: it is a landing-page teaser, not a
# search API, and an unauthenticated endpoint must stay cheap per request.
ANONYMOUS_CATALOG_LIMIT = 200


def list_anonymous_catalog(db: Session) -> list[CoursePublicCatalogEntry]:
    """The catalog as shown to visitors who are not signed in (issue #415).

    Same predicate as the signed-in catalog (public, course and organization
    not archived) and additionally hides courses whose ``visible`` is False:
    a lecturer who hid a course from students has not advertised it. No
    membership lookup, so there is nothing caller-relative to leak.
    """
    rows = (
        _catalog_query(db)
        .filter(Course.visible.isnot(False))
        .with_entities(Course.id, Course.title, Course.description, Course.language_code)
        .order_by(Course.title.asc(), Course.id.asc())
        .limit(ANONYMOUS_CATALOG_LIMIT)
        .all()
    )
    # Explicit constructor, as in list_public_courses: a new Course column
    # cannot reach anonymous visitors by accident.
    return [
        CoursePublicCatalogEntry(
            id=str(course_id),
            title=title,
            description=description,
            language_code=language_code,
        )
        for course_id, title, description, language_code in rows
    ]


def get_public_course_or_404(course_id: UUID | str, db: Session) -> Course:
    """The public course with this id, or 404.

    Missing, private and archived-organization all raise the *same* error:
    telling them apart would confirm that a course exists.
    """
    row = _catalog_query(db).filter(Course.id == str(course_id)).first()
    if row is None:
        raise PermissionDeniedAsNotFound(detail="No public course with this id.")
    return row[0]


def resolve_registration_group(
    course: Course, permissions: Principal, db: Session
) -> CourseGroup:
    """The group a self-registered student joins.

    The course's first group by creation order, not the alphabetically first —
    ordering by title would drop strangers into whatever real teaching group
    happens to sort earliest ("Group A"). A course with no groups at all gets
    one named ``default``.

    ``id`` breaks ties because Postgres ``now()`` is fixed for a transaction,
    so groups created in one batch share a ``created_at`` to the microsecond.
    The tie-break is then arbitrary but *stable*, which is the property that
    actually matters: every self-registering student in a given course lands
    in the same group rather than being scattered across the batch.

    Mirrors ``course_member_import._get_or_create_course_group``; not reused,
    because that helper looks a group up *by title* and this one takes
    whichever exists.
    """
    group = (
        db.query(CourseGroup)
        .filter(CourseGroup.course_id == course.id)
        .order_by(CourseGroup.created_at.asc(), CourseGroup.id.asc())
        .first()
    )
    if group is not None:
        return group

    # Two first-registrations racing would both see zero groups and both try
    # to insert "default", which course_group_title_key forbids. Take the
    # savepoint so losing the race costs the insert, not the caller's whole
    # transaction.
    try:
        with db.begin_nested():
            group = CourseGroup(
                course_id=course.id,
                title=SELF_REGISTRATION_GROUP_TITLE,
                description="Created automatically for self-registered students.",
                created_by=permissions.user_id,
                updated_by=permissions.user_id,
            )
            db.add(group)
            db.flush()
        logger.info(
            "Created the '%s' course group for self-registration in course %s",
            SELF_REGISTRATION_GROUP_TITLE,
            course.id,
        )
        return group
    except exc.IntegrityError:
        group = (
            db.query(CourseGroup)
            .filter(
                CourseGroup.course_id == course.id,
                CourseGroup.title == SELF_REGISTRATION_GROUP_TITLE,
            )
            .first()
        )
        if group is None:  # pragma: no cover - only if the constraint changed
            raise
        return group


def _ensure_seat_available(
    course: Course, user_id: str, db: Session
) -> Optional[CourseMember]:
    """Raise 409 when the course's self-registration cap is reached.

    Locks the course row (``FOR UPDATE`` on ``course`` only) before counting,
    so two students racing for the last seat serialize here: the second one
    counts after the first has committed and sees the course full. The lock is
    held until the caller's commit. Uncapped courses skip the lock entirely.

    Returns the caller's membership if one appeared while waiting for the
    lock: a retried request from the same user must get that back, not a 409
    for a seat they already hold. The caller's pre-lock check is stale then.
    """
    if course.max_self_registrations is None:
        return None
    cap = (
        db.query(Course.max_self_registrations)
        .filter(Course.id == course.id)
        .with_for_update(of=Course)
        .scalar()
    )
    if cap is None:
        return None
    existing = (
        db.query(CourseMember)
        .filter(CourseMember.course_id == course.id, CourseMember.user_id == user_id)
        .first()
    )
    if existing is not None:
        return existing
    students = (
        db.query(func.count(CourseMember.id))
        .filter(
            CourseMember.course_id == course.id,
            CourseMember.course_role_id == "_student",
        )
        .scalar()
    )
    if students >= cap:
        raise ConflictException(
            error_code="CONFLICT_003",
            detail="This course is full.",
            context={"course_id": str(course.id), "max_self_registrations": cap},
        )
    return None


async def register_in_public_course(
    course_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> Tuple[CourseMember, bool]:
    """Enrol the caller in a public course as ``_student``.

    Returns ``(member, created)``. Idempotent: an existing membership is
    returned untouched with ``created=False``, whatever its role — a lecturer
    who clicks Register is not demoted.
    """
    if permissions.is_service:
        raise ForbiddenException(
            detail="Self-registration is for user accounts, not service accounts."
        )

    course = get_public_course_or_404(course_id, db)
    user_id = permissions.get_user_id_or_throw()

    existing = (
        db.query(CourseMember)
        .filter(
            CourseMember.course_id == course.id,
            CourseMember.user_id == user_id,
        )
        .first()
    )
    if existing is not None:
        return existing, False

    existing = _ensure_seat_available(course, user_id, db)
    if existing is not None:
        return existing, False

    group = resolve_registration_group(course, permissions, db)

    try:
        with db.begin_nested():
            member = CourseMember(
                user_id=user_id,
                course_id=course.id,
                course_group_id=group.id,
                # Literal, never from the request. This is the whole security
                # property of self-registration.
                course_role_id="_student",
                properties={"self_registered": True},
                created_by=user_id,
                updated_by=user_id,
            )
            db.add(member)
            db.flush()
    except exc.IntegrityError:
        # course_member_key on (user_id, course_id): someone else's request
        # won the race. Their row is as good as ours would have been.
        existing = (
            db.query(CourseMember)
            .filter(
                CourseMember.course_id == course.id,
                CourseMember.user_id == user_id,
            )
            .first()
        )
        if existing is None:  # pragma: no cover - only if the constraint changed
            raise
        return existing, False

    # Flush, hook, then commit — the ordering api/course_member_import.py uses,
    # so a hook failure rolls the membership back instead of leaving a member
    # whose side effects never ran. (Not fully atomic past this point:
    # provision_submission_groups_for_user commits internally. Pre-existing and
    # shared with the import path.)
    from computor_backend.business_logic.course_member_post_create import (
        course_member_post_create,
    )

    await course_member_post_create(member, db, permissions=permissions)
    db.commit()
    db.refresh(member)

    logger.info(
        "User %s self-registered in public course %s (group %s)",
        user_id,
        course.id,
        group.id,
    )
    return member, True
