from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from sqlalchemy.orm import Session, Query, aliased
from sqlalchemy import and_, or_, select
from computor_backend.permissions.principal import Principal
from computor_backend.api.exceptions import ForbiddenException


class PermissionHandler(ABC):
    """Base class for entity-specific permission handlers"""
    
    def __init__(self, entity: Type[Any]):
        self.entity = entity
        self.resource_name = entity.__tablename__
    
    @abstractmethod
    def can_perform_action(self, principal: Principal, action: str, resource_id: Optional[str] = None, context: Optional[Dict[str, str]] = None) -> bool:
        """Check if principal can perform an action on a resource.

        Args:
            principal: Current principal
            action: Action to perform (e.g., create, update)
            resource_id: Optional primary context identifier (e.g., course_id)
            context: Optional mapping of context identifiers (e.g., {"course_id": "...", "execution_backend_id": "..."})
        """
        pass
    
    @abstractmethod
    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        """Build a filtered query based on permissions"""
        pass
    
    def check_admin(self, principal: Principal) -> bool:
        """Check if principal has admin privileges"""
        return principal.is_admin
    
    def check_general_permission(self, principal: Principal, action: str) -> bool:
        """Check if principal has general permission for action on this resource"""
        return principal.permitted(self.resource_name, action)
    
    def check_dependent_permission(self, principal: Principal, action: str, resource_id: str) -> bool:
        """Check if principal has specific permission for action on a specific resource"""
        return principal.permitted(self.resource_name, action, resource_id)

    def _has_subject_claims(self, principal: Principal, subject: str) -> bool:
        """Check if any claims exist for a subject (general or dependent)."""
        general = principal.claims.general or {}
        dependent = principal.claims.dependent or {}
        return subject in general or subject in dependent

    def check_additional_context_permissions(
        self,
        principal: Principal,
        context: Optional[Dict[str, str]],
        exclude_keys: Optional[list[str]] = None,
        allowed_actions: Optional[list[str]] = None,
    ) -> bool:
        """Check permissions for additional parent context identifiers.

        Enforces that, for each extra context key (e.g., execution_backend_id), if the
        principal has any claims for that subject, then one of the allowed actions must
        be permitted (general or dependent) for that subject. Subjects are derived by
        stripping the trailing `_id` from the key (e.g., `execution_backend_id` → `execution_backend`).

        If the principal has no claims for that subject at all, the check is skipped
        for backward compatibility (treat as not applicable).
        """
        if not context:
            return True
        exclude = set(exclude_keys or [])
        actions = allowed_actions or ["create", "update", "use", "link", "assign", "get"]
        for key, value in context.items():
            if key in exclude or not key.endswith("_id"):
                continue
            subject = key[:-3]
            if not self._has_subject_claims(principal, subject):
                # No claims for this subject → ignore constraint
                continue
            # Require permission on this subject; prefer dependent check by id
            if value and principal.permitted(subject, actions, str(value)):
                continue
            # Fallback to any general permission
            if principal.permitted(subject, actions):
                continue
            return False
        return True


class PermissionRegistry:
    """Registry for managing entity permission handlers"""
    
    _instance = None
    _handlers: Dict[Type[Any], PermissionHandler] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def register(self, entity: Type[Any], handler: PermissionHandler):
        """Register a permission handler for an entity"""
        self._handlers[entity] = handler
    
    def get_handler(self, entity: Type[Any]) -> Optional[PermissionHandler]:
        """Get the permission handler for an entity"""
        return self._handlers.get(entity)
    
    def check_permissions(self, principal: Principal, entity: Type[Any], action: str, db: Session) -> Query:
        """Check permissions and return filtered query"""
        handler = self.get_handler(entity)
        if not handler:
            # Fallback to admin-only if no handler registered
            if not principal.is_admin:
                raise ForbiddenException(detail={"entity": entity.__tablename__})
            return db.query(entity)
        
        return handler.build_query(principal, action, db)


# Global registry instance
permission_registry = PermissionRegistry()
