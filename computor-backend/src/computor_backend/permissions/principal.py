import base64
from collections import defaultdict
from typing import Optional, Dict, List, Set, Tuple
from pydantic import BaseModel, model_validator, Field, PrivateAttr
from computor_backend.api.exceptions import NotFoundException
from functools import lru_cache


class CourseRoleHierarchy:
    """Manages course role hierarchy and inheritance"""

    # Default hierarchy - can be made configurable later
    DEFAULT_HIERARCHY = {
        "_owner": ["_owner"],
        "_maintainer": ["_maintainer", "_owner"],
        "_lecturer": ["_lecturer", "_maintainer", "_owner"],
        "_tutor": ["_tutor", "_lecturer", "_maintainer", "_owner"],
        "_student": ["_student", "_tutor", "_lecturer", "_maintainer", "_owner"],
    }

    # Numeric levels for role comparison (higher = more privilege)
    ROLE_LEVELS = {
        "_owner": 5,
        "_maintainer": 4,
        "_lecturer": 3,
        "_tutor": 2,
        "_student": 1,
    }

    def __init__(self, hierarchy: Optional[Dict[str, List[str]]] = None):
        self.hierarchy = hierarchy or self.DEFAULT_HIERARCHY

    @lru_cache(maxsize=128)
    def get_allowed_roles(self, role: str) -> List[str]:
        """Get all roles that meet or exceed the given role"""
        return self.hierarchy.get(role, [])

    def has_role_permission(self, user_role: str, required_role: str) -> bool:
        """Check if user_role has permission for required_role"""
        return user_role in self.get_allowed_roles(required_role)

    def get_role_level(self, role: str) -> int:
        """Get numeric level for a role (higher = more privilege)."""
        return self.ROLE_LEVELS.get(role, 0)

    def can_assign_role(self, assigner_role: str, target_role: str) -> bool:
        """Check if assigner can assign target role (must have equal or higher level)."""
        assigner_level = self.get_role_level(assigner_role)
        target_level = self.get_role_level(target_role)
        return assigner_level >= target_level


# Global instance - can be configured at startup
course_role_hierarchy = CourseRoleHierarchy()


