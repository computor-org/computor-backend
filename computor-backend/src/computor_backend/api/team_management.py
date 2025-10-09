"""API endpoints for student team management."""

import logging
import secrets
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from computor_backend.database import get_db
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.model.course import (
    Course,
    CourseContent,
    CourseMember,
    SubmissionGroup,
    SubmissionGroupMember,
)
from computor_backend.model.auth import User
from computor_backend.business_logic.team_formation import (
    get_team_formation_rules,
    validate_team_formation_action,
    is_team_assignment,
)
from computor_backend.api.exceptions import (
    BadRequestException,
    NotFoundException,
    ForbiddenException,
)
from computor_types.team_management import (
    TeamCreate,
    TeamResponse,
    AvailableTeam,
    JoinTeamRequest,
    JoinTeamResponse,
    LeaveTeamResponse,
    TeamMemberInfo,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def generate_join_code() -> str:
    """Generate a 6-character random join code."""
    return secrets.token_hex(3).upper()


def get_team_member_info(course_member: CourseMember) -> TeamMemberInfo:
    """Convert CourseMember to TeamMemberInfo DTO."""
    user = course_member.user
    return TeamMemberInfo(
        course_member_id=str(course_member.id),
        user_id=str(user.id) if user else "",
        given_name=user.given_name if user else None,
        family_name=user.family_name if user else None,
        email=user.email if user else None,
    )


def get_course_member_for_user(
    user_id: UUID | str,
    course_id: UUID | str,
    db: Session
) -> Optional[CourseMember]:
    """Get course member for a user in a course."""
    return db.query(CourseMember).filter(
        CourseMember.user_id == user_id,
        CourseMember.course_id == course_id
    ).first()


def submission_group_to_team_response(
    submission_group: SubmissionGroup,
    db: Session,
    current_user_id: Optional[str] = None
) -> TeamResponse:
    """Convert SubmissionGroup to TeamResponse DTO."""
    # Get members
    members_query = (
        db.query(CourseMember)
        .join(SubmissionGroupMember, SubmissionGroupMember.course_member_id == CourseMember.id)
        .filter(SubmissionGroupMember.submission_group_id == submission_group.id)
    )
    members = [get_team_member_info(cm) for cm in members_query.all()]

    # Get team properties
    team_props = submission_group.properties.get('team_formation', {}) if submission_group.properties else {}

    status = team_props.get('status', 'forming')
    created_by = team_props.get('created_by', 'student')
    join_code = team_props.get('join_code')
    locked_at_str = team_props.get('locked_at')
    locked_at = datetime.fromisoformat(locked_at_str) if locked_at_str else None

    # Check if more members can join
    member_count = len(members)
    max_size = submission_group.max_group_size or 1
    can_join = member_count < max_size and status == 'forming'

    return TeamResponse(
        id=str(submission_group.id),
        course_content_id=str(submission_group.course_content_id),
        course_id=str(submission_group.course_id),
        max_group_size=max_size,
        status=status,
        created_by=created_by,
        join_code=join_code,
        members=members,
        member_count=member_count,
        can_join=can_join,
        locked_at=locked_at,
    )


@router.post(
    "/course-contents/{course_content_id}/submission-groups/my-team",
    response_model=TeamResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["team-management"],
)
async def create_my_team(
    course_content_id: UUID,
    team_data: TeamCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> TeamResponse:
    """
    Create a new team for the current user for a course content.

    Student endpoint - creates a team and adds the current user as the first member.
    """
    user_id = principal.user_id

    # Get course content
    course_content = db.query(CourseContent).filter(
        CourseContent.id == course_content_id
    ).first()
    if not course_content:
        raise NotFoundException(detail=f"Course content {course_content_id} not found")

    # Validate this is a team assignment
    if not is_team_assignment(course_content):
        raise BadRequestException(
            detail=f"Course content '{course_content.title}' is not a team assignment (max_group_size={course_content.max_group_size})"
        )

    # Get course
    course = db.query(Course).filter(Course.id == course_content.course_id).first()
    if not course:
        raise NotFoundException(detail=f"Course {course_content.course_id} not found")

    # Validate team formation rules
    allowed, error = validate_team_formation_action(course_content, "create", course, db)
    if not allowed:
        raise BadRequestException(detail=error)

    # Get course member for current user
    course_member = get_course_member_for_user(user_id, course_content.course_id, db)
    if not course_member:
        raise ForbiddenException(
            detail=f"You are not a member of course {course_content.course_id}"
        )

    # Check if user already has a team for this course content
    existing_team = (
        db.query(SubmissionGroup)
        .join(SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id)
        .filter(
            SubmissionGroup.course_content_id == course_content_id,
            SubmissionGroupMember.course_member_id == course_member.id
        )
        .first()
    )

    if existing_team:
        raise BadRequestException(
            detail=f"You already have a team for this assignment (team {existing_team.id})"
        )

    # Create submission group (team)
    submission_group = SubmissionGroup(
        course_content_id=course_content_id,
        course_id=course_content.course_id,
        max_group_size=course_content.max_group_size,
        max_test_runs=course_content.max_test_runs,
        properties={
            'team_formation': {
                'status': 'forming',
                'created_by': 'student',
                'join_code': generate_join_code(),
                'created_at': datetime.utcnow().isoformat(),
            }
        }
    )
    db.add(submission_group)
    db.flush()  # Get the ID

    # Add creator as first member
    submission_group_member = SubmissionGroupMember(
        submission_group_id=submission_group.id,
        course_member_id=course_member.id,
        course_id=course_content.course_id
    )
    db.add(submission_group_member)
    db.commit()

    logger.info(
        f"User {user_id} created team {submission_group.id} for course_content {course_content_id}"
    )

    return submission_group_to_team_response(submission_group, db, str(user_id))


@router.get(
    "/course-contents/{course_content_id}/submission-groups/my-team",
    response_model=TeamResponse,
    tags=["team-management"],
)
async def get_my_team(
    course_content_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> TeamResponse:
    """
    Get the current user's team for a course content.

    Returns 404 if user doesn't have a team yet.
    """
    user_id = principal.user_id

    # Get course content
    course_content = db.query(CourseContent).filter(
        CourseContent.id == course_content_id
    ).first()
    if not course_content:
        raise NotFoundException(detail=f"Course content {course_content_id} not found")

    # Get course member
    course_member = get_course_member_for_user(user_id, course_content.course_id, db)
    if not course_member:
        raise ForbiddenException(
            detail=f"You are not a member of course {course_content.course_id}"
        )

    # Find user's team
    submission_group = (
        db.query(SubmissionGroup)
        .join(SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id)
        .filter(
            SubmissionGroup.course_content_id == course_content_id,
            SubmissionGroupMember.course_member_id == course_member.id
        )
        .first()
    )

    if not submission_group:
        raise NotFoundException(
            detail=f"You don't have a team for this assignment yet"
        )

    return submission_group_to_team_response(submission_group, db, str(user_id))


@router.delete(
    "/course-contents/{course_content_id}/submission-groups/my-team",
    response_model=LeaveTeamResponse,
    tags=["team-management"],
)
async def leave_my_team(
    course_content_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> LeaveTeamResponse:
    """
    Leave the current user's team for a course content.

    If the user is the last member, the team is deleted.
    """
    user_id = principal.user_id

    # Get course content
    course_content = db.query(CourseContent).filter(
        CourseContent.id == course_content_id
    ).first()
    if not course_content:
        raise NotFoundException(detail=f"Course content {course_content_id} not found")

    # Get course
    course = db.query(Course).filter(Course.id == course_content.course_id).first()
    if not course:
        raise NotFoundException(detail=f"Course {course_content.course_id} not found")

    # Validate leaving is allowed
    allowed, error = validate_team_formation_action(course_content, "leave", course, db)
    if not allowed:
        raise BadRequestException(detail=error)

    # Get course member
    course_member = get_course_member_for_user(user_id, course_content.course_id, db)
    if not course_member:
        raise ForbiddenException(
            detail=f"You are not a member of course {course_content.course_id}"
        )

    # Find user's team
    submission_group = (
        db.query(SubmissionGroup)
        .join(SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id)
        .filter(
            SubmissionGroup.course_content_id == course_content_id,
            SubmissionGroupMember.course_member_id == course_member.id
        )
        .first()
    )

    if not submission_group:
        raise NotFoundException(detail="You don't have a team for this assignment")

    # Check if team is locked
    team_props = submission_group.properties.get('team_formation', {}) if submission_group.properties else {}
    if team_props.get('status') == 'locked':
        raise BadRequestException(detail="Team is locked and cannot be left")

    # Remove member from team
    membership = db.query(SubmissionGroupMember).filter(
        SubmissionGroupMember.submission_group_id == submission_group.id,
        SubmissionGroupMember.course_member_id == course_member.id
    ).first()

    if membership:
        db.delete(membership)

    # Check remaining members
    remaining_members = db.query(SubmissionGroupMember).filter(
        SubmissionGroupMember.submission_group_id == submission_group.id
    ).count()

    if remaining_members == 0:
        # Delete empty team
        db.delete(submission_group)
        db.commit()
        logger.info(
            f"User {user_id} left and deleted empty team {submission_group.id} "
            f"for course_content {course_content_id}"
        )
        return LeaveTeamResponse(
            success=True,
            message="You left the team and the team was deleted (no remaining members)"
        )
    else:
        db.commit()
        logger.info(
            f"User {user_id} left team {submission_group.id} for course_content {course_content_id}. "
            f"{remaining_members} members remaining."
        )
        return LeaveTeamResponse(
            success=True,
            message=f"You left the team. {remaining_members} member(s) remaining."
        )


@router.get(
    "/course-contents/{course_content_id}/submission-groups/available",
    response_model=List[AvailableTeam],
    tags=["team-management"],
)
async def get_available_teams(
    course_content_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> List[AvailableTeam]:
    """
    Browse available teams that the current user can join.

    Only shows teams that:
    - Are in 'forming' status
    - Have space for more members
    - Are for the specified course content
    """
    user_id = principal.user_id

    # Get course content
    course_content = db.query(CourseContent).filter(
        CourseContent.id == course_content_id
    ).first()
    if not course_content:
        raise NotFoundException(detail=f"Course content {course_content_id} not found")

    # Validate this is a team assignment
    if not is_team_assignment(course_content):
        raise BadRequestException(
            detail=f"Course content '{course_content.title}' is not a team assignment"
        )

    # Get course member
    course_member = get_course_member_for_user(user_id, course_content.course_id, db)
    if not course_member:
        raise ForbiddenException(
            detail=f"You are not a member of course {course_content.course_id}"
        )

    # Check if user already has a team
    has_team = (
        db.query(SubmissionGroup)
        .join(SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id)
        .filter(
            SubmissionGroup.course_content_id == course_content_id,
            SubmissionGroupMember.course_member_id == course_member.id
        )
        .first()
    )

    if has_team:
        raise BadRequestException(
            detail="You already have a team for this assignment"
        )

    # Get all teams for this course content
    all_teams = db.query(SubmissionGroup).filter(
        SubmissionGroup.course_content_id == course_content_id
    ).all()

    available_teams = []
    for team in all_teams:
        team_props = team.properties.get('team_formation', {}) if team.properties else {}
        status = team_props.get('status', 'forming')

        # Only show forming teams
        if status != 'forming':
            continue

        # Get member count
        member_count = db.query(SubmissionGroupMember).filter(
            SubmissionGroupMember.submission_group_id == team.id
        ).count()

        max_size = team.max_group_size or 1

        # Only show teams with space
        if member_count >= max_size:
            continue

        # Get members for display
        members_query = (
            db.query(CourseMember)
            .join(SubmissionGroupMember, SubmissionGroupMember.course_member_id == CourseMember.id)
            .filter(SubmissionGroupMember.submission_group_id == team.id)
        )
        members = [get_team_member_info(cm) for cm in members_query.all()]

        available_teams.append(AvailableTeam(
            id=str(team.id),
            member_count=member_count,
            max_group_size=max_size,
            join_code=team_props.get('join_code'),
            requires_approval=team_props.get('require_approval', False),
            status=status,
            members=members,
        ))

    logger.info(
        f"User {user_id} browsing {len(available_teams)} available teams "
        f"for course_content {course_content_id}"
    )

    return available_teams


@router.post(
    "/submission-groups/{submission_group_id}/join",
    response_model=JoinTeamResponse,
    tags=["team-management"],
)
async def join_team(
    submission_group_id: UUID,
    join_request: JoinTeamRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> JoinTeamResponse:
    """
    Join an existing team.

    If require_approval is true, the join request will be pending until approved.
    Otherwise, the user is immediately added to the team.
    """
    user_id = principal.user_id

    # Get submission group
    submission_group = db.query(SubmissionGroup).filter(
        SubmissionGroup.id == submission_group_id
    ).first()
    if not submission_group:
        raise NotFoundException(detail=f"Team {submission_group_id} not found")

    # Get course content
    course_content = db.query(CourseContent).filter(
        CourseContent.id == submission_group.course_content_id
    ).first()
    if not course_content:
        raise NotFoundException(detail=f"Course content not found")

    # Get course
    course = db.query(Course).filter(Course.id == course_content.course_id).first()
    if not course:
        raise NotFoundException(detail=f"Course not found")

    # Validate joining is allowed
    allowed, error = validate_team_formation_action(course_content, "join", course, db)
    if not allowed:
        raise BadRequestException(detail=error)

    # Get course member
    course_member = get_course_member_for_user(user_id, course_content.course_id, db)
    if not course_member:
        raise ForbiddenException(
            detail=f"You are not a member of this course"
        )

    # Check if user already has a team
    existing_team = (
        db.query(SubmissionGroup)
        .join(SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id)
        .filter(
            SubmissionGroup.course_content_id == course_content.id,
            SubmissionGroupMember.course_member_id == course_member.id
        )
        .first()
    )

    if existing_team:
        raise BadRequestException(
            detail=f"You already have a team for this assignment"
        )

    # Check team status
    team_props = submission_group.properties.get('team_formation', {}) if submission_group.properties else {}
    status = team_props.get('status', 'forming')

    if status != 'forming':
        raise BadRequestException(detail=f"Team is {status} and cannot accept new members")

    # Check if team is full
    member_count = db.query(SubmissionGroupMember).filter(
        SubmissionGroupMember.submission_group_id == submission_group_id
    ).count()

    max_size = submission_group.max_group_size or 1

    if member_count >= max_size:
        raise BadRequestException(detail="Team is full")

    # Check if approval is required (future feature)
    requires_approval = team_props.get('require_approval', False)

    if requires_approval:
        # TODO: Implement approval workflow in Phase 2B
        logger.warning("Team requires approval, but approval workflow not yet implemented")
        return JoinTeamResponse(
            id=str(submission_group_id),
            status="pending_approval",
            message="Your request to join has been sent and is pending approval"
        )

    # Add member to team immediately
    submission_group_member = SubmissionGroupMember(
        submission_group_id=submission_group_id,
        course_member_id=course_member.id,
        course_id=course_content.course_id
    )
    db.add(submission_group_member)
    db.commit()

    logger.info(
        f"User {user_id} joined team {submission_group_id} for course_content {course_content.id}"
    )

    return JoinTeamResponse(
        id=str(submission_group_id),
        status="joined",
        message=f"You have successfully joined the team ({member_count + 1}/{max_size} members)"
    )


# Export router
team_management_router = router
