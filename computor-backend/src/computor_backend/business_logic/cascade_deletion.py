"""
Business logic for cascade deletion of organizations, course families, courses, and examples.

This module provides functions to delete entities and all their descendants,
including proper handling of RESTRICT constraints and MinIO storage cleanup.

IMPORTANT: These operations permanently delete data. Use dry_run=True to preview.
"""

import logging
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, or_, literal, text, cast
from sqlalchemy.orm import Session
from sqlalchemy.types import String

from computor_types.cascade_deletion import (
    EntityDeleteCount,
    CascadeDeletePreview,
    CascadeDeleteResult,
    ExampleDeletePreview,
    ExampleBulkDeleteRequest,
    ExampleBulkDeleteResult,
    ForceLevel,
)
from ..model import (
    Organization,
    CourseFamily,
    Course,
    CourseContentType,
    CourseGroup,
    CourseContent,
    CourseMember,
    SubmissionGroup,
    SubmissionGroupMember,
    CourseMemberComment,
    Result,
    Message,
    StudentProfile,
    ExampleRepository,
    Example,
    ExampleVersion,
    ExampleDependency,
    CourseContentDeployment,
    DeploymentHistory,
)
from ..model.artifact import (
    SubmissionArtifact,
    ResultArtifact,
    SubmissionGrade,
    SubmissionReview,
)
from ..services.storage_service import StorageService, get_storage_service
from ..services.cascade_cleanup import (
    cleanup_submission_artifacts_batch,
    cleanup_results_batch,
    collect_artifact_storage_info,
    collect_result_artifact_storage_info,
    cleanup_example_versions_batch,
)

logger = logging.getLogger(__name__)


class CourseEntityIds:
    """Container for collected entity IDs within a course."""

    def __init__(self):
        self.course_member_ids: List[str] = []
        self.course_group_ids: List[str] = []
        self.course_content_type_ids: List[str] = []
        self.course_content_ids: List[str] = []
        self.submission_group_ids: List[str] = []
        self.result_ids: List[str] = []


def collect_course_entity_ids(db: Session, course_id: str) -> CourseEntityIds:
    """
    Collect all entity IDs for a course for deletion and MinIO cleanup.

    Args:
        db: Database session
        course_id: The course ID

    Returns:
        CourseEntityIds with all related entity IDs
    """
    ids = CourseEntityIds()

    # Collect course members
    members = db.query(CourseMember.id).filter(
        CourseMember.course_id == course_id
    ).all()
    ids.course_member_ids = [str(m.id) for m in members]

    # Collect course groups
    groups = db.query(CourseGroup.id).filter(
        CourseGroup.course_id == course_id
    ).all()
    ids.course_group_ids = [str(g.id) for g in groups]

    # Collect course content types
    content_types = db.query(CourseContentType.id).filter(
        CourseContentType.course_id == course_id
    ).all()
    ids.course_content_type_ids = [str(ct.id) for ct in content_types]

    # Collect course contents
    contents = db.query(CourseContent.id).filter(
        CourseContent.course_id == course_id
    ).all()
    ids.course_content_ids = [str(c.id) for c in contents]

    # Collect submission groups
    submission_groups = db.query(SubmissionGroup.id).filter(
        SubmissionGroup.course_id == course_id
    ).all()
    ids.submission_group_ids = [str(sg.id) for sg in submission_groups]

    # Collect results (for MinIO cleanup)
    results = db.query(Result.id).filter(
        Result.course_content_id.in_(ids.course_content_ids) if ids.course_content_ids else False
    ).all()
    ids.result_ids = [str(r.id) for r in results]

    return ids


