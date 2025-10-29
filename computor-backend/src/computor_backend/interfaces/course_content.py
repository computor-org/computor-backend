"""Backend CourseContent interface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session
import logging

from computor_types.course_contents import (
    CourseContentInterface as CourseContentInterfaceBase,
    CourseContentQuery,
)
from computor_types.custom_types import Ltree
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.course import (
    CourseContent,
    CourseMember,
    CourseContentKind,
    SubmissionGroup,
    SubmissionGroupMember,
)

logger = logging.getLogger(__name__)


async def post_create_course_content(course_content: CourseContent, db: Session):
    """
    Post-create hook for CourseContent.

    When a new submittable course content with max_group_size=1 or None is created,
    automatically create submission groups for all existing students in the course.

    Args:
        course_content: The newly created course content
        db: Database session
    """
    # Check if this course content is submittable
    if not course_content.course_content_kind_id:
        logger.debug(f"CourseContent {course_content.id} has no kind, skipping submission group creation")
        return

    course_content_kind = db.query(CourseContentKind).filter(
        CourseContentKind.id == course_content.course_content_kind_id
    ).first()

    if not course_content_kind or not course_content_kind.submittable:
        logger.debug(f"CourseContent {course_content.id} is not submittable, skipping submission group creation")
        return

    # Only create submission groups for individual assignments (max_group_size=1 or None)
    max_group_size = course_content.max_group_size
    if max_group_size is not None and max_group_size > 1:
        logger.info(
            f"CourseContent {course_content.id} has max_group_size={max_group_size} > 1, "
            f"skipping automatic submission group creation (team submissions require manual setup)"
        )
        return

    logger.info(
        f"Creating submission groups for new individual course content {course_content.id} "
        f"in course {course_content.course_id}"
    )

    # Get all student members in this course with user info loaded
    from sqlalchemy.orm import joinedload
    student_members = (
        db.query(CourseMember)
        .options(joinedload(CourseMember.user))
        .filter(
            CourseMember.course_id == course_content.course_id,
            CourseMember.course_role_id == "_student"
        )
        .all()
    )

    created_count = 0
    for course_member in student_members:
        # Check if submission group already exists
        existing_group = (
            db.query(SubmissionGroup)
            .join(SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id)
            .filter(
                SubmissionGroup.course_content_id == course_content.id,
                SubmissionGroupMember.course_member_id == course_member.id
            )
            .first()
        )

        if existing_group:
            continue  # Already exists

        # Generate display name for individual submission (max_group_size == 1 or None)
        display_name = None
        resolved_max_group_size = max_group_size if max_group_size is not None else 1
        if resolved_max_group_size == 1 and course_member.user:
            given_name = course_member.user.given_name or ""
            family_name = course_member.user.family_name or ""
            display_name = f"{given_name} {family_name}".strip()
            if not display_name:
                display_name = course_member.user.email

        # Create submission group
        submission_group = SubmissionGroup(
            course_content_id=course_content.id,
            course_id=course_content.course_id,
            max_group_size=resolved_max_group_size,
            max_test_runs=course_content.max_test_runs,
            display_name=display_name,
            properties={}
        )
        db.add(submission_group)
        db.flush()  # Get the ID

        # Create submission group member
        submission_group_member = SubmissionGroupMember(
            submission_group_id=submission_group.id,
            course_member_id=course_member.id,
            course_id=course_content.course_id
        )
        db.add(submission_group_member)
        created_count += 1

    db.commit()
    logger.info(
        f"Created {created_count} submission groups for course content {course_content.id} "
        f"({len(student_members)} students in course)"
    )


class CourseContentInterface(CourseContentInterfaceBase, BackendEntityInterface):
    """Backend-specific CourseContent interface with model attached."""

    model = CourseContent
    endpoint = "course-contents"
    cache_ttl = 300
    post_create = post_create_course_content

    @staticmethod
    def search(db: Session, query, params: Optional[CourseContentQuery]):
        """
        Apply search filters to coursecontent query.

        Args:
            db: Database session
            query: SQLAlchemy query object
            params: Query parameters

        Returns:
            Filtered query object
        """
        if params is None:
            return query

        if params.id is not None:
            query = query.filter(CourseContent.id == params.id)
        if params.title is not None:
            query = query.filter(CourseContent.title == params.title)
        if params.description is not None:
            query = query.filter(CourseContent.description.ilike(f"%{params.description}%"))
        if params.path is not None:
            # Convert string to Ltree for proper comparison
            query = query.filter(CourseContent.path == Ltree(params.path))
        if params.course_id is not None:
            query = query.filter(CourseContent.course_id == params.course_id)
        if params.course_content_type_id is not None:
            query = query.filter(CourseContent.course_content_type_id == params.course_content_type_id)
        if params.testing_service_id is not None:
            query = query.filter(CourseContent.testing_service_id == params.testing_service_id)
        if params.example_version_id is not None:
            query = query.filter(CourseContent.example_version_id == params.example_version_id)

        return query
