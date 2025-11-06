from typing import Optional
from sqlalchemy.orm import Session, Query
from computor_backend.permissions.handlers import PermissionHandler
from computor_backend.permissions.query_builders import (
    CoursePermissionQueryBuilder, 
    OrganizationPermissionQueryBuilder,
    UserPermissionQueryBuilder
)
from computor_backend.permissions.principal import Principal
from computor_backend.api.exceptions import ForbiddenException
from computor_backend.model.auth import User
from computor_backend.model.course import Course, CourseMember, CourseContentType
from computor_backend.model.message import Message


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

            # For update/delete, user managers cannot modify admins or service accounts
            if action in ["update", "delete"] and resource_id:
                from computor_backend.model.auth import User
                from computor_backend.model.role import UserRole
                from computor_backend.database import SessionLocal

                # Need to check the target user in the database
                # This requires a database query, which is handled in build_query
                # For can_perform_action with resource_id, we return True here
                # and do the actual check in build_query
                return True

        # Users can view themselves
        if action in ["list", "get"] and resource_id == principal.user_id:
            return True

        return False
    
    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        from computor_backend.model.role import UserRole
        from sqlalchemy import and_, not_, exists

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
    """Permission handler for Organization entity"""
    
    ACTION_ROLE_MAP = {
        "get": "_student",
        "list": "_student",
        "update": None,  # Only through general permission
        "create": None,  # Only through general permission
        "delete": None   # Only through general permission
    }
    
    def can_perform_action(self, principal: Principal, action: str, resource_id: Optional[str] = None, context: Optional[dict] = None) -> bool:
        if self.check_admin(principal):
            return True
        
        if self.check_general_permission(principal, action):
            return True
        
        # Users can view organizations of courses they're in
        if action in ["get", "list"]:
            return True  # Will be filtered by query
        
        return False
    
    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        if self.check_admin(principal):
            return db.query(self.entity)
        
        if self.check_general_permission(principal, action):
            return db.query(self.entity)
        
        min_role = self.ACTION_ROLE_MAP.get(action)
        if min_role:
            return OrganizationPermissionQueryBuilder.filter_by_course_organization(
                self.entity, principal.user_id, min_role, db
            )
        
        raise ForbiddenException(detail={"entity": self.resource_name})


class CourseFamilyPermissionHandler(PermissionHandler):
    """Permission handler for CourseFamily entity"""
    
    ACTION_ROLE_MAP = {
        "get": "_student",
        "list": "_student",
        "update": None,  # Only through general permission
        "create": None,  # Only through general permission
        "delete": None   # Only through general permission
    }
    
    def can_perform_action(self, principal: Principal, action: str, resource_id: Optional[str] = None, context: Optional[dict] = None) -> bool:
        if self.check_admin(principal):
            return True
        
        if self.check_general_permission(principal, action):
            return True
        
        if action in ["get", "list"]:
            return True  # Will be filtered by query
        
        return False
    
    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        if self.check_admin(principal):
            return db.query(self.entity)
        
        if self.check_general_permission(principal, action):
            return db.query(self.entity)
        
        min_role = self.ACTION_ROLE_MAP.get(action)
        if min_role:
            from sqlalchemy.orm import aliased
            from sqlalchemy import select
            
            cm_other = aliased(CourseMember)
            
            subquery = CoursePermissionQueryBuilder.user_courses_subquery(
                principal.user_id, min_role, db
            )
            
            query = (
                db.query(self.entity)
                .select_from(User)
                .outerjoin(cm_other, cm_other.user_id == User.id)
                .outerjoin(Course, cm_other.course_id == Course.id)
                .outerjoin(self.entity, self.entity.id == Course.course_family_id)
                .filter(
                    cm_other.course_id.in_(subquery)
                )
            )
            
            return query
        
        raise ForbiddenException(detail={"entity": self.resource_name})