def count_course_entities(db: Session, course_id: str) -> EntityDeleteCount:
    """
    Count all entities that would be deleted for a course.

    Args:
        db: Database session
        course_id: The course ID

    Returns:
        EntityDeleteCount with counts of each entity type
    """
    counts = EntityDeleteCount()

    # Count course members
    counts.course_members = db.query(CourseMember).filter(
        CourseMember.course_id == course_id
    ).count()

    # Count course groups
    counts.course_groups = db.query(CourseGroup).filter(
        CourseGroup.course_id == course_id
    ).count()

    # Count course content types
    counts.course_content_types = db.query(CourseContentType).filter(
        CourseContentType.course_id == course_id
    ).count()

    # Count course contents
    course_content_ids = [
        str(c.id) for c in
        db.query(CourseContent.id).filter(CourseContent.course_id == course_id).all()
    ]
    counts.course_contents = len(course_content_ids)

    # Count submission groups
    counts.submission_groups = db.query(SubmissionGroup).filter(
        SubmissionGroup.course_id == course_id
    ).count()

    if course_content_ids:
        # Count results
        counts.results = db.query(Result).filter(
            Result.course_content_id.in_(course_content_ids)
        ).count()

        # Count course content deployments
        counts.course_content_deployments = db.query(CourseContentDeployment).filter(
            CourseContentDeployment.course_content_id.in_(course_content_ids)
        ).count()

    # Count submission group members
    submission_group_ids = [
        str(sg.id) for sg in
        db.query(SubmissionGroup.id).filter(SubmissionGroup.course_id == course_id).all()
    ]
    if submission_group_ids:
        counts.submission_group_members = db.query(SubmissionGroupMember).filter(
            SubmissionGroupMember.submission_group_id.in_(submission_group_ids)
        ).count()

        # Count submission artifacts
        counts.submission_artifacts = db.query(SubmissionArtifact).filter(
            SubmissionArtifact.submission_group_id.in_(submission_group_ids)
        ).count()

        # Count submission grades and reviews
        artifact_ids = [
            str(a.id) for a in
            db.query(SubmissionArtifact.id).filter(
                SubmissionArtifact.submission_group_id.in_(submission_group_ids)
            ).all()
        ]
        if artifact_ids:
            counts.submission_grades = db.query(SubmissionGrade).filter(
                SubmissionGrade.artifact_id.in_(artifact_ids)
            ).count()
            counts.submission_reviews = db.query(SubmissionReview).filter(
                SubmissionReview.artifact_id.in_(artifact_ids)
            ).count()

    # Count course member comments
    course_member_ids = [
        str(m.id) for m in
        db.query(CourseMember.id).filter(CourseMember.course_id == course_id).all()
    ]
    if course_member_ids:
        counts.course_member_comments = db.query(CourseMemberComment).filter(
            or_(
                CourseMemberComment.transmitter_id.in_(course_member_ids),
                CourseMemberComment.course_member_id.in_(course_member_ids)
            )
        ).count()

    # Count messages targeted to this course
    counts.messages = db.query(Message).filter(
        Message.course_id == course_id
    ).count()

    return counts


