"""Course-domain permission handlers.

Split out of the former ``handlers_impl`` god-module (TASK-109). Covers
the course subtree: ``Course``, ``CourseContentType``, ``CourseContent``,
``CourseMember`` (and the course-scoped artifact/group models registered
against it), ``Result`` and ``Message``. ``handlers_impl`` re-exports
every public name here so existing imports keep working.
"""

from typing import Optional
from sqlalchemy import and_, exists, or_
from sqlalchemy.orm import Session, Query, aliased
from computor_backend.permissions.handlers import PermissionHandler
from computor_backend.permissions.query_builders import CoursePermissionQueryBuilder
from computor_backend.permissions.principal import Principal, course_role_hierarchy
from computor_backend.exceptions import ForbiddenException
from computor_backend.model.auth import User
from computor_backend.model.course import (
    Course,
    CourseContent,
    CourseGroup,
    CourseMember,
    SubmissionGroup,
    SubmissionGroupMember,
)
from computor_backend.model.result import Result

__all__ = [
    "CoursePermissionHandler",
    "CourseContentTypePermissionHandler",
    "CourseContentPermissionHandler",
    "CourseMemberPermissionHandler",
    "ResultPermissionHandler",
    "MessagePermissionHandler",
]


class CoursePermissionHandler(PermissionHandler):
    """Permission handler for Course entity"""

    ACTION_ROLE_MAP = {
        "get": "_student",
        "list": "_student",
        "update": "_lecturer",
        "create": None,  # Only through general permission
        "delete": None   # Only through general permission
    }

    def can_perform_action(self, principal: Principal, action: str, resource_id: Optional[str] = None, context: Optional[dict] = None) -> bool:
        if self.check_admin(principal):
            return True

        if self.check_general_permission(principal, action):
            return True

        # Check course-specific permissions
        if resource_id and action in self.ACTION_ROLE_MAP:
            min_role = self.ACTION_ROLE_MAP[action]
            if min_role:
                # Check if user has required role in this course via course-role claim
                return principal.permitted("course", action, resource_id, course_role=min_role)

        return False

    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        if self.check_admin(principal):
            return db.query(self.entity)

        if self.check_general_permission(principal, action):
            return db.query(self.entity)

        min_role = self.ACTION_ROLE_MAP.get(action)
        if min_role:
            return CoursePermissionQueryBuilder.build_course_filtered_query(
                self.entity, principal.user_id, min_role, db
            )

        raise ForbiddenException(detail={"entity": self.resource_name})


class CourseContentTypePermissionHandler(PermissionHandler):

    def _check_role_hierarchy(self, user_roles: set, required_role: str) -> bool:
        """Check if user roles meet the required role in hierarchy"""
        if not user_roles:
            return False

        # Check if any user role has permission for the required role
        for role in user_roles:
            if course_role_hierarchy.has_role_permission(role, required_role):
                return True

        return False

    """Permission handler for CourseContentType entity

    CourseContentType can be created, updated, and deleted by lecturers and higher roles.
    Lower roles can only get and list.
    """

    ACTION_ROLE_MAP = {
        "get": "_student",      # Students and higher can view
        "list": "_student",     # Students and higher can list
        "create": "_lecturer",  # Lecturers and higher can create
        "update": "_lecturer",  # Lecturers and higher can update
        "delete": "_lecturer"   # Lecturers and higher can delete
    }

    def can_perform_action(self, principal: Principal, action: str, resource_id: Optional[str] = None, context: Optional[dict] = None) -> bool:
        if self.check_admin(principal):
            return True

        if self.check_general_permission(principal, action):
            return True

        min_role = self.ACTION_ROLE_MAP.get(action)
        if min_role:
            # For read operations, allow if user has any course membership
            if action in ["get", "list"]:
                return True  # Will be filtered by query

            # For write operations, check if user has required role in any course
            # Check if user has the required course role in their claims
            if principal.claims and principal.claims.dependent:
                for course_id, roles in principal.claims.dependent.get("course", {}).items():
                    if self._check_role_hierarchy(roles, min_role):
                        return True
            return False

        return False

    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        if self.check_admin(principal):
            return db.query(self.entity)

        if self.check_general_permission(principal, action):
            return db.query(self.entity)

        min_role = self.ACTION_ROLE_MAP.get(action)
        if min_role:
            # For CourseContentType, we need to check if the user has the required role
            # in at least one course that uses this content type.
            # For read operations, return all content types if user has any course membership.
            if action in ["get", "list"]:
                # Check if user has any course membership
                has_membership = db.query(
                    exists().where(
                        CourseMember.user_id == principal.user_id
                    )
                ).scalar()

                if has_membership:
                    return db.query(self.entity)
                else:
                    # Return empty query if no membership
                    return db.query(self.entity).filter(self.entity.id == None)

            # For write operations, check role hierarchy
            user_courses = CoursePermissionQueryBuilder.user_courses_subquery(
                principal.user_id, min_role, db
            )

            # Check if user has required role in any course
            has_required_role = db.query(
                exists().where(
                    CourseMember.course_id.in_(user_courses)
                )
            ).scalar()

            if has_required_role:
                return db.query(self.entity)
            else:
                # Return empty query if insufficient permissions
                return db.query(self.entity).filter(self.entity.id == None)

        raise ForbiddenException(detail={"entity": self.resource_name})


