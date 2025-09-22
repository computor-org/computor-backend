# from collections import defaultdict
# import os
import os
from typing import Annotated, Optional
from uuid import UUID
from fastapi import Depends
# from gitlab import Gitlab
# from gitlab.v4.objects import ProjectCommit
from sqlalchemy.orm import Session, aliased, joinedload

from ctutor_backend.api.exceptions import BadRequestException, NotFoundException
# from ctutor_backend.api.exceptions import BadRequestException, InternalServerException
from ctutor_backend.permissions.auth import get_current_permissions
from ctutor_backend.permissions.core import check_course_permissions
from ctutor_backend.permissions.principal import Principal
# from ctutor_backend.api.queries import latest_result_subquery, results_count_subquery
from ctutor_backend.database import get_db
# from ctutor_backend.generator.git_helper import clone_or_pull_and_checkout
# from ctutor_backend.interface.course_member_comments import CourseMemberCommentList
from ctutor_backend.interface.accounts import AccountCreate
from ctutor_backend.interface.course_member_accounts import (
    CourseMemberProviderAccountUpdate,
    CourseMemberReadinessStatus,
)
from ctutor_backend.interface.course_members import CourseMemberGet, CourseMemberInterface
from ctutor_backend.interface.courses import CourseGet, CourseProperties
# from ctutor_backend.interface.git import get_git_commits
from ctutor_backend.interface.organizations import OrganizationProperties
from ctutor_backend.api.api_builder import CrudRouter
# from ctutor_backend.interface.tokens import decrypt_api_key
from ctutor_backend.interface.users import UserGet
from ctutor_backend.model.course import Course, CourseContent, CourseContentType, CourseMember, CourseMemberComment, CourseRole
from ctutor_backend.model.course import CourseSubmissionGroup, CourseSubmissionGroupMember, CourseSubmissionGroupGrading
from ctutor_backend.model.organization import Organization
from ctutor_backend.model.result import Result
from ctutor_backend.model.auth import Account, User
from sqlalchemy import func

from ctutor_backend.settings import settings
course_member_router = CrudRouter(CourseMemberInterface)


def _load_course_member_with_provider(
    course_member_id: UUID | str,
    permissions: Principal,
    db: Session,
):
    course_member = (
        check_course_permissions(permissions, CourseMember, "_student", db)
        .options(
            joinedload(CourseMember.course).joinedload(Course.organization),
            joinedload(CourseMember.user),
        )
        .filter(CourseMember.id == course_member_id)
        .first()
    )

    if not course_member:
        raise NotFoundException()

    course = course_member.course
    if not course:
        raise NotFoundException(detail="Course not found for course member")

    organization = course.organization
    if not organization:
        raise NotFoundException(detail="Organization not found for course")

    org_props = (
        OrganizationProperties(**organization.properties)
        if organization.properties
        else OrganizationProperties()
    )

    course_props = (
        CourseProperties(**course.properties)
        if course.properties
        else CourseProperties()
    )

    provider_url: Optional[str] = None
    if org_props.gitlab and org_props.gitlab.url:
        provider_url = org_props.gitlab.url.strip()
    elif course_props.gitlab and course_props.gitlab.url:
        provider_url = course_props.gitlab.url.strip()

    provider_type = "gitlab" if provider_url else None

    return course_member, provider_url, provider_type


def _get_existing_account(
    db: Session,
    course_member: CourseMember,
    provider_url: Optional[str],
):
    if not provider_url:
        return None

    return (
        db.query(Account)
        .filter(
            Account.user_id == course_member.user_id,
            Account.provider == provider_url,
            Account.type == "gitlab",
        )
        .first()
    )


def _build_validation_status(
    course_member: CourseMember,
    provider_url: Optional[str],
    provider_type: Optional[str],
    existing_account: Optional[Account],
) -> CourseMemberReadinessStatus:
    requires_account = bool(provider_url)
    has_account = existing_account is not None

    return CourseMemberReadinessStatus(
        course_member_id=str(course_member.id),
        course_id=str(course_member.course_id),
        organization_id=str(course_member.course.organization_id),
        course_role_id=course_member.course_role_id,
        provider=provider_url,
        provider_type=provider_type,
        requires_account=requires_account,
        has_account=has_account,
        is_ready=(not requires_account) or has_account,
        provider_account_id=existing_account.provider_account_id if existing_account else None,
    )