async def delete_course_cascade(
    db: Session,
    course_id: str,
    storage: StorageService | None = None,
    dry_run: bool = False
) -> CascadeDeleteResult:
    """
    Delete a course and all its descendant data.

    Deletion order (bottom-up to handle RESTRICT constraints):
    1. SubmissionGrade (RESTRICT on CourseMember)
    2. SubmissionReview (RESTRICT on CourseMember)
    3. Result & ResultArtifact (RESTRICT on CourseMember, CourseContentType)
    4. SubmissionArtifact
    5. SubmissionGroupMember (RESTRICT on CourseMember)
    6. SubmissionGroup
    7. DeploymentHistory (CASCADE from CourseContentDeployment)
    8. CourseContentDeployment
    9. CourseContent (RESTRICT FK to CourseContentType)
    10. CourseContentType
    11. CourseMemberComment
    12. CourseMember (RESTRICT FK to CourseGroup)
    13. CourseGroup
    14. Message
    15. Course

    Args:
        db: Database session
        course_id: The course ID to delete
        storage: Optional storage service for MinIO cleanup
        dry_run: If True, only return counts without deleting

    Returns:
        CascadeDeleteResult with deletion counts
    """
    if storage is None:
        storage = get_storage_service()

    # Verify course exists
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return CascadeDeleteResult(
            dry_run=dry_run,
            entity_type="course",
            entity_id=str(course_id),
            deleted_counts=EntityDeleteCount(),
            errors=[f"Course not found: {course_id}"]
        )

    # Count entities
    counts = count_course_entities(db, course_id)

    if dry_run:
        return CascadeDeleteResult(
            dry_run=True,
            entity_type="course",
            entity_id=str(course_id),
            deleted_counts=counts,
            minio_objects_deleted=0,
            errors=[]
        )

    # Collect IDs for MinIO cleanup before deletion
    entity_ids = collect_course_entity_ids(db, course_id)
    artifact_storage_info = collect_artifact_storage_info(db, entity_ids.submission_group_ids)

    errors = []
    minio_deleted = 0

    try:
        # Get all submission artifact IDs for this course
        submission_artifact_ids = [
            str(a.id) for a in
            db.query(SubmissionArtifact.id).filter(
                SubmissionArtifact.submission_group_id.in_(entity_ids.submission_group_ids)
            ).all()
        ] if entity_ids.submission_group_ids else []

        # 1. Delete SubmissionGrade (RESTRICT on CourseMember)
        if submission_artifact_ids:
            db.query(SubmissionGrade).filter(
                SubmissionGrade.artifact_id.in_(submission_artifact_ids)
            ).delete(synchronize_session=False)

            # 2. Delete SubmissionReview (RESTRICT on CourseMember)
            db.query(SubmissionReview).filter(
                SubmissionReview.artifact_id.in_(submission_artifact_ids)
            ).delete(synchronize_session=False)

        # 3. Delete ResultArtifact and Result (RESTRICT on CourseMember, CourseContentType)
        if entity_ids.result_ids:
            db.query(ResultArtifact).filter(
                ResultArtifact.result_id.in_(entity_ids.result_ids)
            ).delete(synchronize_session=False)

            db.query(Result).filter(
                Result.id.in_(entity_ids.result_ids)
            ).delete(synchronize_session=False)

        # 4. Delete SubmissionArtifact
        if entity_ids.submission_group_ids:
            db.query(SubmissionArtifact).filter(
                SubmissionArtifact.submission_group_id.in_(entity_ids.submission_group_ids)
            ).delete(synchronize_session=False)

            # 5. Delete SubmissionGroupMember (RESTRICT on CourseMember)
            db.query(SubmissionGroupMember).filter(
                SubmissionGroupMember.submission_group_id.in_(entity_ids.submission_group_ids)
            ).delete(synchronize_session=False)

            # 6. Delete SubmissionGroup
            db.query(SubmissionGroup).filter(
                SubmissionGroup.id.in_(entity_ids.submission_group_ids)
            ).delete(synchronize_session=False)

        # 7-8. Delete DeploymentHistory and CourseContentDeployment
        if entity_ids.course_content_ids:
            deployment_ids = [
                str(d.id) for d in
                db.query(CourseContentDeployment.id).filter(
                    CourseContentDeployment.course_content_id.in_(entity_ids.course_content_ids)
                ).all()
            ]
            if deployment_ids:
                db.query(DeploymentHistory).filter(
                    DeploymentHistory.deployment_id.in_(deployment_ids)
                ).delete(synchronize_session=False)

                db.query(CourseContentDeployment).filter(
                    CourseContentDeployment.id.in_(deployment_ids)
                ).delete(synchronize_session=False)

            # 9. Delete CourseContent
            db.query(CourseContent).filter(
                CourseContent.id.in_(entity_ids.course_content_ids)
            ).delete(synchronize_session=False)

        # 10. Delete CourseContentType
        if entity_ids.course_content_type_ids:
            db.query(CourseContentType).filter(
                CourseContentType.id.in_(entity_ids.course_content_type_ids)
            ).delete(synchronize_session=False)

        # 11. Delete CourseMemberComment
        if entity_ids.course_member_ids:
            db.query(CourseMemberComment).filter(
                or_(
                    CourseMemberComment.transmitter_id.in_(entity_ids.course_member_ids),
                    CourseMemberComment.course_member_id.in_(entity_ids.course_member_ids)
                )
            ).delete(synchronize_session=False)

            # 12. Delete CourseMember
            db.query(CourseMember).filter(
                CourseMember.id.in_(entity_ids.course_member_ids)
            ).delete(synchronize_session=False)

        # 13. Delete CourseGroup
        if entity_ids.course_group_ids:
            db.query(CourseGroup).filter(
                CourseGroup.id.in_(entity_ids.course_group_ids)
            ).delete(synchronize_session=False)

        # 14. Delete Message (targeted to course)
        db.query(Message).filter(
            Message.course_id == course_id
        ).delete(synchronize_session=False)

        # 15. Delete Course
        db.query(Course).filter(Course.id == course_id).delete(synchronize_session=False)

        # Commit database changes
        db.commit()
        counts.courses = 1

        logger.info(f"Deleted course {course_id} and all descendant data")

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting course {course_id}: {e}")
        errors.append(f"Database error: {str(e)}")
        return CascadeDeleteResult(
            dry_run=False,
            entity_type="course",
            entity_id=str(course_id),
            deleted_counts=EntityDeleteCount(),
            errors=errors
        )

    # Clean up MinIO storage (after successful DB commit)
    try:
        minio_deleted += await cleanup_submission_artifacts_batch(artifact_storage_info, storage)
        minio_deleted += await cleanup_results_batch(entity_ids.result_ids, storage)
    except Exception as e:
        logger.warning(f"MinIO cleanup error for course {course_id}: {e}")
        errors.append(f"MinIO cleanup error: {str(e)}")

    return CascadeDeleteResult(
        dry_run=False,
        entity_type="course",
        entity_id=str(course_id),
        deleted_counts=counts,
        minio_objects_deleted=minio_deleted,
        errors=errors
    )