class Claims(BaseModel):
    """Structured claims for permission management"""
    general: Dict[str, Set[str]] = Field(default_factory=dict)
    dependent: Dict[str, Dict[str, Set[str]]] = Field(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True
    
    def has_general_permission(self, resource: str, action: str) -> bool:
        """Check if claims include general permission for resource and action"""
        return resource in self.general and action in self.general[resource]
    
    def has_dependent_permission(self, resource: str, resource_id: str, action: str) -> bool:
        """Check if claims include dependent permission for specific resource instance"""
        return (
            resource in self.dependent and
            resource_id in self.dependent[resource] and
            action in self.dependent[resource][resource_id]
        )
    
    def get_resource_ids_with_action(self, resource: str, action: str) -> Set[str]:
        """Get all resource IDs where user has specific action permission"""
        if resource not in self.dependent:
            return set()
        
        resource_ids = set()
        for resource_id, actions in self.dependent[resource].items():
            if action in actions:
                resource_ids.add(resource_id)
        
        return resource_ids


def build_claims(claim_values: List[Tuple[str, str]]) -> Claims:
    """Build structured claims from claim value tuples"""
    
    general: Dict[str, Set[str]] = defaultdict(set)
    dependent: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
    
    for claim_type, resource_string in claim_values:
        # Only accept standardized "permissions" claim type
        if claim_type is None or claim_type.lower() != "permissions":
            continue
            
        parts = resource_string.split(":")
        
        if len(parts) == 2:
            # General permission: resource:action
            resource, action = parts
            general[resource].add(action)
            
        elif len(parts) == 3:
            # Dependent permission: resource:action:resource_id or resource:role:course_id
            resource, action_or_role, resource_id = parts
            
            # Check if this is a course role claim
            if resource == "course" and action_or_role.startswith("_"):
                # This is a course role claim: course:_role:course_id
                dependent[resource][resource_id].add(action_or_role)
            else:
                # This is a regular dependent claim: resource:action:resource_id
                dependent[resource][resource_id].add(action_or_role)
    
    return Claims(
        general=dict(general),
        dependent=dict(dependent)
    )


class Principal(BaseModel):
    """Enhanced Principal class with improved permission evaluation"""
    
    is_admin: bool = False
    user_id: Optional[str] = None
    
    roles: List[str] = Field(default_factory=list)
    claims: Claims = Field(default_factory=Claims)
    
    # Cache for permission checks (using private attribute)
    _permission_cache: Dict[str, bool] = PrivateAttr(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True
    
    @model_validator(mode='after')
    def set_is_admin_from_roles(self):
        """Automatically set admin flag based on roles"""
        if any(role.endswith("_admin") for role in self.roles):
            self.is_admin = True
        return self
    
    def encode(self) -> bytes:
        """Encode principal for transmission"""
        return base64.b64encode(bytes(self.model_dump_json(), encoding="utf-8"))
    
    def get_user_id(self) -> Optional[str]:
        """Get user ID if available"""
        return self.user_id
    
    def get_user_id_or_throw(self) -> str:
        """Get user ID or raise exception"""
        if self.user_id is None:
            raise NotFoundException("User ID not found")
        return self.user_id
    
    def clear_permission_cache(self):
        """Clear the permission cache"""
        self._permission_cache.clear()
    
    def _cache_key(self, resource: str, action: str, resource_id: Optional[str] = None) -> str:
        """Generate cache key for permission check"""
        return f"{resource}:{action}:{resource_id or ''}"
    
    def has_general_permission(self, resource: str, action: str) -> bool:
        """Check if principal has general permission for resource and action"""
        if self.is_admin:
            return True
        return self.claims.has_general_permission(resource, action)
    
    def has_dependent_permission(self, resource: str, resource_id: str, action: str) -> bool:
        """Check if principal has permission for specific resource instance"""
        if self.is_admin:
            return True
        return self.claims.has_dependent_permission(resource, resource_id, action)
    
    def has_course_role(self, course_id: str, required_role: str) -> bool:
        """Check if user has required role in a course"""
        if self.is_admin:
            return True

        if "course" not in self.claims.dependent:
            return False

        if course_id not in self.claims.dependent["course"]:
            return False

        user_roles = self.claims.dependent["course"][course_id]

        # Check if any of the user's roles in this course meet the requirement
        for user_role in user_roles:
            if user_role.startswith("_") and course_role_hierarchy.has_role_permission(user_role, required_role):
                return True

        return False

    def get_highest_course_role(self, course_id: str) -> Optional[str]:
        """Get the user's highest privilege role in a course.

        Args:
            course_id: The course ID to check

        Returns:
            The highest role (e.g., "_owner", "_lecturer") or None if no role
        """
        if self.is_admin:
            return "_owner"  # Admin has equivalent of owner access

        if "course" not in self.claims.dependent:
            return None

        if course_id not in self.claims.dependent["course"]:
            return None

        user_roles = self.claims.dependent["course"][course_id]
        highest_role = None
        highest_level = 0

        for user_role in user_roles:
            if user_role.startswith("_"):
                level = course_role_hierarchy.get_role_level(user_role)
                if level > highest_level:
                    highest_level = level
                    highest_role = user_role

        return highest_role
    
    def get_courses_with_role(self, minimum_role: str) -> Set[str]:
        """Get all course IDs where user has at least the minimum role"""
        if self.is_admin:
            return set()  # Admin has access to all, return empty to avoid filtering
        
        course_ids = set()
        
        if "course" not in self.claims.dependent:
            return course_ids
        
        allowed_roles = course_role_hierarchy.get_allowed_roles(minimum_role)
        
        for course_id, user_roles in self.claims.dependent["course"].items():
            for user_role in user_roles:
                if user_role in allowed_roles:
                    course_ids.add(course_id)
                    break
        
        return course_ids
    
    def permitted(self, resource: str, action: str | List[str], 
                 resource_id: Optional[str] = None, 
                 course_role: Optional[str] = None) -> bool:
        """
        Enhanced permission check with caching and course role support
        
        Args:
            resource: The resource type (e.g., "user", "course")
            action: Single action or list of actions to check
            resource_id: Specific resource instance ID
            course_role: Required course role (for course-based resources)
        
        Returns:
            True if permission is granted, False otherwise
        """
        
        # Admin bypasses all checks
        if self.is_admin:
            return True
        
        # Handle multiple actions
        if isinstance(action, list):
            return any(self.permitted(resource, a, resource_id, course_role) for a in action)
        
        # Check cache
        cache_key = self._cache_key(resource, action, resource_id)
        if cache_key in self._permission_cache:
            return self._permission_cache[cache_key]
        
        # Perform permission check
        result = False
        
        # Check general permission
        if self.has_general_permission(resource, action):
            result = True
        
        # Check dependent permission
        elif resource_id:
            if course_role:
                # Course-based permission check
                result = self.has_course_role(resource_id, course_role)
            else:
                # Regular dependent permission check
                result = self.has_dependent_permission(resource, resource_id, action)
        
        # Cache result
        self._permission_cache[cache_key] = result
        
        return result


# Backward compatibility functions
def allowed_course_role_ids(course_role_id: Optional[str] = None) -> List[str]:
    """Backward compatibility wrapper for course role hierarchy"""
    if course_role_id is None:
        return []
    return course_role_hierarchy.get_allowed_roles(course_role_id)


def build_claim_actions(claim_values: List[Tuple[str, str]]) -> Claims:
    """Backward compatibility wrapper for building claims"""
    return build_claims(claim_values)
