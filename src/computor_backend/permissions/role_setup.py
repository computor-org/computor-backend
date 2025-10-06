"""
Role setup utilities for initializing system roles with claims.

This module contains functions for generating claims for system roles.
These are used during server startup to initialize the permission system.
"""

from typing import Generator, List, Tuple
from computor_types import get_all_dtos
from computor_types.accounts import AccountInterface
from computor_types.course_families import CourseFamilyInterface
from computor_types.courses import CourseInterface
from computor_types.organizations import OrganizationInterface
from computor_types.roles_claims import RoleClaimInterface
from computor_types.user_roles import UserRoleInterface
from computor_types.users import UserInterface
from computor_types.student_profile import StudentProfileInterface
from computor_types.profiles import ProfileInterface
from computor_types.example import ExampleInterface
from computor_types.extensions import ExtensionInterface
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