async def delete_course_family_cascade(
    db: Session,
    course_family_id: str,
    storage: StorageService | None = None,
    dry_run: bool = False
) -> CascadeDeleteResult:
    """
    Delete a course family and all its courses.

    Args:
        db: Database session
        course_family_id: The course family ID to delete
        storage: Optional storage service for MinIO cleanup
        dry_run: If True, only return counts without deleting

    Returns:
        CascadeDeleteResult with deletion counts
    """
    if storage is None:
        storage = get_storage_service()

    # Verify course family exists
    family = db.query(CourseFamily).filter(CourseFamily.id == course_family_id).first()
    if not family:
        return CascadeDeleteResult(
            dry_run=dry_run,
            entity_type="course_family",
            entity_id=str(course_family_id),
            deleted_counts=EntityDeleteCount(),
            errors=[f"Course family not found: {course_family_id}"]
        )

    # Get all courses in this family
    courses = db.query(Course).filter(Course.course_family_id == course_family_id).all()
    course_ids = [str(c.id) for c in courses]

    # Aggregate counts from all courses
    total_counts = EntityDeleteCount()
    total_counts.course_families = 1
    total_counts.courses = len(course_ids)

    for course_id in course_ids:
        course_counts = count_course_entities(db, course_id)
        total_counts.course_members += course_counts.course_members
        total_counts.course_groups += course_counts.course_groups
        total_counts.course_content_types += course_counts.course_content_types
        total_counts.course_contents += course_counts.course_contents
        total_counts.submission_groups += course_counts.submission_groups
        total_counts.submission_group_members += course_counts.submission_group_members
        total_counts.submission_artifacts += course_counts.submission_artifacts
        total_counts.submission_grades += course_counts.submission_grades
        total_counts.submission_reviews += course_counts.submission_reviews
        total_counts.results += course_counts.results
        total_counts.course_content_deployments += course_counts.course_content_deployments
        total_counts.course_member_comments += course_counts.course_member_comments
        total_counts.messages += course_counts.messages

    # Count messages targeted to the family
    family_messages = db.query(Message).filter(
        Message.course_family_id == course_family_id
    ).count()
    total_counts.messages += family_messages

    if dry_run:
        return CascadeDeleteResult(
            dry_run=True,
            entity_type="course_family",
            entity_id=str(course_family_id),
            deleted_counts=total_counts,
            minio_objects_deleted=0,
            errors=[]
        )

    errors = []
    total_minio_deleted = 0

    # Delete all courses first
    for course_id in course_ids:
        result = await delete_course_cascade(db, course_id, storage, dry_run=False)
        total_minio_deleted += result.minio_objects_deleted
        errors.extend(result.errors)

    # Delete family-scoped messages
    try:
        db.query(Message).filter(
            Message.course_family_id == course_family_id
        ).delete(synchronize_session=False)

        # Delete the course family
        db.query(CourseFamily).filter(
            CourseFamily.id == course_family_id
        ).delete(synchronize_session=False)

        db.commit()
        logger.info(f"Deleted course family {course_family_id}")

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting course family {course_family_id}: {e}")
        errors.append(f"Database error: {str(e)}")

    return CascadeDeleteResult(
        dry_run=False,
        entity_type="course_family",
        entity_id=str(course_family_id),
        deleted_counts=total_counts,
        minio_objects_deleted=total_minio_deleted,
        errors=errors
    )