class CourseContentPermissionHandler(PermissionHandler):
    """Permission handler for CourseContent entity"""

    ACTION_ROLE_MAP = {
        "get": "_student",
        "list": "_student",
        "create": "_lecturer",
        "update": "_lecturer",
        "delete": "_lecturer",
        "archive": "_lecturer"
    }

    def can_perform_action(self, principal: Principal, action: str, resource_id: Optional[str] = None, context: Optional[dict] = None) -> bool:
        if self.check_admin(principal):
            return True

        if self.check_general_permission(principal, action):
            return True

        # Check course-based permissions
        if action in self.ACTION_ROLE_MAP:
            min_role = self.ACTION_ROLE_MAP[action]
            # For create/update/delete/archive, require course context to match the specific course
            if action in ["create", "update", "delete", "archive"]:
                # Prefer explicit course_id from context, fallback to resource_id
                course_id = (context or {}).get("course_id") or resource_id
                if course_id:
                    # Check course role
                    if not principal.permitted("course", action, course_id, course_role=min_role):
                        return False
                    # Enforce additional parent context constraints when applicable
                    if not self.check_additional_context_permissions(
                        principal, context, exclude_keys=["course_id"]
                    ):
                        return False
                    return True
                return False
            # For get/list, filtering is applied in build_query
            return True

        return False

    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        if self.check_admin(principal):
            return db.query(self.entity)

        if self.check_general_permission(principal, action):
            return db.query(self.entity)

        min_role = self.ACTION_ROLE_MAP.get(action)
        if min_role:
            cm_other = aliased(CourseMember)

            subquery = CoursePermissionQueryBuilder.user_courses_subquery(
                principal.user_id, min_role, db
            )

            query = (
                db.query(self.entity)
                .select_from(User)
                .outerjoin(cm_other, cm_other.user_id == User.id)
                .outerjoin(self.entity, self.entity.course_id == cm_other.course_id)
                .filter(
                    cm_other.course_id.in_(subquery)
                )
            )

            return query

        raise ForbiddenException(detail={"entity": self.resource_name})