@course_member_router.router.get(
    "/{course_member_id}/validate",
    response_model=CourseMemberReadinessStatus,
)
async def validate_course_member(
    course_member_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
):
    course_member, provider_url, provider_type = _load_course_member_with_provider(
        course_member_id, permissions, db
    )
    existing_account = _get_existing_account(db, course_member, provider_url)
    return _build_validation_status(course_member, provider_url, provider_type, existing_account)


@course_member_router.router.post(
    "/{course_member_id}/register",
    response_model=CourseMemberReadinessStatus,
)
async def register_course_member_provider_account(
    course_member_id: UUID | str,
    payload: CourseMemberProviderAccountUpdate,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
):
    course_member, provider_url, provider_type = _load_course_member_with_provider(
        course_member_id, permissions, db
    )

    if not provider_url:
        raise BadRequestException(
            "Course organization does not define a GitLab provider, no account required."
        )

    provider_account_id = payload.provider_account_id.strip()

    existing_account = _get_existing_account(db, course_member, provider_url)

    conflicting_account = (
        db.query(Account)
        .filter(
            Account.provider == provider_url,
            Account.type == "gitlab",
            Account.provider_account_id == provider_account_id,
            Account.user_id != course_member.user_id,
        )
        .first()
    )

    if conflicting_account:
        raise BadRequestException(
            "Provider account ID is already linked to another user for this provider."
        )

    if existing_account:
        if existing_account.provider_account_id == provider_account_id:
            return _build_validation_status(
                course_member, provider_url, provider_type, existing_account
            )
        existing_account.provider_account_id = provider_account_id
        existing_account.updated_at = func.now()
    else:
        account_payload = AccountCreate(
            provider=provider_url,
            type="gitlab",
            provider_account_id=provider_account_id,
            user_id=str(course_member.user_id),
        )
        new_account = Account(**account_payload.model_dump())
        db.add(new_account)
        existing_account = new_account

    db.commit()
    db.refresh(existing_account)

    return _build_validation_status(course_member, provider_url, provider_type, existing_account)