async def delete_organization_cascade(
    db: Session,
    organization_id: str,
    storage: StorageService | None = None,
    dry_run: bool = False
) -> CascadeDeleteResult:
    """
    Delete an organization and all its descendant data.

    This includes:
    - All course families and their courses
    - Example repositories and their examples
    - Student profiles (NOT the users themselves)
    - Messages targeted to the organization

    Args:
        db: Database session
        organization_id: The organization ID to delete
        storage: Optional storage service for MinIO cleanup
        dry_run: If True, only return counts without deleting

    Returns:
        CascadeDeleteResult with deletion counts
    """
    if storage is None:
        storage = get_storage_service()

    # Verify organization exists
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        return CascadeDeleteResult(
            dry_run=dry_run,
            entity_type="organization",
            entity_id=str(organization_id),
            deleted_counts=EntityDeleteCount(),
            errors=[f"Organization not found: {organization_id}"]
        )

    # Get all course families
    families = db.query(CourseFamily).filter(
        CourseFamily.organization_id == organization_id
    ).all()
    family_ids = [str(f.id) for f in families]

    # Get all courses directly under organization (shouldn't happen normally, but safe)
    direct_courses = db.query(Course).filter(
        Course.organization_id == organization_id,
        ~Course.course_family_id.in_(family_ids) if family_ids else True
    ).all()

    # Get example repositories
    example_repos = db.query(ExampleRepository).filter(
        ExampleRepository.organization_id == organization_id
    ).all()

    # Initialize total counts
    total_counts = EntityDeleteCount()

    # Count course family data
    for family_id in family_ids:
        family_result = await delete_course_family_cascade(
            db, family_id, storage, dry_run=True
        )
        total_counts.course_families += 1
        total_counts.courses += family_result.deleted_counts.courses
        total_counts.course_members += family_result.deleted_counts.course_members
        total_counts.course_groups += family_result.deleted_counts.course_groups
        total_counts.course_content_types += family_result.deleted_counts.course_content_types
        total_counts.course_contents += family_result.deleted_counts.course_contents
        total_counts.submission_groups += family_result.deleted_counts.submission_groups
        total_counts.submission_group_members += family_result.deleted_counts.submission_group_members
        total_counts.submission_artifacts += family_result.deleted_counts.submission_artifacts
        total_counts.submission_grades += family_result.deleted_counts.submission_grades
        total_counts.submission_reviews += family_result.deleted_counts.submission_reviews
        total_counts.results += family_result.deleted_counts.results
        total_counts.course_content_deployments += family_result.deleted_counts.course_content_deployments
        total_counts.course_member_comments += family_result.deleted_counts.course_member_comments
        total_counts.messages += family_result.deleted_counts.messages

    # Count example repositories and their examples
    total_counts.example_repositories = len(example_repos)
    for repo in example_repos:
        examples = db.query(Example).filter(Example.example_repository_id == repo.id).all()
        total_counts.examples += len(examples)
        for ex in examples:
            versions = db.query(ExampleVersion).filter(ExampleVersion.example_id == ex.id).all()
            total_counts.example_versions += len(versions)
            deps = db.query(ExampleDependency).filter(ExampleDependency.example_id == ex.id).count()
            total_counts.example_dependencies += deps

    # Count student profiles
    total_counts.student_profiles = db.query(StudentProfile).filter(
        StudentProfile.organization_id == organization_id
    ).count()

    # Count org-level messages
    org_messages = db.query(Message).filter(
        Message.organization_id == organization_id
    ).count()
    total_counts.messages += org_messages

    if dry_run:
        return CascadeDeleteResult(
            dry_run=True,
            entity_type="organization",
            entity_id=str(organization_id),
            deleted_counts=total_counts,
            minio_objects_deleted=0,
            errors=[]
        )

    errors = []
    total_minio_deleted = 0

    # Delete all course families (which deletes all courses)
    for family_id in family_ids:
        result = await delete_course_family_cascade(db, family_id, storage, dry_run=False)
        total_minio_deleted += result.minio_objects_deleted
        errors.extend(result.errors)

    # Delete any direct courses (edge case)
    for course in direct_courses:
        result = await delete_course_cascade(db, str(course.id), storage, dry_run=False)
        total_minio_deleted += result.minio_objects_deleted
        errors.extend(result.errors)

    try:
        # Delete example versions and their storage, then examples and repos
        for repo in example_repos:
            # Use source_url as bucket name
            if not repo.source_url:
                raise ValueError(f"Repository {repo.id} has no source_url (bucket name)")
            bucket = repo.source_url

            examples = db.query(Example).filter(Example.example_repository_id == repo.id).all()
            for ex in examples:
                versions = db.query(ExampleVersion).filter(ExampleVersion.example_id == ex.id).all()
                version_storage = []
                for v in versions:
                    if v.storage_path:
                        version_storage.append((v.storage_path, bucket))

                # Clean up storage for versions
                if version_storage:
                    minio_deleted = await cleanup_example_versions_batch(version_storage, storage)
                    total_minio_deleted += minio_deleted

        # Delete example dependencies first (CASCADE on both sides)
        example_ids = [
            str(ex.id) for repo in example_repos
            for ex in db.query(Example.id).filter(Example.example_repository_id == repo.id).all()
        ]
        if example_ids:
            db.query(ExampleDependency).filter(
                or_(
                    ExampleDependency.example_id.in_(example_ids),
                    ExampleDependency.depends_id.in_(example_ids)
                )
            ).delete(synchronize_session=False)

            # Delete example versions
            db.query(ExampleVersion).filter(
                ExampleVersion.example_id.in_(example_ids)
            ).delete(synchronize_session=False)

            # Delete examples
            db.query(Example).filter(
                Example.id.in_(example_ids)
            ).delete(synchronize_session=False)

        # Delete example repositories
        repo_ids = [str(r.id) for r in example_repos]
        if repo_ids:
            db.query(ExampleRepository).filter(
                ExampleRepository.id.in_(repo_ids)
            ).delete(synchronize_session=False)

        # Delete student profiles
        db.query(StudentProfile).filter(
            StudentProfile.organization_id == organization_id
        ).delete(synchronize_session=False)

        # Delete organization-level messages
        db.query(Message).filter(
            Message.organization_id == organization_id
        ).delete(synchronize_session=False)

        # Delete the organization
        db.query(Organization).filter(
            Organization.id == organization_id
        ).delete(synchronize_session=False)

        db.commit()
        logger.info(f"Deleted organization {organization_id} and all descendant data")

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting organization {organization_id}: {e}")
        errors.append(f"Database error: {str(e)}")

    return CascadeDeleteResult(
        dry_run=False,
        entity_type="organization",
        entity_id=str(organization_id),
        deleted_counts=total_counts,
        minio_objects_deleted=total_minio_deleted,
        errors=errors
    )


