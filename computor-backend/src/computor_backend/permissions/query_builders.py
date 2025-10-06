from typing import List, Type, Any
from sqlalchemy.orm import Session, Query, aliased
from sqlalchemy import or_, select
from computor_backend.model.course import Course, CourseMember
from computor_backend.permissions.principal import course_role_hierarchy
from computor_backend.model.auth import User
from computor_backend.model.course import CourseContent
import asyncio
import logging

logger = logging.getLogger(__name__)

class CoursePermissionQueryBuilder:
    """Utility class for building course-related permission queries"""
    
    @classmethod
    def get_allowed_roles(cls, minimum_role: str) -> List[str]:
        """Get all roles that meet or exceed the minimum required role"""
        # Delegate to the shared course role hierarchy to avoid drift
        return course_role_hierarchy.get_allowed_roles(minimum_role)
    
    @classmethod
    def user_courses_subquery(cls, user_id: str, minimum_role: str, db: Session):
        """
        Create a subquery for courses where user has at least the minimum role.

        PERFORMANCE NOTE: This method builds a SQL subquery. For better performance
        in async contexts, consider using the cached version:
        `user_courses_subquery_cached()` which uses Redis caching.

        Args:
            user_id: User identifier
            minimum_role: Minimum required role
            db: SQLAlchemy session

        Returns:
            SQLAlchemy select subquery
        """
        cm_alias = aliased(CourseMember)

        return select(cm_alias.course_id).where(
            cm_alias.user_id == user_id,
            cm_alias.course_role_id.in_(cls.get_allowed_roles(minimum_role))
        )

    @classmethod
    def user_courses_subquery_cached(cls, user_id: str, minimum_role: str, db: Session):
        """
        Create a subquery using CACHED course memberships (RECOMMENDED).

        This version uses Redis caching for significantly better performance.
        Falls back to database query if cache is unavailable.

        Args:
            user_id: User identifier
            minimum_role: Minimum required role
            db: SQLAlchemy session

        Returns:
            SQLAlchemy select with course IDs (cached when possible)
        """
        try:
            # Try to use cached version
            from computor_backend.permissions.cache import get_user_courses_with_role

            # Get cached course IDs
            course_ids = asyncio.run(get_user_courses_with_role(
                user_id,
                minimum_role,
                db,
                cls.get_allowed_roles
            ))

            if course_ids:
                # Return a select that matches these specific course IDs
                # This is much faster than a subquery join
                logger.debug(f"Using cached course list ({len(course_ids)} courses) for user {user_id}")
                return select(Course.id).where(Course.id.in_(course_ids))

        except Exception as e:
            logger.warning(f"Cache lookup failed, falling back to DB query: {e}")

        # Fallback to standard subquery if cache fails
        return cls.user_courses_subquery(user_id, minimum_role, db)
    
    @classmethod
    def filter_by_course_membership(cls, query: Query, entity: Type[Any], 
                                   user_id: str, minimum_role: str, 
                                   db: Session) -> Query:
        """Filter query based on course membership"""
        subquery = cls.user_courses_subquery(user_id, minimum_role, db)
        
        # Check which foreign key the entity has
        table_keys = entity.__table__.columns.keys()

        if entity.__tablename__ == Course.__tablename__:
            return query.filter(entity.id.in_(subquery))
        
        elif "course_id" in table_keys:
            # Direct course relationship
            return query.filter(entity.course_id.in_(subquery))
        
        elif "course_content_id" in table_keys:
            # Indirect through CourseContent
            return (
                query.join(CourseContent, CourseContent.id == entity.course_content_id)
                .filter(CourseContent.course_id.in_(subquery))
            )
        
        elif "course_member_id" in table_keys:
            # Indirect through CourseMember
            return (
                query.join(CourseMember, CourseMember.id == entity.course_member_id)
                .filter(CourseMember.course_id.in_(subquery))
            )
        
        return query
    
    @classmethod
    def build_course_filtered_query(cls, entity: Type[Any], user_id: str,
                                   minimum_role: str, db: Session) -> Query:
        """Build a query filtered by course membership"""
        cm_other = aliased(CourseMember)
        
        # Check if entity is Course or has course_id
        if entity.__name__ == 'Course':
            # For Course entity, use id field
            subquery = cls.user_courses_subquery(user_id, minimum_role, db)
            query = (
                db.query(entity)
                .select_from(User)
                .outerjoin(cm_other, cm_other.user_id == User.id)
                .outerjoin(entity, entity.id == cm_other.course_id)
                .filter(
                    cm_other.course_id.in_(subquery)
                )
            )
        else:
            # For other entities with course_id field
            subquery = cls.user_courses_subquery(user_id, minimum_role, db)
            query = (
                db.query(entity)
                .select_from(User)
                .outerjoin(cm_other, cm_other.user_id == User.id)
                .outerjoin(entity, entity.course_id == cm_other.course_id)
                .filter(
                    cm_other.course_id.in_(subquery)
                )
            )
        
        return query


class OrganizationPermissionQueryBuilder:
    """Utility class for building organization-related permission queries"""
    
    @classmethod
    def filter_by_course_organization(cls, entity: Type[Any], user_id: str,
                                     minimum_role: str, db: Session) -> Query:
        """Filter organizations based on course membership"""
        cm_other = aliased(CourseMember)
        
        subquery = CoursePermissionQueryBuilder.user_courses_subquery(user_id, minimum_role, db)
        
        query = (
            db.query(entity)
            .select_from(User)
            .outerjoin(cm_other, cm_other.user_id == User.id)
            .outerjoin(Course, cm_other.course_id == Course.id)
            .outerjoin(entity, entity.id == Course.organization_id)
            .filter(
                cm_other.course_id.in_(subquery)
            )
        )
        
        return query


class UserPermissionQueryBuilder:
    """Utility class for building user-related permission queries"""
    
    @classmethod
    def filter_visible_users(cls, user_id: str, db: Session) -> Query:
        """Filter users that are visible to the current user"""
        cm_other = aliased(CourseMember)
        
        # Get the subquery for courses where user is at least a tutor
        subquery = CoursePermissionQueryBuilder.user_courses_subquery(user_id, "_tutor", db)
        
        # User can see themselves and other users in courses where they're at least a tutor
        query = (
            db.query(User)
            .outerjoin(cm_other, cm_other.user_id == User.id)
            .filter(
                or_(
                    User.id == user_id,
                    cm_other.course_id.in_(subquery)
                )
            )
            .distinct()
        )
        
        return query