class CourseContentTypePermissionHandler(PermissionHandler):
    
    def _check_role_hierarchy(self, user_roles: set, required_role: str) -> bool:
        """Check if user roles meet the required role in hierarchy"""
        from computor_backend.permissions.principal import course_role_hierarchy
        
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
            # in at least one course that uses this content type
            from sqlalchemy.orm import aliased
            from sqlalchemy import select, exists
            
            # For read operations, return all content types if user has any course membership
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
        "delete": "_lecturer"
    }
    
    def can_perform_action(self, principal: Principal, action: str, resource_id: Optional[str] = None, context: Optional[dict] = None) -> bool:
        if self.check_admin(principal):
            return True
        
        if self.check_general_permission(principal, action):
            return True
        
        # Check course-based permissions
        if action in self.ACTION_ROLE_MAP:
            min_role = self.ACTION_ROLE_MAP[action]
            # For create/update/delete, require course context to match the specific course
            if action in ["create", "update", "delete"]:
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
            from sqlalchemy.orm import aliased
            from sqlalchemy import select
            
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
            from sqlalchemy.orm import aliased
            from sqlalchemy import or_, and_, select
            
            cm_other = aliased(CourseMember)
            
            # Base visibility: courses where user meets minimum role
            base_filter = cm_other.course_id.in_(
                CoursePermissionQueryBuilder.user_courses_subquery(
                    principal.user_id, min_role, db
                )
            )

            filters = [base_filter]
            # For read actions, also allow the current student's own membership row
            if action in ["get", "list"]:
                filters.append(
                    and_(
                        User.id == principal.user_id,
                        cm_other.course_role_id == "_student",
                        self.entity.id == cm_other.id
                    )
                )

            query = (
                db.query(self.entity)
                .select_from(User)
                .outerjoin(cm_other, cm_other.user_id == User.id)
                .outerjoin(self.entity, self.entity.course_id == cm_other.course_id)
                .filter(or_(*filters))
            )
            
            return query
        
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
        from computor_backend.model.result import Result
        from computor_backend.model.course import CourseContent, CourseMember, SubmissionGroupMember
        from sqlalchemy.orm import aliased
        from sqlalchemy import or_, and_
        
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
            
            # Students can only see their own results
            if "_student" in min_role:
                # Filter for results belonging to the user's course member
                query = query.join(
                    CourseMember, 
                    and_(
                        CourseMember.course_id == CourseContent.course_id,
                        CourseMember.user_id == principal.user_id
                    )
                ).filter(
                    or_(
                        Result.course_member_id == CourseMember.id,
                        # Also include results from submission groups the user belongs to
                        Result.submission_group_id.in_(
                            db.query(SubmissionGroupMember.submission_group_id)
                            .filter(SubmissionGroupMember.course_member_id == CourseMember.id)
                        )
                    )
                )
            else:
                # For tutors/lecturers, filter by course membership with appropriate role
                query = query.filter(
                    CourseContent.course_id.in_(
                        CoursePermissionQueryBuilder.user_courses_subquery(
                            principal.user_id, min_role, db
                        )
                    )
                )
            
            return query
        
        raise ForbiddenException(detail={"entity": self.resource_name})


