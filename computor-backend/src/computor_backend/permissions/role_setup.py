"""
Role setup utilities for initializing system roles with claims.

This module contains functions for generating claims for system roles.
These are used during server startup to initialize the permission system.
"""

from typing import Generator, List, Tuple
from computor_types import get_all_dtos
from computor_backend.interfaces import (
    AccountInterface,
    CourseFamilyInterface,
    CourseInterface,
    OrganizationInterface,
    RoleClaimInterface,
    UserRoleInterface,
    UserInterface,
    StudentProfileInterface,
    ProfileInterface,
    ExampleInterface,
    ExtensionInterface,
)
from computor_backend.model.example import Example


def get_all_claim_values() -> Generator[Tuple[str, str], None, None]:
    """
    Get all claim values from all DTOs.
    
    Yields:
        Tuples of (claim_type, claim_value) for all registered DTOs
    """
    for dto_class in get_all_dtos():
        for claim in dto_class().claim_values():
            yield claim


def claims_user_manager() -> List[Tuple[str, str]]:
    """
    Generate claims for the user manager role.

    Returns:
        List of (claim_type, claim_value) tuples for user management permissions
    """
    claims = []

    claims.extend(UserInterface().claim_values())
    claims.extend(AccountInterface().claim_values())
    claims.extend(ProfileInterface().claim_values())
    claims.extend(StudentProfileInterface().claim_values())
    claims.extend(RoleClaimInterface().claim_values())
    claims.extend(UserRoleInterface().claim_values())

    return claims


def claims_organization_manager() -> List[Tuple[str, str]]:
    """
    Generate claims for the organization manager role.
    
    Returns:
        List of (claim_type, claim_value) tuples for organization management permissions
    """
    claims = []
    
    claims.extend(OrganizationInterface().claim_values())
    claims.extend(CourseFamilyInterface().claim_values())
    claims.extend(CourseInterface().claim_values())
    claims.extend(ExampleInterface().claim_values())
    claims.extend(ExtensionInterface().claim_values())

    # Add specific example permissions
    claims.extend([
        ("permissions", f"{Example.__tablename__}:get"),
        ("permissions", f"{Example.__tablename__}:list"),
        ("permissions", f"{Example.__tablename__}:create"),
        ("permissions", f"{Example.__tablename__}:upload"),
        ("permissions", f"{Example.__tablename__}:download")
    ])

    return claims


def claims_workspace_user() -> List[Tuple[str, str]]:
    """
    Generate claims for the workspace user role.

    Basic access: view UI, list own workspaces, start/stop own workspaces.
    Cannot provision, delete, or manage other users' workspaces.

    Returns:
        List of (claim_type, claim_value) tuples for workspace access permissions
    """
    return [
        ("permissions", "workspace:access"),       # Gate-keeper: can access coder-ui
        ("permissions", "workspace:list"),          # List own workspaces
        ("permissions", "workspace:start"),         # Start own workspace
        ("permissions", "workspace:stop"),          # Stop own workspace
    ]


def claims_workspace_maintainer() -> List[Tuple[str, str]]:
    """
    Generate claims for the workspace maintainer role.

    Full access: everything a workspace user can do, plus provisioning,
    deleting, managing other users' workspaces, and template management.

    Returns:
        List of (claim_type, claim_value) tuples for workspace maintainer permissions
    """
    return [
        # Includes all workspace user claims
        ("permissions", "workspace:access"),
        ("permissions", "workspace:list"),
        ("permissions", "workspace:start"),
        ("permissions", "workspace:stop"),
        # Maintainer-only claims
        ("permissions", "workspace:provision"),     # Provision new workspaces
        ("permissions", "workspace:delete"),        # Delete workspaces
        ("permissions", "workspace:manage"),        # Query/manage any user's workspaces
        ("permissions", "workspace:session"),       # Create coder sessions
        ("permissions", "workspace:templates"),     # View/manage templates
    ]