class CourseMemberPermissionHandler(PermissionHandler):
    """Permission handler for CourseMember entity"""

    ACTION_ROLE_MAP = {
        "get": "_tutor",
        "list": "_tutor",
        "update": "_lecturer",
        "create": "_lecturer",
        "delete": "_lecturer"
    }

    def can_perform_action(self, principal: Principal, action: str, resource_id: Optional[str] = None, context: Optional[dict] = None) -> bool:
        # Admins and organization managers manage course rosters everywhere
        # (consistent with the uncapped assignment ceiling): full read/write on
        # course members in any course.
        if self.check_admin(principal) or "_organization_manager" in principal.roles:
            return True

        if self.check_general_permission(principal, action):
            return True

        # Students can view their own membership
        if action in ["get", "list"] and resource_id == principal.user_id:
            return True

        # Creation must be scoped to a specific course via resource_id (course_id)
        if action == "create":
            # resource_id expected to be course_id; prefer context course_id
            course_id = (context or {}).get("course_id") or resource_id
            if course_id:
                if not principal.permitted("course", action, course_id, course_role=self.ACTION_ROLE_MAP.get(action)):
                    return False
                # Enforce the role-assignment ceiling: lecturers (and below) may
                # only enrol members as _student; only maintainers, owners,
                # organization managers and admins may grant a role above
                # _student. Mirrors the guard on update and the email-import path.
                target_role = (context or {}).get("course_role_id")
                if target_role:
                    ceiling = principal.get_course_assignment_ceiling(course_id)
                    if not ceiling or not course_role_hierarchy.can_assign_role(ceiling, target_role):
                        raise ForbiddenException(
                            error_code="AUTHZ_005",
                            detail=f"You cannot assign the role '{target_role}'. "
                                   f"Your role can only assign roles up to '{ceiling or '—'}'.",
                            context={"target_role": target_role, "course_id": course_id},
                        )
                # Enforce additional parent context constraints (ignore course_id)
                return self.check_additional_context_permissions(
                    principal, context, exclude_keys=["course_id"]
                )
            # Require maintainer role or above in the target course
            return False

        return False

    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        # Admins and organization managers see/manage every course's roster.
        if self.check_admin(principal) or "_organization_manager" in principal.roles:
            return db.query(self.entity)

        if self.check_general_permission(principal, action):
            return db.query(self.entity)

        min_role = self.ACTION_ROLE_MAP.get(action)
        if min_role:
            # Get courses where principal has required role
            permitted_courses = CoursePermissionQueryBuilder.user_courses_subquery(
                principal.user_id, min_role, db
            )

            # Base filter: all entities in permitted courses
            filters = [self.entity.course_id.in_(permitted_courses)]

            # For read actions on entities with user_id (e.g., CourseMember),
            # also allow viewing own record (for students)
            if action in ["get", "list"] and hasattr(self.entity, 'user_id'):
                filters.append(self.entity.user_id == principal.user_id)

            return db.query(self.entity).filter(or_(*filters))

        raise ForbiddenException(detail={"entity": self.resource_name})


class ResultPermissionHandler(PermissionHandler):
    """Permission handler for Result entities that don't have direct course_id"""

    ACTION_ROLE_MAP = {
        "get": ["_student"],      # Students can get their own results
        "list": ["_student"],     # Students can list their own results
        "create": ["_student"],   # Students can create results (via tests)
        "update": ["_tutor"],     # Tutors can update results
        "delete": ["_lecturer"],  # Only lecturers can delete results
    }

    def can_perform_action(self, principal: Principal, action: str, resource_id: Optional[str] = None) -> bool:
        if self.check_admin(principal):
            return True

        if self.check_general_permission(principal, action):
            return True

        # For specific resource operations, check course membership through course_content
        if resource_id and action in self.ACTION_ROLE_MAP:
            # Would need to query the Result and check permissions through its course_content
            # This is handled in build_query for efficiency
            return True

        return False

    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        if self.check_admin(principal):
            return db.query(Result)

        if self.check_general_permission(principal, action):
            return db.query(Result)

        min_role = self.ACTION_ROLE_MAP.get(action)
        if min_role:
            # For Result, we need to join through CourseContent to get to Course
            query = (
                db.query(Result)
                .join(CourseContent, CourseContent.id == Result.course_content_id)
            )

            # Check if user has tutor+ role in any course - they can see all results in their courses
            tutor_courses = CoursePermissionQueryBuilder.user_courses_subquery(
                principal.user_id, "_tutor", db
            )

            # Check if user is a student in any course
            student_course_member = aliased(CourseMember)

            # Build query that allows:
            # 1. Tutors/lecturers to see all results in courses they have tutor+ access to
            # 2. Students to see only their own results (via course_member_id or submission_group membership)
            query = query.outerjoin(
                student_course_member,
                and_(
                    student_course_member.course_id == CourseContent.course_id,
                    student_course_member.user_id == principal.user_id
                )
            ).filter(
                or_(
                    # Tutors/lecturers can see all results in their courses
                    CourseContent.course_id.in_(tutor_courses),
                    # Students can see their own results
                    and_(
                        student_course_member.id.isnot(None),
                        or_(
                            Result.course_member_id == student_course_member.id,
                            Result.submission_group_id.in_(
                                db.query(SubmissionGroupMember.submission_group_id)
                                .filter(SubmissionGroupMember.course_member_id == student_course_member.id)
                            )
                        )
                    )
                )
            )

            return query

        raise ForbiddenException(detail={"entity": self.resource_name})


