from typing import Optional
from sqlalchemy import and_, exists, not_, or_, select
from sqlalchemy.orm import Session, Query, aliased
from computor_backend.permissions.handlers import PermissionHandler
from computor_backend.permissions.query_builders import (
    CoursePermissionQueryBuilder,
    OrganizationPermissionQueryBuilder,
    UserPermissionQueryBuilder,
)
from computor_backend.permissions.principal import Principal, course_role_hierarchy
from computor_backend.api.exceptions import ForbiddenException
from computor_backend.database import SessionLocal
from computor_backend.model.auth import User
from computor_backend.model.course import (
    Course,
    CourseContent,
    CourseContentType,
    CourseGroup,
    CourseMember,
    SubmissionGroup,
    SubmissionGroupMember,
)
from computor_backend.model.message import Message
from computor_backend.model.result import Result
from computor_backend.model.role import UserRole


class UserPermissionHandler(PermissionHandler):
    """Permission handler for User entity"""
    
    ACTION_PERMISSIONS = {
        "list": ["list", "get"],  # Actions that allow listing
        "get": ["get"],
        "create": ["create"],
        "update": ["update"],
        "delete": ["delete"]
    }
    
    def can_perform_action(self, principal: Principal, action: str, resource_id: Optional[str] = None, context: Optional[dict] = None) -> bool:
        # Admin can do anything
        if self.check_admin(principal):
            return True

        # Check general permission (e.g., _user_manager)
        if self.check_general_permission(principal, action):
            # User managers can list/get any user
            if action in ["list", "get", "create"]:
                return True

            # For update/delete, user managers cannot modify admins or service accounts.
            # The actual check is in build_query; here we just allow the action through.
            if action in ["update", "delete"] and resource_id:
                return True

        # Users can view themselves
        if action in ["list", "get"] and resource_id == principal.user_id:
            return True

        return False
    
    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        # Admin gets everything
        if self.check_admin(principal):
            return db.query(self.entity)

        # Check general permission (e.g., _user_manager)
        if self.check_general_permission(principal, action):
            base_query = db.query(self.entity)

            # For update/delete actions, user managers cannot modify admins or service accounts
            if action in ["update", "delete"]:
                # Exclude service accounts
                base_query = base_query.filter(self.entity.is_service == False)

                # Exclude users with admin role
                admin_subquery = exists().where(
                    and_(
                        UserRole.user_id == self.entity.id,
                        UserRole.role_id == "_admin"
                    )
                )
                base_query = base_query.filter(not_(admin_subquery))

            return base_query

        # For list/get, users can see themselves and users in their courses (as tutor+)
        if action in ["list", "get"]:
            return UserPermissionQueryBuilder.filter_visible_users(principal.user_id, db)

        raise ForbiddenException(detail=f"Insufficient permissions to {action} {self.resource_name}")


class AccountPermissionHandler(PermissionHandler):
    """Permission handler for Account entity"""
    
    def can_perform_action(self, principal: Principal, action: str, resource_id: Optional[str] = None, context: Optional[dict] = None) -> bool:
        if self.check_admin(principal):
            return True
        
        if self.check_general_permission(principal, action):
            return True
        
        # Users can view their own accounts
        if action in ["list", "get"]:
            return True
        
        return False
    
    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        if self.check_admin(principal):
            return db.query(self.entity)
        
        if self.check_general_permission(principal, action):
            return db.query(self.entity)
        
        # Users can only see their own accounts
        if action in ["list", "get"]:
            return (
                db.query(self.entity)
                .join(User, User.id == self.entity.user_id)
                .filter(User.id == principal.user_id)
            )
        
        raise ForbiddenException(detail={"entity": self.resource_name})


class ProfilePermissionHandler(PermissionHandler):
    """Permission handler for Profile entity"""

    def can_perform_action(self, principal: Principal, action: str, resource_id: Optional[str] = None, context: Optional[dict] = None) -> bool:
        if self.check_admin(principal):
            return True

        if self.check_general_permission(principal, action):
            return True

        # Users can create their own profile
        if action == "create":
            if context and context.get("user_id") == principal.user_id:
                return True
            return False

        # Users can view and update their own profile
        if action in ["list", "get", "update"]:
            return True

        return False

    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        if self.check_admin(principal):
            return db.query(self.entity)

        if self.check_general_permission(principal, action):
            return db.query(self.entity)

        if action in ["list", "get", "update"]:
            return db.query(self.entity).filter(self.entity.user_id == principal.user_id)

        raise ForbiddenException(detail={"entity": self.resource_name})