async def delete_examples_by_pattern(
    db: Session,
    request: ExampleBulkDeleteRequest,
    storage: StorageService | None = None,
) -> ExampleBulkDeleteResult:
    """
    Delete examples matching an identifier pattern.

    Uses Ltree ~ operator for pattern matching.
    Pattern examples:
    - "itpcp.progphys.py.*" matches itpcp.progphys.py.example1, itpcp.progphys.py.example2
    - "itpcp.*" matches itpcp.anything

    Args:
        db: Database session
        request: ExampleBulkDeleteRequest with pattern and options
        storage: Optional storage service for MinIO cleanup

    Returns:
        ExampleBulkDeleteResult with deletion details
    """
    if storage is None:
        storage = get_storage_service()

    # Build query for matching examples
    query = db.query(Example).join(
        ExampleRepository, Example.example_repository_id == ExampleRepository.id
    )

    # Apply Ltree pattern filter (use literal to prevent SQLAlchemy from processing as Ltree)
    query = query.filter(Example.identifier.op('~')(literal(request.identifier_pattern)))

    # Optionally filter by repository
    if request.repository_id:
        query = query.filter(Example.example_repository_id == request.repository_id)

    examples = query.all()

    if not examples:
        return ExampleBulkDeleteResult(
            dry_run=request.dry_run,
            pattern_matched=request.identifier_pattern,
            repository_id=request.repository_id,
            examples_affected=0,
            versions_deleted=0,
            dependencies_deleted=0,
            storage_objects_deleted=0,
            deployment_references_orphaned=0,
            examples=[],
            errors=[]
        )

    # Build preview for each example
    previews = []
    total_versions = 0
    total_deployment_refs = 0
    example_ids = []

    for ex in examples:
        # Get versions for this example
        versions = db.query(ExampleVersion).filter(ExampleVersion.example_id == ex.id).all()
        version_ids = [str(v.id) for v in versions]

        # Count ACTIVE deployments only (currently deployed/deploying/pending with these specific versions)
        active_deployment_refs = db.query(CourseContentDeployment).filter(
            CourseContentDeployment.example_version_id.in_(version_ids),
            CourseContentDeployment.deployment_status.in_(['pending', 'deploying', 'deployed'])
        ).count()

        # Get repository info
        repo = db.query(ExampleRepository).filter(
            ExampleRepository.id == ex.example_repository_id
        ).first()

        storage_paths = [v.storage_path for v in versions if v.storage_path]

        previews.append(ExampleDeletePreview(
            example_id=str(ex.id),
            identifier=str(ex.identifier),
            title=ex.title or "",
            directory=ex.directory,
            repository_id=str(ex.example_repository_id),
            repository_name=repo.name if repo else "Unknown",
            version_count=len(versions),
            storage_paths=storage_paths,
            deployment_references=active_deployment_refs
        ))

        example_ids.append(str(ex.id))
        total_versions += len(versions)
        total_deployment_refs += active_deployment_refs

    # Check if we should block due to deployment references based on force level
    if total_deployment_refs > 0 and not request.dry_run:
        # Collect all version IDs across all examples
        all_version_ids = []
        for ex in examples:
            versions = db.query(ExampleVersion).filter(ExampleVersion.example_id == ex.id).all()
            all_version_ids.extend([str(v.id) for v in versions])

        # For OLD force level, check if any active deployments are in non-archived courses
        if request.force_level == ForceLevel.OLD:
            # Count active deployments in NON-archived courses
            active_in_live_courses = db.query(CourseContentDeployment).join(
                CourseContent, CourseContentDeployment.course_content_id == CourseContent.id
            ).join(
                Course, CourseContent.course_id == Course.id
            ).filter(
                CourseContentDeployment.example_version_id.in_(all_version_ids),
                CourseContentDeployment.deployment_status.in_(['pending', 'deploying', 'deployed']),
                Course.archived_at.is_(None)  # Course is NOT archived
            ).count()

            if active_in_live_courses > 0:
                return ExampleBulkDeleteResult(
                    dry_run=request.dry_run,
                    pattern_matched=request.identifier_pattern,
                    repository_id=request.repository_id,
                    examples_affected=len(examples),
                    versions_deleted=0,
                    dependencies_deleted=0,
                    storage_objects_deleted=0,
                    deployment_references_orphaned=total_deployment_refs,
                    examples=previews,
                    errors=[
                        f"Cannot delete: {active_in_live_courses} active deployment(s) in non-archived courses. "
                        f"Use --force-all to delete anyway (deployments will be orphaned)."
                    ]
                )
        elif request.force_level == ForceLevel.NONE:
            # Block if ANY active deployments exist
            return ExampleBulkDeleteResult(
                dry_run=request.dry_run,
                pattern_matched=request.identifier_pattern,
                repository_id=request.repository_id,
                examples_affected=len(examples),
                versions_deleted=0,
                dependencies_deleted=0,
                storage_objects_deleted=0,
                deployment_references_orphaned=total_deployment_refs,
                examples=previews,
                errors=[
                    f"Cannot delete: {total_deployment_refs} active deployment(s) reference these examples. "
                    f"Use --force-old to delete if courses are archived, or --force-all to force deletion."
                ]
            )
        # ForceLevel.ALL: Don't block, proceed with deletion

    # Count dependencies
    deps_count = db.query(ExampleDependency).filter(
        or_(
            ExampleDependency.example_id.in_(example_ids),
            ExampleDependency.depends_id.in_(example_ids)
        )
    ).count()

    if request.dry_run:
        return ExampleBulkDeleteResult(
            dry_run=True,
            pattern_matched=request.identifier_pattern,
            repository_id=request.repository_id,
            examples_affected=len(examples),
            versions_deleted=total_versions,
            dependencies_deleted=deps_count,
            storage_objects_deleted=0,
            deployment_references_orphaned=total_deployment_refs,
            examples=previews,
            errors=[]
        )

    # Perform actual deletion
    errors = []
    storage_deleted = 0

    try:
        # Collect storage info before deletion
        version_storage = []
        for ex in examples:
            # Get the repository to determine the bucket name
            repo = db.query(ExampleRepository).filter(
                ExampleRepository.id == ex.example_repository_id
            ).first()

            if not repo:
                raise ValueError(f"Repository not found for example {ex.id}")

            # Use source_url as bucket name
            if not repo.source_url:
                raise ValueError(f"Repository {repo.id} has no source_url (bucket name)")
            bucket = repo.source_url

            versions = db.query(ExampleVersion).filter(ExampleVersion.example_id == ex.id).all()
            for v in versions:
                if v.storage_path:
                    version_storage.append((v.storage_path, bucket))

        # Delete dependencies first
        db.query(ExampleDependency).filter(
            or_(
                ExampleDependency.example_id.in_(example_ids),
                ExampleDependency.depends_id.in_(example_ids)
            )
        ).delete(synchronize_session=False)

        # Delete versions
        db.query(ExampleVersion).filter(
            ExampleVersion.example_id.in_(example_ids)
        ).delete(synchronize_session=False)

        # Delete examples
        db.query(Example).filter(
            Example.id.in_(example_ids)
        ).delete(synchronize_session=False)

        db.commit()
        logger.info(
            f"Deleted {len(examples)} examples matching pattern '{request.identifier_pattern}'"
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting examples: {e}")
        errors.append(f"Database error: {str(e)}")
        return ExampleBulkDeleteResult(
            dry_run=False,
            pattern_matched=request.identifier_pattern,
            repository_id=request.repository_id,
            examples_affected=0,
            versions_deleted=0,
            dependencies_deleted=0,
            storage_objects_deleted=0,
            deployment_references_orphaned=0,
            examples=[],
            errors=errors
        )

    # Clean up MinIO storage
    try:
        if version_storage:
            storage_deleted = await cleanup_example_versions_batch(version_storage, storage)
    except Exception as e:
        logger.warning(f"MinIO cleanup error: {e}")
        errors.append(f"MinIO cleanup error: {str(e)}")

    return ExampleBulkDeleteResult(
        dry_run=False,
        pattern_matched=request.identifier_pattern,
        repository_id=request.repository_id,
        examples_affected=len(examples),
        versions_deleted=total_versions,
        dependencies_deleted=deps_count,
        storage_objects_deleted=storage_deleted,
        deployment_references_orphaned=total_deployment_refs,
        examples=previews,
        errors=errors
    )