class MessagePermissionHandler(PermissionHandler):
    """Permission handler for Message entity with multi-scope visibility.

    Read visibility per target (additive — author always sees own):

    +-----------------------+-----------------------------------------------+
    | user_id               | recipient or author                           |
    | course_member_id      | course_member owner OR course role >= _tutor  |
    | submission_group_id   | submission_group_member OR course role >=     |
    |                       | _tutor in the containing course               |
    | course_group_id       | course_group member OR course role >= _tutor  |
    | course_content_id     | any course_member of the containing course    |
    | course_id             | any course_member of that course              |
    | course_family_id      | scoped course_family role OR course_member of |
    |                       | any course inside the family (cascade)        |
    | organization_id       | scoped organization role OR course_member of  |
    |                       | any course inside the organization (cascade)  |
    | (none — global)       | everyone (read); admin-only on the write side |
    +-----------------------+-----------------------------------------------+

    Write rules are enforced in ``business_logic.messages`` (create) and
    ``business_logic.message_operations`` (update/delete: author only).
    The build_query restriction below additionally blocks update/delete
    of targets whose CREATE path is not implemented yet, so the audit
    trail can't disagree with the create-side guard.
    """

    def can_perform_action(self, principal: Principal, action: str, resource_id: Optional[str] = None, context: Optional[dict] = None) -> bool:
        if self.check_admin(principal):
            return True

        # Create: allow if user participates in the context or is tutor+ of course context.
        if action == "create":
            return True  # validated in create business logic

        # Update/Delete: author only (non-admin), but restricted by target type
        if action in ["update", "delete"]:
            return True  # enforced in build_query by restricting to author

        # Get/List: allowed; filtered in query
        if action in ["get", "list"]:
            return True

        return False

    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        base = db.query(self.entity)

        if self.check_admin(principal):
            return base

        filters = []

        # Author can always access their own messages.
        filters.append(self.entity.author_id == principal.user_id)

        # user_id target: recipient sees the message.
        filters.append(self.entity.user_id == principal.user_id)

        # course_member_id target: the principal who owns the course_member.
        cm_ids_subq = db.query(CourseMember.id).filter(CourseMember.user_id == principal.user_id)
        filters.append(self.entity.course_member_id.in_(cm_ids_subq))

        # submission_group_id target: members of the group.
        sgm_subq = (
            db.query(SubmissionGroupMember.submission_group_id)
            .join(CourseMember, CourseMember.id == SubmissionGroupMember.course_member_id)
            .filter(CourseMember.user_id == principal.user_id)
        )
        filters.append(self.entity.submission_group_id.in_(sgm_subq))

        # course_group_id target: members of the group.
        cg_subq = (
            db.query(CourseMember.course_group_id)
            .filter(
                CourseMember.user_id == principal.user_id,
                CourseMember.course_group_id.isnot(None)
            )
        )
        filters.append(self.entity.course_group_id.in_(cg_subq))

        # course_content_id target: any course_member of the containing course.
        user_course_contents_subq = (
            db.query(CourseContent.id)
            .join(CourseMember, CourseMember.course_id == CourseContent.course_id)
            .filter(CourseMember.user_id == principal.user_id)
        )
        filters.append(self.entity.course_content_id.in_(user_course_contents_subq))

        # course_id target: any course_member of that course.
        course_ids_subq = (
            db.query(CourseMember.course_id)
            .filter(CourseMember.user_id == principal.user_id)
        )
        filters.append(self.entity.course_id.in_(course_ids_subq))

        # Course family / organization cascade: any course the principal is
        # a member of cascades read access UP to its family and org. This
        # mirrors OrganizationPermissionHandler / CourseFamilyPermissionHandler
        # so that an org-level announcement reaches every student in any of
        # its courses without requiring an explicit org-scoped role.
        family_via_course_subq = (
            db.query(Course.course_family_id)
            .join(CourseMember, CourseMember.course_id == Course.id)
            .filter(CourseMember.user_id == principal.user_id)
        )
        filters.append(self.entity.course_family_id.in_(family_via_course_subq))

        org_via_course_subq = (
            db.query(Course.organization_id)
            .join(CourseMember, CourseMember.course_id == Course.id)
            .filter(CourseMember.user_id == principal.user_id)
        )
        filters.append(self.entity.organization_id.in_(org_via_course_subq))

        # Explicit scoped-role visibility for org / family (additive on top of
        # the cascade above). ``_developer`` is the lowest org/family role.
        family_via_member_ids = principal.get_scoped_ids_with_role(
            "course_family", "_developer"
        )
        if family_via_member_ids:
            filters.append(self.entity.course_family_id.in_(family_via_member_ids))

        org_via_member_ids = principal.get_scoped_ids_with_role(
            "organization", "_developer"
        )
        if org_via_member_ids:
            filters.append(self.entity.organization_id.in_(org_via_member_ids))

        # Tutor / lecturer escalation: extra read access to all message
        # types within courses where the principal has an elevated role.
        permitted_courses = CoursePermissionQueryBuilder.user_courses_subquery(
            principal.user_id, "_tutor", db
        )
        if permitted_courses is not None:
            filters.append(
                self.entity.course_member_id.in_(
                    db.query(CourseMember.id).filter(CourseMember.course_id.in_(permitted_courses))
                )
            )
            filters.append(
                self.entity.submission_group_id.in_(
                    db.query(SubmissionGroup.id).filter(SubmissionGroup.course_id.in_(permitted_courses))
                )
            )
            filters.append(
                self.entity.course_group_id.in_(
                    db.query(CourseGroup.id).filter(CourseGroup.course_id.in_(permitted_courses))
                )
            )
            filters.append(
                self.entity.course_content_id.in_(
                    db.query(CourseContent.id).filter(CourseContent.course_id.in_(permitted_courses))
                )
            )
            filters.append(self.entity.course_id.in_(permitted_courses))

        # Global messages (every target NULL) are readable by everyone —
        # the write side is admin-only, but once posted they're a broadcast.
        filters.append(
            and_(
                self.entity.user_id.is_(None),
                self.entity.course_member_id.is_(None),
                self.entity.submission_group_id.is_(None),
                self.entity.course_content_id.is_(None),
                self.entity.course_group_id.is_(None),
                self.entity.course_id.is_(None),
                self.entity.course_family_id.is_(None),
                self.entity.organization_id.is_(None),
            )
        )

        query = base.filter(or_(*filters))

        # Update / delete: author only. Additionally block the targets whose
        # CREATE path raises NotImplementedException, so a row that was never
        # supposed to exist via the public API can't be quietly mutated.
        if action in ["update", "delete"]:
            query = query.filter(self.entity.author_id == principal.user_id)
            query = query.filter(
                and_(
                    self.entity.user_id.is_(None),
                    self.entity.course_member_id.is_(None),
                )
            )

        return query
