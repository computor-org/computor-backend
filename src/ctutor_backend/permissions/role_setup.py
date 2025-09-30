"""
Role setup utilities for initializing system roles with claims.

This module contains functions for generating claims for system roles.
These are used during server startup to initialize the permission system.
"""

from typing import Generator, List, Tuple
from ctutor_backend.interface import get_all_dtos
from ctutor_backend.interface.accounts import AccountInterface
from ctutor_backend.interface.course_families import CourseFamilyInterface
from ctutor_backend.interface.courses import CourseInterface
from ctutor_backend.interface.organizations import OrganizationInterface
from ctutor_backend.interface.roles_claims import RoleClaimInterface
from ctutor_backend.interface.user_roles import UserRoleInterface
from ctutor_backend.interface.users import UserInterface
from ctutor_backend.interface.student_profile import StudentProfileInterface
from ctutor_backend.interface.profiles import ProfileInterface
from ctutor_backend.interface.example import ExampleInterface
from ctutor_backend.interface.extensions import ExtensionInterface
from ctutor_backend.model.example import Example


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