class StudentProfilePermissionHandler(PermissionHandler):
    """Permission handler for StudentProfile entity

    Students are READ-ONLY - they can only view their student profiles.
    Only admins and users with general permissions can create/update/delete.
    """

    def can_perform_action(self, principal: Principal, action: str, resource_id: Optional[str] = None, context: Optional[dict] = None) -> bool:
        if self.check_admin(principal):
            return True

        if self.check_general_permission(principal, action):
            return True

        # Students can ONLY view (list/get) their own student profiles
        # They CANNOT create, update, or delete
        if action in ["list", "get"]:
            return True

        # Block all other actions (create, update, delete) for regular users
        return False

    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        if self.check_admin(principal):
            return db.query(self.entity)

        if self.check_general_permission(principal, action):
            return db.query(self.entity)

        # Users can only list/get their own student profiles
        if action in ["list", "get"]:
            return db.query(self.entity).filter(self.entity.user_id == principal.user_id)

        raise ForbiddenException(detail={"entity": self.resource_name})


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


class OrganizationPermissionHandler(PermissionHandler):
    """Permission handler for Organization entity.

    Read visibility is *additive*: a principal sees an organization if
    any of these is true (admin / general permission shortcut aside) —

    - they are a member of any course inside the org (existing behavior,
      kept for back-compat: course role cascade UP for read only); or
    - they are an OrganizationMember with any scoped role on the org.

    Write actions (``update`` / ``delete``) require an explicit scoped
    role on the org itself (or admin / general permission). Scoped
    roles do NOT cascade between scopes — being an org ``_owner`` does
    not grant any course_family or course privilege.
    """

    # Course-membership cascade only powers the read filter.
    READ_COURSE_ROLE = "_student"

    ACTION_ORG_ROLE_MAP = {
        # update / archive / delete: developer can edit, owner-only deletes.
        "update": "_developer",
        "archive": "_owner",
        "delete": "_owner",
    }

    def can_perform_action(
        self,
        principal: Principal,
        action: str,
        resource_id: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> bool:
        if self.check_admin(principal):
            return True

        if self.check_general_permission(principal, action):
            return True

        if action in ("get", "list"):
            return True  # build_query applies the actual filter

        min_org_role = self.ACTION_ORG_ROLE_MAP.get(action)
        if min_org_role and resource_id:
            return principal.has_organization_role(resource_id, min_org_role)

        return False

    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        if self.check_admin(principal):
            return db.query(self.entity)

        if self.check_general_permission(principal, action):
            return db.query(self.entity)

        if action in ("get", "list"):
            # Visible if course-cascade OR org_member: union of two id sets.
            course_subquery = (
                CoursePermissionQueryBuilder.user_courses_subquery(
                    principal.user_id, self.READ_COURSE_ROLE, db
                )
            )
            org_via_course = (
                db.query(Course.organization_id)
                .filter(Course.id.in_(course_subquery))
            )

            org_via_member_ids = principal.get_scoped_ids_with_role(
                "organization", "_developer"
            )
            # _developer is the lowest scoped role; hierarchy includes
            # _manager and _owner.

            return db.query(self.entity).filter(
                or_(
                    self.entity.id.in_(org_via_course),
                    self.entity.id.in_(org_via_member_ids)
                    if org_via_member_ids
                    else False,
                )
            )

        min_org_role = self.ACTION_ORG_ROLE_MAP.get(action)
        if min_org_role:
            org_ids = principal.get_scoped_ids_with_role("organization", min_org_role)
            if not org_ids:
                # Empty filter → empty result, not a 403.
                return db.query(self.entity).filter(self.entity.id.in_([]))
            return db.query(self.entity).filter(self.entity.id.in_(org_ids))

        raise ForbiddenException(detail={"entity": self.resource_name})


class CourseFamilyPermissionHandler(PermissionHandler):
    """Permission handler for CourseFamily entity.

    Symmetric to ``OrganizationPermissionHandler``. Read visibility is
    additive (course-membership cascade UP, plus explicit scoped role
    on the family). Write actions need an explicit scoped role on the
    family itself.
    """

    READ_COURSE_ROLE = "_student"

    ACTION_FAMILY_ROLE_MAP = {
        "update": "_developer",
        "archive": "_owner",
        "delete": "_owner",
    }

    def can_perform_action(
        self,
        principal: Principal,
        action: str,
        resource_id: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> bool:
        if self.check_admin(principal):
            return True

        if self.check_general_permission(principal, action):
            return True

        if action in ("get", "list"):
            return True

        min_family_role = self.ACTION_FAMILY_ROLE_MAP.get(action)
        if min_family_role and resource_id:
            return principal.has_course_family_role(resource_id, min_family_role)

        return False

    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        if self.check_admin(principal):
            return db.query(self.entity)

        if self.check_general_permission(principal, action):
            return db.query(self.entity)

        if action in ("get", "list"):
            course_subquery = CoursePermissionQueryBuilder.user_courses_subquery(
                principal.user_id, self.READ_COURSE_ROLE, db
            )
            family_via_course = (
                db.query(Course.course_family_id)
                .filter(Course.id.in_(course_subquery))
            )

            family_via_member_ids = principal.get_scoped_ids_with_role(
                "course_family", "_developer"
            )

            return db.query(self.entity).filter(
                or_(
                    self.entity.id.in_(family_via_course),
                    self.entity.id.in_(family_via_member_ids)
                    if family_via_member_ids
                    else False,
                )
            )

        min_family_role = self.ACTION_FAMILY_ROLE_MAP.get(action)
        if min_family_role:
            family_ids = principal.get_scoped_ids_with_role(
                "course_family", min_family_role
            )
            if not family_ids:
                return db.query(self.entity).filter(self.entity.id.in_([]))
            return db.query(self.entity).filter(self.entity.id.in_(family_ids))

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
        if self.check_admin(principal):
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
                # Enforce additional parent context constraints (ignore course_id)
                return self.check_additional_context_permissions(
                    principal, context, exclude_keys=["course_id"]
                )
            # Require maintainer role or above in the target course
            return False
        
        return False
    
    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        if self.check_admin(principal):
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


class ReadOnlyPermissionHandler(PermissionHandler):
    """Permission handler for read-only entities like CourseRole, CourseContentKind"""

    def can_perform_action(
        self,
        principal: Principal,
        action: str,
        resource_id: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> bool:
        # ``context`` is accepted for signature parity with the base
        # ``PermissionHandler.can_perform_action`` and the call site in
        # ``business_logic/crud.py::create_entity`` — read-only entities
        # don't actually consult it. Without this kwarg the create path
        # raised a TypeError for any registered ReadOnly entity.
        if self.check_admin(principal):
            return True

        # Everyone can read these entities
        if action in ["list", "get"]:
            return True

        # Only admin can modify
        return self.check_general_permission(principal, action)

    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        if self.check_admin(principal):
            return db.query(self.entity)

        if action in ["list", "get"]:
            return db.query(self.entity)

        if self.check_general_permission(principal, action):
            return db.query(self.entity)

        raise ForbiddenException(detail={"entity": self.resource_name})


class UserRolePermissionHandler(PermissionHandler):
    """Permission handler for the ``user_role`` junction table.

    Reads are open (every authenticated user can list / get user-role
    assignments). Writes are gated by the standard ``user_role:<action>``
    claim — held by the ``_user_manager`` role today.

    Critical extra rule: even with the claim, non-admins cannot
    create / update / delete a row whose ``role_id`` is ``_admin``.
    Without this, anyone with ``_user_manager`` could grant themselves
    or others the ``_admin`` system role and escalate. Mirrors the
    ``_manager``-can't-promote-to-``_owner`` pattern that landed for
    scoped roles in PR #112.

    The ``context`` dict that ``business_logic/crud.py::create_entity``
    builds from the request payload includes ``role_id`` (any
    ``*_id`` field is folded in), so the create path sees the target
    role before it commits. The ``build_query`` path filters out admin
    rows for non-admins so update / delete URLs that target an admin
    row resolve to ``NotFound`` rather than succeed silently.
    """

    PROTECTED_ROLE_ID = "_admin"

    def can_perform_action(
        self,
        principal: Principal,
        action: str,
        resource_id: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> bool:
        if self.check_admin(principal):
            return True

        if action in ("list", "get"):
            return True

        # Writes require the general claim (typically held by
        # ``_user_manager``).
        if not self.check_general_permission(principal, action):
            return False

        # Even with the claim, only admins may grant ``_admin``.
        if context and context.get("role_id") == self.PROTECTED_ROLE_ID:
            return False

        return True

    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        if self.check_admin(principal):
            return db.query(self.entity)

        if action in ("list", "get"):
            return db.query(self.entity)

        if self.check_general_permission(principal, action):
            # Filter out admin rows so non-admins targeting an
            # admin assignment by (user_id, role_id) get a clean
            # NotFound, not a successful update / delete.
            return db.query(self.entity).filter(
                self.entity.role_id != self.PROTECTED_ROLE_ID
            )

        raise ForbiddenException(detail={"entity": self.resource_name})


class ExamplePermissionHandler(PermissionHandler):
    """Permission handler for Example entities - restricted to lecturers and above.

    Access rules:
    - _lecturer and above: Full read/write access
    - _tutor and _student: NO access
    - Admin: Full access
    """

    ACTION_ROLE_MAP = {
        "get": "_lecturer",
        "list": "_lecturer",
        "create": "_lecturer",
        "update": "_lecturer",
        "delete": "_lecturer",
        "download": "_lecturer",
    }

    def can_perform_action(self, principal: Principal, action: str, resource_id: Optional[str] = None, context: Optional[dict] = None) -> bool:
        if self.check_admin(principal):
            return True

        # Check if user has general permission for this action
        if self.check_general_permission(principal, action):
            return True

        # Check if user has lecturer role in ANY course
        # This allows lecturers to view examples from any course
        min_role = self.ACTION_ROLE_MAP.get(action, "_lecturer")
        courses_with_role = principal.get_courses_with_role(min_role)
        if courses_with_role:  # Has lecturer role in at least one course
            return True

        return False

    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        if self.check_admin(principal):
            return db.query(self.entity)

        if self.check_general_permission(principal, action):
            return db.query(self.entity)

        # Check if user has lecturer role in any course
        min_role = self.ACTION_ROLE_MAP.get(action, "_lecturer")
        courses_with_role = principal.get_courses_with_role(min_role)
        if courses_with_role:  # Has lecturer role in at least one course
            return db.query(self.entity)

        # No access for students or tutors
        raise ForbiddenException(detail={"entity": self.resource_name, "message": "Examples are only accessible to lecturers and above"})


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


class _ScopeMemberPermissionHandler(PermissionHandler):
    """Shared logic for OrganizationMember / CourseFamilyMember handlers.

    Subclasses set:

    * ``SCOPE``  — the claim namespace, e.g. ``"organization"`` /
      ``"course_family"``;
    * ``SCOPE_FK`` — column on the entity pointing to the parent scope,
      e.g. ``"organization_id"``;
    * ``ROLE_FK`` — column on the entity holding the assigned role,
      e.g. ``"organization_role_id"``.

    Permission model:

    * ``_developer``  → read scope only; cannot read/write members.
    * ``_manager``    → read all members of the scope; create / update /
                        delete members whose role is **not** ``_owner``.
                        A manager cannot grant or revoke ``_owner``.
    * ``_owner``      → full CRUD on members, including ``_owner`` rows.

    A user always sees their own membership row regardless of role.

    The ``UPDATE`` path uses a ``custom_permissions`` callable
    (``make_scope_member_custom_permissions`` below) to additionally
    inspect the new-role payload — this prevents a manager from
    promoting an existing membership to ``_owner`` via PATCH, which
    the row-level filter alone would not catch. ``DELETE`` does not
    need the extra hook because ``build_query`` already excludes
    ``_owner`` rows from a manager's deletable set.
    """

    SCOPE: str = ""
    SCOPE_FK: str = ""
    ROLE_FK: str = ""

    def can_perform_action(
        self,
        principal: Principal,
        action: str,
        resource_id: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> bool:
        if self.check_admin(principal):
            return True
        if self.check_general_permission(principal, action):
            return True

        if action == "create":
            ctx = context or {}
            scope_id = ctx.get(self.SCOPE_FK)
            target_role = ctx.get(self.ROLE_FK)
            if not scope_id or not target_role:
                return False
            scope_id = str(scope_id)
            # Owner can assign any role.
            if principal.has_scope_role(self.SCOPE, scope_id, "_owner"):
                return True
            # Manager can assign anything except _owner.
            if (
                principal.has_scope_role(self.SCOPE, scope_id, "_manager")
                and target_role != "_owner"
            ):
                return True
            return False

        if action in ("update", "delete") and resource_id:
            # build_query applies the row-level restriction.
            return True

        if action in ("list", "get"):
            return True

        return False

    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        scope_fk = getattr(self.entity, self.SCOPE_FK)
        role_fk = getattr(self.entity, self.ROLE_FK)

        if self.check_admin(principal):
            return db.query(self.entity)
        if self.check_general_permission(principal, action):
            return db.query(self.entity)

        owner_scopes = principal.get_scoped_ids_with_role(self.SCOPE, "_owner")
        manager_scopes = principal.get_scoped_ids_with_role(self.SCOPE, "_manager")
        # Restrict manager-only set to scopes where principal is NOT owner,
        # so each filter clause stays well-defined.
        manager_only_scopes = manager_scopes - owner_scopes

        if action in ("update", "delete"):
            clauses = []
            if owner_scopes:
                # Owners can edit any row in their scopes.
                clauses.append(scope_fk.in_(owner_scopes))
            if manager_only_scopes:
                # Managers can edit non-_owner rows only.
                clauses.append(
                    and_(
                        scope_fk.in_(manager_only_scopes),
                        role_fk != "_owner",
                    )
                )
            if not clauses:
                return db.query(self.entity).filter(self.entity.id.in_([]))
            return db.query(self.entity).filter(or_(*clauses))

        if action in ("list", "get"):
            # Members of the scope visible to anyone with at least
            # _manager (they need to see the roster). Plus the user's
            # own membership row.
            visible_scopes = owner_scopes | manager_only_scopes
            user_filter = self.entity.user_id == principal.user_id
            if visible_scopes:
                return db.query(self.entity).filter(
                    or_(scope_fk.in_(visible_scopes), user_filter)
                )
            return db.query(self.entity).filter(user_filter)

        raise ForbiddenException(detail={"entity": self.resource_name})


class OrganizationMemberPermissionHandler(_ScopeMemberPermissionHandler):
    SCOPE = "organization"
    SCOPE_FK = "organization_id"
    ROLE_FK = "organization_role_id"


class CourseFamilyMemberPermissionHandler(_ScopeMemberPermissionHandler):
    SCOPE = "course_family"
    SCOPE_FK = "course_family_id"
    ROLE_FK = "course_family_role_id"


def make_scope_member_custom_permissions(
    model: type, scope: str, scope_fk: str, role_fk: str
):
    """Return a ``custom_permissions`` callable for a scoped member entity.

    The build_query filter already restricts which rows a principal can
    delete (a ``_manager`` cannot see ``_owner`` rows), but UPDATE goes
    through ``custom_permissions`` and the row-level filter alone does
    not inspect the *new* role being assigned. This callable closes
    that gap by examining the request payload:

    * Reject the update if the row does not exist (NotFound -> empty).
    * Require the principal to have at least ``_manager`` on the scope.
    * Reject if the row is currently ``_owner`` and the principal is
      not ``_owner`` (a manager cannot demote an owner).
    * Reject if the payload tries to set the role to ``_owner`` and the
      principal is not ``_owner`` (a manager cannot promote to owner).

    Returns a passthrough query that the CRUD layer narrows to ``id``.
    """

    def custom_permissions(
        principal: Principal,
        db: Session,
        id,
        entity,
    ) -> Query:
        if principal.is_admin:
            return db.query(model)

        row = db.query(model).filter(model.id == id).first()
        if row is None:
            return db.query(model).filter(model.id == id)

        scope_id = str(getattr(row, scope_fk))
        current_role = getattr(row, role_fk)

        if not principal.has_scope_role(scope, scope_id, "_manager"):
            raise ForbiddenException(
                detail=(
                    f"You need at least _manager on this {scope} to modify "
                    "its memberships."
                )
            )

        is_scope_owner = principal.has_scope_role(scope, scope_id, "_owner")

        if current_role == "_owner" and not is_scope_owner:
            raise ForbiddenException(
                detail="Only an _owner of this scope can modify an _owner membership."
            )

        new_role = getattr(entity, role_fk, None)
        if new_role is not None and new_role == "_owner" and not is_scope_owner:
            raise ForbiddenException(
                detail="Only an _owner of this scope can grant the _owner role."
            )

        return db.query(model)

    return custom_permissions