class ReadOnlyPermissionHandler(PermissionHandler):
    """Permission handler for read-only entities like CourseRole, CourseContentKind"""
    
    def can_perform_action(self, principal: Principal, action: str, resource_id: Optional[str] = None) -> bool:
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
    """Permission handler for Message entity with multi-context visibility.

    Visibility and write rules:
    - user_id: Readable between user_id and author_id. Write not implemented.
    - course_member_id: Readable between course_member_id and author_id. Write not implemented.
    - submission_group_id: Read and write for submission_group_members and course roles except _student.
    - course_group_id: Readable for course_members in the course_group. Write not allowed.
    - course_content_id: Readable for submission_group_members with the course_content.
    - course_id: Readable for all course_members in the course.
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
        from sqlalchemy import or_, and_
        from computor_backend.permissions.query_builders import CoursePermissionQueryBuilder
        from computor_backend.model.course import SubmissionGroupMember, CourseGroup, CourseMember, SubmissionGroup, CourseContent

        base = db.query(self.entity)

        if self.check_admin(principal):
            return base

        filters = []

        # Author can always access their own messages
        filters.append(self.entity.author_id == principal.user_id)

        # user_id: Readable between user_id and author_id
        # Messages where the user is the target user
        filters.append(self.entity.user_id == principal.user_id)

        # course_member_id: Readable between course_member_id's user and author_id
        # Messages where the user owns the course member
        cm_ids_subq = db.query(CourseMember.id).filter(CourseMember.user_id == principal.user_id)
        filters.append(self.entity.course_member_id.in_(cm_ids_subq))

        # submission_group_id: Readable for all submission_group_members and all course roles except _student
        # Messages in submission groups the user belongs to
        sgm_subq = (
            db.query(SubmissionGroupMember.submission_group_id)
            .join(CourseMember, CourseMember.id == SubmissionGroupMember.course_member_id)
            .filter(CourseMember.user_id == principal.user_id)
        )
        filters.append(self.entity.submission_group_id.in_(sgm_subq))

        # course_group_id: Readable for all course_members in the course_group
        # Messages in course groups the user belongs to
        cg_subq = (
            db.query(CourseMember.course_group_id)
            .filter(
                CourseMember.user_id == principal.user_id,
                CourseMember.course_group_id.isnot(None)
            )
        )
        filters.append(self.entity.course_group_id.in_(cg_subq))

        # course_content_id: Readable for all course members in courses containing the content
        # Students can see course_content messages for any content in their enrolled courses
        # (not just content where they have a submission group - units don't have submission groups)
        user_course_contents_subq = (
            db.query(CourseContent.id)
            .join(CourseMember, CourseMember.course_id == CourseContent.course_id)
            .filter(CourseMember.user_id == principal.user_id)
        )
        filters.append(self.entity.course_content_id.in_(user_course_contents_subq))

        # course_id: Readable for all course_members in the course
        # Messages in courses the user is a member of
        course_ids_subq = (
            db.query(CourseMember.course_id)
            .filter(CourseMember.user_id == principal.user_id)
        )
        filters.append(self.entity.course_id.in_(course_ids_subq))

        # Tutors/lecturers: include messages in courses where principal has elevated role
        # This provides additional access for non-student roles
        permitted_courses = CoursePermissionQueryBuilder.user_courses_subquery(principal.user_id, "_tutor", db)
        if permitted_courses is not None:
            # Additional access for tutors/lecturers to all message types in their courses

            # course_member_id messages in their courses
            filters.append(
                self.entity.course_member_id.in_(
                    db.query(CourseMember.id).filter(CourseMember.course_id.in_(permitted_courses))
                )
            )
            # submission_group_id messages in their courses
            filters.append(
                self.entity.submission_group_id.in_(
                    db.query(SubmissionGroup.id).filter(SubmissionGroup.course_id.in_(permitted_courses))
                )
            )
            # course_group_id messages in their courses
            filters.append(
                self.entity.course_group_id.in_(
                    db.query(CourseGroup.id).filter(CourseGroup.course_id.in_(permitted_courses))
                )
            )
            # course_content_id messages in their courses
            filters.append(
                self.entity.course_content_id.in_(
                    db.query(CourseContent.id).filter(CourseContent.course_id.in_(permitted_courses))
                )
            )
            # course_id messages in their courses (already covered above but kept for clarity)
            filters.append(
                self.entity.course_id.in_(permitted_courses)
            )

        query = base.filter(or_(*filters))

        # For update/delete, restrict to author only (non-admin)
        # Additionally, check that the message target allows writing
        if action in ["update", "delete"]:
            query = query.filter(self.entity.author_id == principal.user_id)
            # Prevent update/delete of messages with user_id or course_member_id targets
            query = query.filter(
                and_(
                    self.entity.user_id.is_(None),
                    self.entity.course_member_id.is_(None),
                    self.entity.course_group_id.is_(None)  # course_group_id is read-only
                )
            )

        return query