@course_member_router.router.get("/{course_member_id}/protocol", response_model=dict)
async def get_protocol(permissions: Annotated[Principal, Depends(get_current_permissions)], course_member_id: UUID | str, db: Session = Depends(get_db)):

    if check_course_permissions(permissions,CourseMember,"_maintainer",db).filter(CourseMember.id == course_member_id).first() == None:
        raise NotFoundException()

    protocol = {}

    meta = db.query(
        CourseMember,
        User,
        Course,
        Organization.properties
    ).select_from(CourseMember) \
        .join(Course,Course.id == CourseMember.course_id) \
            .join(Organization,Course.organization_id == Organization.id) \
                .join(User,User.id == CourseMember.user_id,User.user_type == "user") \
                    .filter(CourseMember.id == course_member_id) \
                        .first()
    meta[0].user = None

    protocol["user"] = UserGet.model_validate(meta[1])
    protocol["course_member"] = CourseMemberGet.model_validate(meta[0])
    protocol["course"] = CourseGet.model_validate(meta[2])

    course_id = meta[0].course_id

    result = db.query(
        Result.created_at,
        Result.result,
        Result.submit,
        CourseContent.path,
        CourseContentType.slug,
    ) \
        .select_from(CourseMember) \
            .join(CourseSubmissionGroupMember, CourseSubmissionGroupMember.course_member_id == CourseMember.id) \
                .join(CourseSubmissionGroup,CourseSubmissionGroup.id == CourseSubmissionGroupMember.course_submission_group_id) \
                    .join(Result,Result.course_submission_group_id == CourseSubmissionGroup.id) \
                        .join(CourseContent,CourseContent.id == Result.course_content_id) \
                            .join(CourseContentType,CourseContentType.id == CourseContent.course_content_type_id) \
                                .group_by(
                                    Result.created_at,
                                    Result.result,
                                    Result.submit,
                                    CourseContent.path,
                                    CourseContentType.slug
                                ) \
                                    .filter(CourseMember.id == course_member_id, Result.status == 0).all()

    json_result = [
        {
            "created_at": str(r[0]),
            "result": r[1],
            "submit": r[2],
            "path": str(r[3]),
            "content_type_slug": r[4]
        }
        for r in result
    ]

    protocol["results"] = json_result

    # Get latest grading for each submission group
    latest_grading_sub = (
        db.query(
            CourseSubmissionGroupGrading.course_submission_group_id,
            CourseSubmissionGroupGrading.grading.label("latest_grading"),
            CourseSubmissionGroupGrading.status.label("latest_status"),
            func.row_number().over(
                partition_by=CourseSubmissionGroupGrading.course_submission_group_id,
                order_by=CourseSubmissionGroupGrading.created_at.desc()
            ).label('rn')
        )
    ).subquery()

    latest_result_sub = (
        db.query(
            Result.course_content_id,
            Result.result.label("latest_result"),
            latest_grading_sub.c.latest_grading,
            latest_grading_sub.c.latest_status,
            func.max(Result.created_at).label("latest_result_date")
        )
        .select_from(Result)
        .join(CourseSubmissionGroup, Result.course_submission_group_id == CourseSubmissionGroup.id)
        .join(CourseSubmissionGroupMember, CourseSubmissionGroupMember.course_submission_group_id == CourseSubmissionGroup.id)
        .outerjoin(
            latest_grading_sub,
            (latest_grading_sub.c.course_submission_group_id == CourseSubmissionGroup.id) &
            (latest_grading_sub.c.rn == 1)
        )
        .filter(CourseSubmissionGroupMember.course_member_id == course_member_id)
        .group_by(
            Result.course_content_id,
            Result.result,
            latest_grading_sub.c.latest_grading,
            latest_grading_sub.c.latest_status
        )
    ).subquery()

    results_count_sub = (
        db.query(
            Result.course_content_id.label("course_content_id"),
            func.count(Result.id).label("total_results_count"),
            func.count().filter(Result.submit == True).label("submitted_count")
        )
        .select_from(Result)
        .join(CourseSubmissionGroup, Result.course_submission_group_id == CourseSubmissionGroup.id)
        .join(CourseSubmissionGroupMember, CourseSubmissionGroupMember.course_submission_group_id == CourseSubmissionGroup.id)
        .filter(CourseSubmissionGroupMember.course_member_id == course_member_id)
        .group_by(Result.course_content_id)
    ).subquery()

    assignments = db.query(
            CourseContent.path,
            CourseContent.title,
            CourseContent.properties.op('#>>')(['{gitlab,directory}']),
            results_count_sub.c.total_results_count,
            results_count_sub.c.submitted_count,
            latest_result_sub.c.latest_result,
            latest_result_sub.c.latest_grading,
            latest_result_sub.c.latest_status,
            latest_result_sub.c.latest_result_date,
            CourseContentType.slug,
            CourseContentType.color,
        ) \
        .join(CourseContentType,CourseContentType.id == CourseContent.course_content_type_id) \
        .filter(
            CourseContent.course_id == course_id,
            CourseContent.course_content_kind_id == "assignment"
        ) \
        .outerjoin(results_count_sub, results_count_sub.c.course_content_id == CourseContent.id) \
        .outerjoin(latest_result_sub, latest_result_sub.c.course_content_id == CourseContent.id) \
        .order_by(
            CourseContent.path,
            results_count_sub.c.total_results_count,
            results_count_sub.c.submitted_count,
            latest_result_sub.c.latest_result,
            latest_result_sub.c.latest_grading,
            latest_result_sub.c.latest_status
        ) \
        .all()

    results_subq = (
        db.query(
            Result.course_content_id.label("course_content_id"),
            func.bool_or(Result.id.isnot(None)).label("attempted"),
            func.bool_or(Result.submit == True).label("submitted")
        )
        .join(CourseSubmissionGroup, Result.course_submission_group_id == CourseSubmissionGroup.id)
        .join(CourseSubmissionGroupMember, CourseSubmissionGroupMember.course_submission_group_id == CourseSubmissionGroup.id)
        .filter(CourseSubmissionGroupMember.course_member_id == course_member_id)
        .group_by(Result.course_content_id)
    ).subquery()

    UCourseContent = aliased(CourseContent)

    results_per_unit_type = (
        db.query(
            func.subpath(CourseContent.path, 0, 1).label("unit_path"),
            CourseContentType.slug.label("type_slug"),
            func.count(CourseContent.id).label("total_count"),
            func.count().filter(results_subq.c.attempted == True).label("attempted_count"),
            func.count().filter(results_subq.c.submitted == True).label("submitted_count"),
            UCourseContent.position
        )
        .select_from(CourseContent)
        .outerjoin(results_subq, results_subq.c.course_content_id == CourseContent.id)
        .join(CourseContentType, CourseContentType.id == CourseContent.course_content_type_id)
        .filter(
            CourseContent.course_id == course_id,
            CourseContent.course_content_kind_id == "assignment"
        )
        .outerjoin(UCourseContent,(UCourseContent.path == func.subpath(CourseContent.path, 0, 1).label("unit_path")) & (UCourseContent.course_id == CourseContent.course_id))
        .group_by("unit_path", CourseContentType.slug,UCourseContent.position)
        .order_by("unit_path", CourseContentType.slug,UCourseContent.position)
        .all()
    )

    grouped_units = []

    for unit in results_per_unit_type:
        grouped_units.append({
            "path": unit[0],
            "type": unit[1],
            "total": unit[2],
            "attempted": unit[3],
            "submitted": unit[4],
            "position": str(unit[5])
        })

    protocol["reference"] = grouped_units

    grouped_assignments = {}

    for row in assignments:
        grouped_assignments[str(row.path)] = {
            "title": row[1],
            "directory": row[2],
            "results_count": row[3],
            "submitted_count": row[4],
            "latest_result": row[5],
            "latest_grading": row[6],
            "latest_status": row[7],
            "latest_result_date": row[8],
            "type_slug": row[9],
            "type_color": row[10],
        }

    comments_ = db.query(
        CourseMemberComment.message,
        CourseMemberComment.updated_at,
        CourseRole.title,
        User.given_name,
        User.family_name
    ) \
    .join(CourseMember,CourseMember.id == CourseMemberComment.transmitter_id) \
    .join(CourseRole,CourseRole.id == CourseMember.course_role_id) \
    .join(User, User.id == CourseMember.user_id) \
    .filter(CourseMemberComment.course_member_id == course_member_id).all()

    comments = [
        {
            "message": c[0],
            "updated_at": c[1],
            "from": {
                "course_role_id": c[2],
                "given_name": c[3],
                "family_name": c[4]
            }
        }
        for c in comments_
    ]

    protocol["comments"] = comments

    protocol["assignments"] = grouped_assignments

    # organization_props = OrganizationProperties(**meta[3])
    # token = decrypt_api_key(organization_props.gitlab.token)

    # repository_dir = os.path.join(settings.API_LOCAL_STORAGE_DIR,"course-members")

    # course_member_directory = os.path.join(f"{repository_dir}",str(course_member_id))

    # if not os.path.exists(course_member_directory):
    #     os.makedirs(course_member_directory,exist_ok=True)
    
    # full_https_git_path = f'{organization_props.gitlab.url}/{protocol["course_member"].properties.gitlab.full_path}'

    # clone_or_pull_and_checkout(course_member_directory,full_https_git_path, token, "main")

    # commits = get_git_commits(course_member_directory)

    # protocol["commits"] = commits
    
    protocol["commits"] = []

    return protocol

@course_member_router.router.get("/{course_member_id}/protocol2", response_model=dict)
async def get_protocol_2(permissions: Annotated[Principal, Depends(get_current_permissions)], course_member_id: UUID | str, db: Session = Depends(get_db)):
    
    if check_course_permissions(permissions,CourseMember,"_maintainer",db).filter(CourseMember.id == course_member_id).first() == None:
        raise NotFoundException()
