"""
CLI commands for deployment operations.

This module provides commands for working with ComputorDeploymentConfig,
including generating example configurations and deploying hierarchies.
"""

import sys
import io
import os
import base64
import zipfile
import yaml
import click
from pathlib import Path
from typing import Any

from computor_types.deployments_refactored import (
    ComputorDeploymentConfig,
    HierarchicalOrganizationConfig,
    HierarchicalCourseFamilyConfig,
    HierarchicalCourseConfig,
    GitLabConfig,
    ExecutionBackendConfig,
    ExecutionBackendReference,
    ServiceConfig,
    ServiceReference,
    ServiceUserConfig,
    ServiceApiTokenConfig,
    CourseProjects,
    CourseContentConfig,
    EXAMPLE_DEPLOYMENT,
    EXAMPLE_MULTI_DEPLOYMENT
)
from computor_cli.auth import authenticate, get_computor_client
from computor_cli.config import CLIAuthConfig
from computor_types.users import UserCreate, UserQuery
from computor_types.accounts import AccountCreate, AccountQuery
from computor_types.courses import CourseQuery
from computor_types.course_members import CourseMemberCreate, CourseMemberQuery
from computor_types.course_groups import CourseGroupQuery, CourseGroupCreate
from computor_types.organizations import OrganizationQuery
from computor_types.course_families import CourseFamilyQuery
# Execution backends removed - migrated to services architecture
from computor_types.services import ServiceCreate, ServiceUpdate
from computor_types.service_type import ServiceTypeQuery
from computor_types.api_tokens import ApiTokenCreate
from computor_types.roles import RoleQuery
from computor_types.user_roles import UserRoleCreate, UserRoleQuery
from computor_types.example import (
    ExampleRepositoryCreate,
    ExampleRepositoryQuery,
    ExampleQuery,
)
from computor_types.course_contents import CourseContentCreate, CourseContentQuery
from computor_types.course_content_types import CourseContentTypeQuery, CourseContentTypeCreate
from computor_types.course_content_kind import CourseContentKindQuery
from computor_utils.vsix_utils import parse_vsix_metadata
from computor_types.exceptions import VsixManifestError
# Deployment is handled through course-contents API, not a separate deployment endpoint

from computor_cli.utils import run_async


class SyncHTTPWrapper:
    """Wrapper to make sync HTTP calls using ComputorClient's httpx client configuration."""

    def __init__(self, computor_client):
        """Initialize with a ComputorClient instance."""
        import httpx

        # Build headers including auth token if available
        headers = dict(computor_client._http._default_headers)
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"
        if computor_client._auth_provider.is_authenticated():
            token = computor_client._auth_provider._access_token
            if token:
                headers["Authorization"] = f"Bearer {token}"

        self._client = httpx.Client(
            base_url=computor_client._http.base_url,
            headers=headers,
            timeout=httpx.Timeout(computor_client._http.timeout)
        )

    def get(self, path: str, params: dict = None):
        """GET request."""
        response = self._client.get(path, params=params)
        response.raise_for_status()
        return response.json() if response.content else None

    def list(self, path: str, params: dict = None):
        """GET request (alias for get) with optional query parameters."""
        return self.get(path, params=params)

    def create(self, path: str, data: dict = None):
        """POST request."""
        response = self._client.post(path, json=data or {})
        response.raise_for_status()
        return response.json() if response.content else None

    def update(self, path: str, data: dict = None):
        """PATCH request."""
        response = self._client.patch(path, json=data or {})
        response.raise_for_status()
        return response.json() if response.content else None

    def __del__(self):
        """Close client on deletion."""
        if hasattr(self, '_client'):
            self._client.close()


@click.group()
def deployment():
    """Manage deployment configurations and operations."""
    pass


# Note: Default service token scopes are now managed by the backend in:
# computor_backend/business_logic/api_tokens.py - DEFAULT_SERVICE_SCOPES
# The backend automatically assigns appropriate scopes based on service type (testing, worker, review, etc.)
# when scopes=None is passed to token creation endpoints.


@deployment.command()
@click.option(
    '--output', '-o',
    type=click.Path(),
    default='deployment.yaml',
    help='Output file path for the example deployment configuration'
)
@click.option(
    '--format', '-f',
    type=click.Choice(['minimal', 'full', 'tutorial']),
    default='tutorial',
    help='Type of example to generate'
)
def init(output: str, format: str):
    """
    Generate an example deployment configuration file.
    
    This creates a template YAML file that can be customized for your deployment.
    """
    click.echo(f"Generating {format} deployment configuration...")
    
    if format == 'minimal':
        # Minimal configuration with only required fields
        config = ComputorDeploymentConfig(
            organizations=[
                HierarchicalOrganizationConfig(
                    name="My Organization",
                    path="my-org",
                    course_families=[
                        HierarchicalCourseFamilyConfig(
                            name="My Courses",
                            path="my-courses",
                            courses=[
                                HierarchicalCourseConfig(
                                    name="My First Course",
                                    path="course-2025"
                                )
                            ]
                        )
                    ]
                )
            ]
        )
    elif format == 'full':
        # Use the multi-organization example
        config = EXAMPLE_MULTI_DEPLOYMENT
    else:  # tutorial
        # Use the example from deployments_refactored.py
        config = EXAMPLE_DEPLOYMENT
    
    # Write to file
    output_path = Path(output)
    yaml_content = config.get_deployment()
    
    # Add helpful comments to the YAML
    header_comments = """# Computor Deployment Configuration
# This file defines the organization -> course family -> course hierarchy
# 
# Environment variables can be used with ${VAR_NAME} or ${VAR_NAME:-default}
# 
# Required fields:
#   - organization.name, organization.path
#   - course_family.name, course_family.path  
#   - course.name, course.path
#
# Optional: GitLab configuration, execution backends, settings
#
"""
    
    with open(output_path, 'w') as f:
        f.write(header_comments)
        f.write(yaml_content)
    
    click.echo(f"✅ Created deployment configuration: {output_path}")
    click.echo(f"\nNext steps:")
    click.echo(f"1. Edit {output_path} to customize your deployment")
    click.echo(f"2. Set required environment variables (e.g., GITLAB_TOKEN)")
    click.echo(f"3. Run: ctutor deployment apply {output_path}")


def _deploy_users(config: ComputorDeploymentConfig, auth: CLIAuthConfig):
    """Deploy users and their course memberships from configuration."""

    client = run_async(get_computor_client(auth))

    # Get API clients
    user_client = client.users  # Note: users (plural) for CRUD, user (singular) for current user
    account_client = client.accounts
    course_client = client.courses
    course_member_client = client.course_members
    course_group_client = client.course_groups
    org_client = client.organizations
    family_client = client.course_families

    processed_users = []
    failed_users = []

    for user_deployment in config.users:
        user_dep = user_deployment.user
        click.echo(f"\n👤 Processing: {user_dep.display_name} ({user_dep.username})")

        try:
            # Check if user already exists by email or username
            existing_users = []
            if user_dep.email:
                existing_users.extend(run_async(user_client.list(UserQuery(email=user_dep.email))))

            # Also check by username if not found by email
            if not existing_users and user_dep.username:
                existing_users.extend(run_async(user_client.list(UserQuery(username=user_dep.username))))
            
            if existing_users:
                user = existing_users[0]
                click.echo(f"  ℹ️  User already exists: {user.display_name}")
            else:
                # Create new user
                user_create = UserCreate(
                    given_name=user_dep.given_name,
                    family_name=user_dep.family_name,
                    email=user_dep.email,
                    number=user_dep.number,
                    username=user_dep.username,
                    user_type=user_dep.user_type,
                    properties=user_dep.properties
                )
                
                user = run_async(user_client.create(user_create))
                click.echo(f"  ✅ Created user: {user.display_name}")
                
            # Assign system roles if provided
            if user_dep.roles:
                role_client = client.roles
                # user_roles methods are on client.user, not a separate client
                user_client_current = client.user

                for role_id in user_dep.roles:
                    try:
                        # Check if role exists
                        roles = run_async(role_client.list(RoleQuery(id=role_id)))
                        if not roles:
                            click.echo(f"  ⚠️  Role not found: {role_id}")
                            continue

                        # Check if user already has this role
                        # Use kwargs to pass query params since user_roles() uses **kwargs
                        existing_user_roles = run_async(user_client_current.user_roles(
                            user_id=str(user.id),
                            role_id=role_id
                        ))

                        if existing_user_roles:
                            click.echo(f"  ℹ️  User already has role: {role_id}")
                        else:
                            # Assign role to user
                            user_role_create = UserRoleCreate(
                                user_id=str(user.id),
                                role_id=role_id
                            )
                            run_async(user_client_current.post_user_roles(user_role_create))
                            click.echo(f"  ✅ Assigned role: {role_id}")
                    except Exception as e:
                        click.echo(f"  ⚠️  Failed to assign role {role_id}: {e}")
                
            # Set password if provided
            if user_dep.password:
                try:
                    import httpx
                    password_payload = {
                        "username": user_dep.username,
                        "password": user_dep.password
                    }
                    # Use direct HTTP call since client doesn't have this method
                    # Build headers with auth token
                    headers = dict(client._http._default_headers)
                    headers["Content-Type"] = "application/json"
                    if client._auth_provider.is_authenticated():
                        token = client._auth_provider._access_token
                        if token:
                            headers["Authorization"] = f"Bearer {token}"
                    with httpx.Client(base_url=client._http.base_url, headers=headers) as sync_client:
                        response = sync_client.post("user/password", json=password_payload)
                        response.raise_for_status()
                    click.echo(f"  ✅ Set password for user: {user.display_name}")
                except Exception as e:
                    click.echo(f"  ⚠️  Failed to set password: {e}")
            
            # Create accounts
            for account_dep in user_deployment.accounts:
                # Check if account already exists for this user
                existing_accounts = run_async(account_client.list(AccountQuery(
                    provider_account_id=account_dep.provider_account_id,
                    user_id=str(user.id)
                )))
                
                if existing_accounts:
                    click.echo(f"  Account already exists: {account_dep.type} @ {account_dep.provider}")
                else:
                    # Create new account
                    account_create = AccountCreate(
                        provider=account_dep.provider,
                        type=account_dep.type,
                        provider_account_id=account_dep.provider_account_id,
                        user_id=str(user.id),
                        properties=account_dep.properties or {}
                    )
                    
                    run_async(account_client.create(account_create))
                    click.echo(f"  ✅ Created account: {account_dep.type} @ {account_dep.provider}")
            
            # Create course memberships
            for cm_dep in user_deployment.course_members:
                try:
                    course = None
                    
                    # Resolve course by path or ID
                    if cm_dep.is_path_based:
                        # Find organization
                        orgs = run_async(org_client.list(OrganizationQuery(path=cm_dep.organization)))
                        if not orgs:
                            click.echo(f"  ⚠️  Organization not found: {cm_dep.organization}")
                            continue
                        org = orgs[0]
                        
                        # Find course family
                        families = run_async(family_client.list(CourseFamilyQuery(
                            organization_id=str(org.id),
                            path=cm_dep.course_family
                        )))
                        if not families:
                            click.echo(f"  ⚠️  Course family not found: {cm_dep.course_family}")
                            continue
                        family = families[0]
                        
                        # Find course
                        courses = run_async(course_client.list(CourseQuery(
                            course_family_id=str(family.id),
                            path=cm_dep.course
                        )))
                        if not courses:
                            click.echo(f"  ⚠️  Course not found: {cm_dep.course}")
                            continue
                        course = courses[0]
                    
                    elif cm_dep.is_id_based:
                        # Direct course lookup by ID
                        course = run_async(course_client.get(cm_dep.id))
                        if not course:
                            click.echo(f"  ⚠️  Course not found: {cm_dep.id}")
                            continue
                    
                    if course:
                        # Handle course group for students
                        course_group_id = None
                        if cm_dep.role == "_student" and cm_dep.group:
                            # Find or create course group
                            groups = run_async(course_group_client.list(CourseGroupQuery(
                                course_id=str(course.id),
                                title=cm_dep.group
                            )))
                            if groups:
                                course_group_id = str(groups[0].id)
                                click.echo(f"  Using existing group: {cm_dep.group}")
                            else:
                                # Create the course group
                                try:
                                    group_create = CourseGroupCreate(
                                        title=cm_dep.group,
                                        description=f"Course group {cm_dep.group}",
                                        course_id=str(course.id)
                                    )
                                    new_group = run_async(course_group_client.create(group_create))
                                    course_group_id = str(new_group.id)
                                    click.echo(f"  ✅ Created course group: {cm_dep.group}")
                                except Exception as e:
                                    click.echo(f"  ⚠️  Failed to create course group {cm_dep.group}: {e}")
                                    continue
                        
                        # Check if course member already exists
                        existing_members = run_async(course_member_client.list(CourseMemberQuery(
                            user_id=str(user.id),
                            course_id=str(course.id)
                        )))
                        
                        if existing_members:
                            existing_member = existing_members[0]
                            # Check if we need to update role or group
                            needs_update = False
                            if existing_member.course_role_id != cm_dep.role:
                                click.echo(f"  Updating role from {existing_member.course_role_id} to {cm_dep.role}")
                                needs_update = True
                            if course_group_id and existing_member.course_group_id != course_group_id:
                                click.echo(f"  Updating group assignment")
                                needs_update = True
                            
                            if needs_update:
                                # Update existing member
                                member_update = {
                                    'course_role_id': cm_dep.role,
                                    'course_group_id': course_group_id
                                }
                                run_async(course_member_client.update(str(existing_member.id), member_update))
                                click.echo(f"  ✅ Updated course membership: {course.path} as {cm_dep.role}")
                            else:
                                click.echo(f"  Already member of course: {course.path} as {cm_dep.role}")
                        else:
                            # Create new course member
                            member_create = CourseMemberCreate(
                                user_id=str(user.id),
                                course_id=str(course.id),
                                course_role_id=cm_dep.role,
                                course_group_id=course_group_id
                            )
                            
                            run_async(course_member_client.create(member_create))
                            click.echo(f"  ✅ Added to course: {course.path} as {cm_dep.role}")
                        
                except Exception as e:
                    click.echo(f"  ⚠️  Failed to add course membership: {e}")
            
            processed_users.append(user_dep)
            
        except Exception as e:
            click.echo(f"  ❌ Failed to process user: {e}")
            failed_users.append(user_dep)
    
    # Summary
    click.echo(f"\n📊 User Deployment Summary:")
    click.echo(f"  ✅ Successfully processed: {len(processed_users)} users")
    if failed_users:
        click.echo(f"  ❌ Failed: {len(failed_users)} users")
        for user_dep in failed_users:
            click.echo(f"    - {user_dep.display_name}")


def _deploy_services(config: ComputorDeploymentConfig, auth: CLIAuthConfig) -> dict:
    """
    Deploy services from configuration (Phase 1 of deployment).

    Creates services with users and API tokens. Returns mapping of service slugs to IDs
    for use in Phase 2 (course creation and token scope updates).

    Args:
        config: Deployment configuration
        auth: Authentication configuration

    Returns:
        dict: Mapping of service slug to service details (id, token_id, user_id)
    """
    from computor_types.services import ServiceCreate
    from computor_types.api_tokens import ApiTokenCreate, ApiTokenCreateResponse
    from computor_types.service_type import ServiceTypeQuery
    from datetime import datetime, timedelta
    import os

    if not config.services:
        return {}

    click.echo(f"\n🔧 Phase 1: Deploying {len(config.services)} services...")

    client = run_async(get_computor_client(auth))
    service_client = client.services
    user_client = client.user
    api_token_client = client.api_tokens
    service_type_client = client.service_types
    custom_client = SyncHTTPWrapper(client)

    # Track deployed services for later use
    deployed_services = {}

    for service_config in config.services:
        click.echo(f"\n  Processing service: {service_config.slug}")

        try:
            # Check if service already exists
            existing_services = run_async(service_client.get_service_accounts(slug=service_config.slug))

            # Track whether we need to create a token
            need_to_create_token = False

            if existing_services and len(existing_services) > 0:
                service = existing_services[0]
                click.echo(f"    ℹ️  Service already exists: {service.slug}")

                # Look up the service's token by user_id (defaults to active tokens only)
                existing_tokens = run_async(api_token_client.get_api_tokens(
                    user_id=str(service.user_id)
                ))

                if existing_tokens and len(existing_tokens) > 0:
                    # Check if force_recreate is enabled
                    if service_config.api_token.force_recreate:
                        if not service_config.api_token.token:
                            click.echo(f"    ❌ force_recreate=True requires a predefined token to be set")
                            raise ValueError(f"force_recreate=True requires a predefined token for service '{service_config.slug}'")

                        # Delete existing token(s) and recreate
                        click.echo(f"    🔄 force_recreate=True: Deleting existing token(s)...")
                        for token in existing_tokens:
                            try:
                                run_async(api_token_client.delete_api_tokens(str(token.id)))
                                click.echo(f"    ✅ Deleted token: {token.token_prefix}...")
                            except Exception as e:
                                click.echo(f"    ⚠️  Failed to delete token {token.id}: {e}")

                        need_to_create_token = True
                    else:
                        # Use the first token (only active tokens are returned by default)
                        token = existing_tokens[0]
                        token_id = str(token.id)
                        click.echo(f"    ℹ️  Found existing token: {token.token_prefix}...")

                        deployed_services[service_config.slug] = {
                            "id": str(service.id),
                            "user_id": str(service.user_id),
                            "token_id": token_id
                        }
                        continue
                else:
                    # Service exists but no token - need to create one
                    click.echo(f"    ⚠️  No token found for service, creating new token...")
                    need_to_create_token = True

            # Only create service if it doesn't exist yet
            if not existing_services or len(existing_services) == 0:
                # 1. Get username for the service (API will create user if needed)
                user_username = service_config.user.username

                # 2. Look up ServiceType by path
                service_type = None
                if service_config.service_type_path:
                    service_types = run_async(service_type_client.list(
                        ServiceTypeQuery(path=service_config.service_type_path)
                    ))
                    if service_types and len(service_types) > 0:
                        service_type = service_types[0]
                        click.echo(f"    ✅ Found ServiceType: {service_config.service_type_path}")
                    else:
                        click.echo(f"    ⚠️  ServiceType not found: {service_config.service_type_path}")

                # 3. Create Service
                service_properties = {}
                if service_config.language:
                    service_properties["language"] = service_config.language

                service_create = ServiceCreate(
                    slug=service_config.slug,
                    name=service_config.user.given_name or service_config.slug.replace('-', ' ').title(),
                    description=service_config.description or f"Service for {service_config.slug}",
                    service_type=service_config.service_type_path if service_type else "custom",
                    username=user_username,
                    email=service_config.user.email,
                    config=service_config.config or {},
                    enabled=True
                )

                service = run_async(service_client.service_accounts(service_create))
                click.echo(f"    ✅ Created service: {service_config.slug}")
                need_to_create_token = True  # New service always needs a token

            # 4. Create API Token (if needed)
            if not need_to_create_token:
                # Service exists and has a token - already handled above
                continue
            token_config = service_config.api_token

            # Check for predefined token
            predefined_token = token_config.token
            predefined_token_specified = bool(predefined_token)  # Remember if token was specified

            if predefined_token:
                # Store original value for error messages
                original_token_value = predefined_token

                # Expand environment variables
                predefined_token = os.path.expandvars(predefined_token)

                # Validate expanded token
                validation_errors = []
                if not predefined_token or predefined_token.strip() == "":
                    validation_errors.append("token is empty after environment variable expansion")
                elif predefined_token.startswith("${"):
                    validation_errors.append(f"environment variable not set or not exported (got: '{predefined_token}')")
                elif len(predefined_token) < 32:
                    validation_errors.append(f"token is too short (got {len(predefined_token)} chars, need at least 32)")
                elif not predefined_token.startswith("ctp_"):
                    validation_errors.append("token must start with 'ctp_' prefix")

                if validation_errors:
                    error_msg = f"Invalid predefined token for service '{service_config.slug}': {'; '.join(validation_errors)}"
                    click.echo(f"    ❌ {error_msg}")
                    click.echo(f"       Original value in deployment.yaml: {original_token_value}")
                    click.echo(f"       Expanded value: {predefined_token if predefined_token else '(empty)'}")
                    raise ValueError(error_msg)

            # Calculate expiration date
            expires_at = None
            if token_config.expires_days:
                expires_at = datetime.utcnow() + timedelta(days=token_config.expires_days)

            if predefined_token:
                # Use admin endpoint to create token with predefined value
                click.echo(f"    ✅ Using predefined token (admin only)")
                from computor_types.api_tokens import ApiTokenAdminCreate

                # Build token creation params - only include scopes if explicitly provided
                token_create_params = {
                    "name": token_config.name or f"{service_config.slug} Token",
                    "description": f"API token for {service_config.slug}",
                    "user_id": str(service.user_id),
                    "predefined_token": predefined_token,
                    "expires_at": expires_at
                }
                if token_config.scopes:  # Only add scopes if explicitly provided
                    token_create_params["scopes"] = token_config.scopes

                token_create = ApiTokenAdminCreate(**token_create_params)

                # Call admin endpoint (use mode='json' to serialize datetime objects)
                token_response = custom_client.create("api-tokens/admin/create", token_create.model_dump(mode='json'))
                click.echo(f"    ✅ Created API token with predefined value: {token_response['token_prefix']}...")

                deployed_services[service_config.slug] = {
                    "id": str(service.id),
                    "user_id": str(service.user_id),
                    "token_id": str(token_response['id']),
                    "token": predefined_token
                }
            else:
                # Generate random token
                click.echo(f"    ℹ️  Generating new random token...")

                # Build token creation params - only include scopes if explicitly provided
                token_create_params = {
                    "name": token_config.name or f"{service_config.slug} Token",
                    "description": f"API token for {service_config.slug}",
                    "user_id": str(service.user_id),
                    "expires_at": expires_at
                }
                if token_config.scopes:  # Only add scopes if explicitly provided
                    token_create_params["scopes"] = token_config.scopes

                token_create = ApiTokenCreate(**token_create_params)

                token_response = run_async(api_token_client.api_tokens(token_create))
                click.echo(f"    ✅ Created API token: {token_response.token_prefix}...")
                click.echo(f"    🔑 Token: {token_response.token}")
                click.echo(f"    ⚠️  IMPORTANT: Store this token securely! It cannot be retrieved later.")

                deployed_services[service_config.slug] = {
                    "id": str(service.id),
                    "user_id": str(service.user_id),
                    "token_id": str(token_response.id),
                    "token": token_response.token
                }

        except Exception as e:
            click.echo(f"    ❌ Failed to deploy service {service_config.slug}: {e}")
            import traceback
            click.echo(f"    {traceback.format_exc()}")

    click.echo(f"\n✅ Phase 1 complete: {len(deployed_services)} services deployed")
    return deployed_services


def _deploy_course_content_types(course_id: str, content_types_config: list, auth: CLIAuthConfig):
    """Deploy course content types for a course via API."""
    if not content_types_config:
        return

    client = run_async(get_computor_client(auth))
    content_type_client = client.course_content_types

    created_count = 0
    existing_count = 0

    for content_type_config in content_types_config:
        try:
            # Check if content type already exists
            existing_types = run_async(content_type_client.list(CourseContentTypeQuery(
                course_id=course_id,
                slug=content_type_config.slug
            )))

            if existing_types:
                click.echo(f"    ℹ️  Content type already exists: {content_type_config.slug}")
                existing_count += 1
                continue

            # Create new content type
            content_type_create = CourseContentTypeCreate(
                slug=content_type_config.slug,
                title=content_type_config.title,
                description=content_type_config.description,
                color=content_type_config.color or "green",
                properties=content_type_config.properties or {},
                course_id=course_id,
                course_content_kind_id=content_type_config.kind
            )

            run_async(content_type_client.create(content_type_create))
            click.echo(f"    ✅ Created content type: {content_type_config.slug}")
            created_count += 1

        except Exception as e:
            click.echo(f"    ❌ Failed to create content type {content_type_config.slug}: {e}")

    if created_count > 0 or existing_count > 0:
        click.echo(f"    📊 Content types: {created_count} created, {existing_count} existing")


def _deploy_course_contents(course_id: str, course_config: HierarchicalCourseConfig, auth: CLIAuthConfig, parent_path: str = None, position_counter: list = None, deployed_services: dict = None):
    """Deploy course contents for a course."""


    client = run_async(get_computor_client(auth))

    if not course_config.contents:
        return
    
    # Initialize position counter if not provided
    if position_counter is None:
        position_counter = [1.0]
    
    # Get API clients
    content_client = client.course_contents
    content_type_client = client.course_content_types
    content_kind_client = client.course_content_kinds
    example_client = client.examples
    # backend_client = client.execution_backends  # REMOVED: execution_backends deprecated
    custom_client = SyncHTTPWrapper(client)
    
    for content_config in course_config.contents:
        try:
            # We may generate the full path later if not provided
            full_path = None
            
            # Find the content type
            content_types = run_async(content_type_client.list(CourseContentTypeQuery(
                course_id=course_id,
                slug=content_config.content_type
            )))
            
            if not content_types:
                click.echo(f"    ⚠️  Content type not found: {content_config.content_type}")
                continue
            
            content_type = content_types[0]
            
            # Determine if submittable by content kind (needed to fetch example metadata)
            is_submittable = False
            if content_type.course_content_kind_id:
                content_kinds = run_async(content_kind_client.list(CourseContentKindQuery(
                    id=content_type.course_content_kind_id
                )))
                if content_kinds and len(content_kinds) > 0:
                    is_submittable = content_kinds[0].submittable
            
            # Prefetch example/version to derive defaults when missing
            example = None
            version = None
            meta_title = None
            meta_description = None
            ex_title = None
            if is_submittable and content_config.example_identifier:
                try:
                    examples = run_async(example_client.list(ExampleQuery(
                        identifier=content_config.example_identifier
                    )))
                    if examples:
                        example = examples[0]
                        ex_title = getattr(example, 'title', None)
                        version_tag = content_config.example_version_tag or "latest"
                        try:
                            # Backend now handles normalization and "latest" tag
                            all_versions = custom_client.list(
                                f"examples/{example.id}/versions",
                                params={"version_tag": version_tag}
                            ) or []
                        except Exception:
                            all_versions = []
                        if version_tag == "latest" and all_versions:
                            version = all_versions[0]
                        else:
                            for v in all_versions:
                                if v.get('version_tag') == version_tag:
                                    version = v
                                    break
                        # Fetch full version details to access meta_yaml
                        if version and not version.get('meta_yaml'):
                            try:
                                version = custom_client.get(f"examples/versions/{version['id']}") or version
                            except Exception:
                                pass
                        if version and version.get('meta_yaml'):
                            try:
                                meta = yaml.safe_load(version.get('meta_yaml') or "") or {}
                                meta_title = meta.get('title')
                                meta_description = meta.get('description')
                            except Exception:
                                pass
                except Exception:
                    pass

            # Decide path: prefer provided path, otherwise generate from title/meta/example id and ensure uniqueness
            if content_config.path:
                full_path = f"{parent_path}.{content_config.path}" if parent_path else content_config.path
            else:
                # Determine effective title now (may still be None)
                identifier_last = None
                if content_config.example_identifier:
                    try:
                        identifier_last = content_config.example_identifier.split('.')[-1]
                    except Exception:
                        identifier_last = content_config.example_identifier
                eff_title_src = content_config.title or meta_title or ex_title or identifier_last or 'content'
                import re
                seg = re.sub(r"[^a-z0-9_]+", "", re.sub(r"[\s-]+", "_", (eff_title_src or 'content').lower().strip())) or 'content'
                candidate = f"{parent_path}.{seg}" if parent_path else seg
                idx = 1
                while True:
                    existing = run_async(content_client.list(CourseContentQuery(course_id=course_id, path=candidate)))
                    if not existing:
                        full_path = candidate
                        break
                    idx += 1
                    seg_try = f"{seg}_{idx}"
                    candidate = f"{parent_path}.{seg_try}" if parent_path else seg_try

            # Helper to humanize a slug/segment to a friendly title
            def _humanize(seg: str) -> str:
                try:
                    return ' '.join([w.capitalize() for w in seg.replace('_', ' ').replace('-', ' ').split() if w]) or seg
                except Exception:
                    return seg

            # Check if content already exists
            # Use custom_client to bypass Pydantic validation issues
            existing_contents = custom_client.list("course-contents", params={
                "course_id": course_id,
                "path": full_path
            })

            if existing_contents:
                # Convert to object for easier access
                from types import SimpleNamespace
                content = SimpleNamespace(**existing_contents[0])
                click.echo(f"    ℹ️  Content already exists: {content.title} ({full_path})")

                # Only update description if explicitly provided in deployment, otherwise if empty use meta_yaml.description
                # NOTE: testing_service_id is NOT set here - it's set automatically when an example is assigned
                to_update = {}
                if content_config.description is not None:
                    if content_config.description != getattr(content, 'description', None):
                        to_update['description'] = content_config.description
                elif is_submittable and not getattr(content, 'description', None) and meta_description:
                    to_update['description'] = meta_description
                # Opportunistically improve title if it's empty or looks like a slug and we have a better source
                current_title = getattr(content, 'title', None)
                fallback_seg = full_path.split('.')[-1]
                friendly_fallback = _humanize(fallback_seg)
                better_title = content_config.title or meta_title or ex_title or friendly_fallback
                if (current_title is None) or (current_title == fallback_seg) or (current_title == friendly_fallback and better_title not in [None, friendly_fallback]):
                    if better_title and better_title != current_title:
                        to_update['title'] = better_title

                if to_update:
                    try:
                        # Use custom_client to bypass Pydantic validation issues
                        custom_client.update(f"course-contents/{content.id}", to_update)
                        update_msg = ", ".join(to_update.keys())
                        click.echo(f"      ✏️  Updated content: {update_msg}")
                    except Exception as e:
                        click.echo(f"      ⚠️  Failed to update content: {e}")
            else:
                # Determine position
                position = content_config.position if content_config.position is not None else position_counter[0]
                position_counter[0] += 1.0

                # Derive title/description defaults: description only from meta_yaml when not given
                fallback_seg = None
                try:
                    fallback_seg = full_path.split('.')[-1]
                except Exception:
                    fallback_seg = full_path
                effective_title = content_config.title or meta_title or ex_title or _humanize(fallback_seg)
                effective_description = content_config.description if content_config.description is not None else meta_description

                # Create the content
                # NOTE: testing_service_id is NOT set here - it's set automatically when an example is assigned
                content_create_data = {
                    "title": effective_title,
                    "description": effective_description,
                    "path": full_path,
                    "course_id": course_id,
                    "course_content_type_id": str(content_type.id),
                    "position": position,
                    "max_group_size": content_config.max_group_size or 1,
                    "max_test_runs": content_config.max_test_runs,
                    "max_submissions": content_config.max_submissions,
                    "testing_service_id": None,  # Will be set when example is assigned
                    "properties": content_config.properties.model_dump() if content_config.properties else None
                }

                # Use custom_client to bypass Pydantic validation issues with deployment field
                content = custom_client.create("course-contents", content_create_data)
                # Convert to object for easier access
                from types import SimpleNamespace
                content = SimpleNamespace(**content)
                click.echo(f"    ✅ Created content: {effective_title} ({full_path})")
            
            # Handle example deployment for submittable content
            if is_submittable and content_config.example_identifier:
                if example and version:
                    # Check if deployment already exists using the course-contents API
                    try:
                        deployment_info = custom_client.get(f"course-contents/deployment/{content.id}")
                        has_deployment = deployment_info and deployment_info.get('deployment_status') not in [None, 'unassigned']
                    except Exception:
                        has_deployment = False
                    
                    if has_deployment:
                        click.echo(f"      ℹ️  Deployment already exists for example: {content_config.example_identifier}")
                    else:
                        # Assign example using the course-contents API
                        try:
                            assign_payload = {
                                "example_version_id": str(version['id'])
                            }
                            custom_client.create(f"course-contents/{content.id}/assign-example", assign_payload)
                            click.echo(f"      ✅ Assigned example: {content_config.example_identifier} ({version.get('version_tag')})")
                            # Ensure deployment_path gets filled from example identifier by the release pipeline
                        except Exception as e:
                            click.echo(f"      ⚠️  Failed to assign example: {e}")
                else:
                    # Legacy fallback: look up again if prefetch failed
                    examples = run_async(example_client.list(ExampleQuery(
                        identifier=content_config.example_identifier
                    )))
                    if not examples:
                        click.echo(f"      ⚠️  Example not found in DB: {content_config.example_identifier}")
                        # Fallback: assign by identifier/version_tag (custom assignment)
                        # Enforce explicit version_tag to avoid ambiguous 'latest'
                        vt = content_config.example_version_tag
                        if not vt:
                            click.echo(f"      ❌ Skipping custom assignment: version_tag required for {content_config.example_identifier}")
                            continue
                        try:
                            assign_payload = {
                                "example_identifier": content_config.example_identifier,
                                "version_tag": vt
                            }
                            custom_client.create(f"course-contents/{content.id}/assign-example", assign_payload)
                            click.echo(f"      ✅ Assigned custom example: {content_config.example_identifier} ({vt})")
                        except Exception as e:
                            click.echo(f"      ⚠️  Failed to assign custom example: {e}")
                        continue
                    else:
                        example = examples[0]
                        version_tag = content_config.example_version_tag or "latest"

                        try:
                            # Backend now handles normalization and "latest" tag
                            all_versions = custom_client.list(
                                f"examples/{example['id']}/versions",
                                params={"version_tag": version_tag}
                            ) or []
                        except Exception as e:
                            print(e)
                            all_versions = []
                        
                        version = None
                        if version_tag == "latest" and all_versions:
                            version = all_versions[0]
                        else:
                            for v in all_versions:
                                if v.get('version_tag') == version_tag:
                                    version = v
                                    break

                        # Fetch full version details to access meta_yaml (if later needed)
                        if version and not version.get('meta_yaml'):
                            try:
                                version = custom_client.get(f"examples/versions/{version['id']}") or version
                            except Exception:
                                pass
                        if version:
                            try:
                                deployment_info = custom_client.get(f"course-contents/deployment/{content.id}")
                                has_deployment = deployment_info and deployment_info.get('deployment_status') not in [None, 'unassigned']
                            except Exception:
                                has_deployment = False
                            if has_deployment:
                                click.echo(f"      ℹ️  Deployment already exists for example: {content_config.example_identifier}")
                            else:
                                try:
                                    assign_payload = {"example_version_id": str(version['id'])}
                                    custom_client.create(f"course-contents/{content.id}/assign-example", assign_payload)
                                    click.echo(f"      ✅ Assigned example: {content_config.example_identifier} ({version_tag})")
                                except Exception as e:
                                    click.echo(f"      ⚠️  Failed to assign example: {e}")
                        else:
                            click.echo(f"      ⚠️  Example version not found: {content_config.example_identifier} ({version_tag})")
            
            # Recursively deploy nested contents
            if content_config.contents:
                # Create a temporary course config with just the nested contents
                nested_config = type('obj', (object,), {'contents': content_config.contents, 'services': getattr(course_config, 'services', None)})()
                _deploy_course_contents(course_id, nested_config, auth, full_path, position_counter, deployed_services)
                
        except Exception as e:
            click.echo(f"    ❌ Failed to create content {content_config.title}: {e}")


def _generate_student_templates(config: ComputorDeploymentConfig, auth: CLIAuthConfig):
    """Generate GitLab student template repositories for courses with contents."""
    

    client = run_async(get_computor_client(auth))

    click.echo(f"\n🚀 Generating student template repositories...")
    
    # Get API clients
    org_client = client.organizations
    family_client = client.course_families
    course_client = client.courses
    custom_client = SyncHTTPWrapper(client)
    
    generated_count = 0
    failed_count = 0
    
    # Process each organization
    for org_config in config.organizations:
        # Find the organization
        orgs = run_async(org_client.list(OrganizationQuery(path=org_config.path)))
        if not orgs:
            continue
        org = orgs[0]
        
        # Process each course family
        for family_config in org_config.course_families:
            # Find the course family
            families = run_async(family_client.list(CourseFamilyQuery(
                organization_id=str(org.id),
                path=family_config.path
            )))
            if not families:
                continue
            family = families[0]
            
            # Process each course
            for course_config in family_config.courses:
                # Only process courses that have contents defined
                if not course_config.contents:
                    continue
                    
                # Find the course
                courses = run_async(course_client.list(CourseQuery(
                    course_family_id=str(family.id),
                    path=course_config.path
                )))
                if not courses:
                    continue
                course = courses[0]
                
                # First, generate assignments repository (initial populate from Example Library)
                try:
                    click.echo(f"  Initializing assignments repo for: {course_config.name} ({course_config.path})")
                    custom_client.create(
                        f"system/courses/{course.id}/generate-assignments",
                        {
                            "all": True,
                            "overwrite_strategy": "force_update"
                        }
                    )
                except Exception as e:
                    click.echo(f"    ⚠️  Failed to initialize assignments: {e}")
                
                # Then, generate student template for this course
                try:
                    click.echo(f"  Generating template for: {course_config.name} ({course_config.path})")
                    result = custom_client.create(f"system/courses/{course.id}/generate-student-template", {})
                    
                    if result and result.get('workflow_id'):
                        click.echo(f"    ✅ Template generation started (workflow: {result.get('workflow_id')})")
                        # Wait for completion before proceeding to user repo creation
                        workflow_id = result.get('workflow_id')
                        import time
                        for _ in range(120):  # up to 10 minutes, poll every 5s
                            time.sleep(5)
                            try:
                                task_info = custom_client.get(f"tasks/{workflow_id}/status")
                                status = (task_info or {}).get('status')
                                if status in ['finished', 'failed', 'cancelled']:
                                    click.echo(f"    ▶ Template generation status: {status}")
                                    break
                            except Exception:
                                # Keep trying a bit
                                continue
                        generated_count += 1
                    else:
                        click.echo(f"    ⚠️  Template generation response unclear")
                        failed_count += 1
                except Exception as e:
                    click.echo(f"    ❌ Failed to generate template: {e}")
                    failed_count += 1
    
    # Summary
    if generated_count > 0 or failed_count > 0:
        click.echo(f"\n📊 Student Template Generation Summary:")
        click.echo(f"  ✅ Successfully initiated: {generated_count} templates")
        if failed_count > 0:
            click.echo(f"  ❌ Failed: {failed_count} templates")


def _link_backends_to_deployed_courses(config: ComputorDeploymentConfig, auth: CLIAuthConfig, deployed_services: dict = None, generate_student_template: bool = False) -> dict:
    """
    Link execution backends and services to all deployed courses and create course contents.

    Args:
        config: Deployment configuration
        auth: Authentication config
        deployed_services: Dict mapping service slug to service details from Phase 1
        generate_student_template: Whether to generate student templates

    Returns:
        dict: Mapping of service_id to list of course_ids for scope updates
    """

    client = run_async(get_computor_client(auth))

    if deployed_services is None:
        deployed_services = {}

    # Track which services are used by which courses for scope updates
    service_course_mapping = {}  # {service_id: [course_id1, course_id2, ...]}

    click.echo(f"\n🔗 Phase 2: Linking services and backends to courses...")

    # Get API clients
    org_client = client.organizations
    family_client = client.course_families
    course_client = client.courses

    # Process each organization
    for org_config in config.organizations:
        # Find the organization
        orgs = run_async(org_client.list(OrganizationQuery(path=org_config.path)))
        if not orgs:
            click.echo(f"  ⚠️  Organization not found: {org_config.path}")
            continue
        org = orgs[0]

        # Process each course family
        for family_config in org_config.course_families:
            # Find the course family
            families = run_async(family_client.list(CourseFamilyQuery(
                organization_id=str(org.id),
                path=family_config.path
            )))
            if not families:
                click.echo(f"  ⚠️  Course family not found: {family_config.path}")
                continue
            family = families[0]

            # Process each course
            for course_config in family_config.courses:
                # Find the course
                courses = run_async(course_client.list(CourseQuery(
                    course_family_id=str(family.id),
                    path=course_config.path
                )))
                if not courses:
                    click.echo(f"  ⚠️  Course not found: {course_config.path}")
                    continue
                course = courses[0]

                click.echo(f"  Course: {course_config.name} ({course_config.path})")

                # Link services to this course (new architecture)
                if course_config.services:
                    course_service_ids = _link_services_to_course(
                        str(course.id),
                        course_config.services,
                        deployed_services,
                        auth
                    )
                    # Track service-course mappings
                    for service_id in course_service_ids:
                        if service_id not in service_course_mapping:
                            service_course_mapping[service_id] = []
                        service_course_mapping[service_id].append(str(course.id))

                # Deploy course content types first (must exist before creating contents)
                if course_config.content_types:
                    click.echo(f"\n📋 Creating course content types for {course_config.name}...")
                    _deploy_course_content_types(str(course.id), course_config.content_types, auth)

                # Deploy course contents
                if course_config.contents:
                    click.echo(f"\n📚 Creating course contents for {course_config.name}...")
                    # Pass service information so course contents can link to testing services
                    _deploy_course_contents(str(course.id), course_config, auth, deployed_services=deployed_services)

    # Generate student templates if requested
    if generate_student_template:
        _generate_student_templates(config, auth)

    return service_course_mapping


def _link_services_to_course(course_id: str, services: list, deployed_services: dict, auth: CLIAuthConfig) -> list:
    """
    Link services to a course (new architecture).

    Services are referenced by course contents, not through a join table.
    This function validates that the services exist and returns a list of service IDs
    used by this course for scope updates.

    Args:
        course_id: Course ID
        services: List of ServiceReference objects
        deployed_services: Dict mapping service slug to service details
        auth: Authentication config

    Returns:
        list: List of service IDs used by this course
    """

    if not services:
        return []

    client = run_async(get_computor_client(auth))
    service_client = client.services

    course_service_ids = []

    for service_ref in services:
        try:
            # Check if service exists in deployed_services first
            if service_ref.slug in deployed_services:
                service_id = deployed_services[service_ref.slug]["id"]
                course_service_ids.append(service_id)
                click.echo(f"      ✅ Service registered for course: {service_ref.slug}")
                continue

            # Otherwise, look up by slug
            existing_services = run_async(service_client.get_service_accounts(slug=service_ref.slug))

            if not existing_services or len(existing_services) == 0:
                click.echo(f"      ⚠️  Service not found: {service_ref.slug}")
                continue

            service = existing_services[0]
            course_service_ids.append(str(service.id))
            click.echo(f"      ✅ Service registered for course: {service_ref.slug}")

        except Exception as e:
            click.echo(f"      ❌ Failed to process service {service_ref.slug}: {e}")

    return course_service_ids


def _update_token_scopes(service_course_mapping: dict, deployed_services: dict, auth: CLIAuthConfig):
    """
    Verify API token scopes (Phase 3).

    NOTE: As of the latest changes, token scopes are automatically assigned by the backend
    based on service type when tokens are created in Phase 1. This function now just verifies
    the scopes are correctly set and reports them.

    Args:
        service_course_mapping: Dict mapping service_id to list of course_ids
        deployed_services: Dict mapping service slug to service details (including token_id)
        auth: Authentication config
    """

    if not service_course_mapping:
        click.echo("\n⚠️  No service-course mappings found, skipping token scope verification")
        return

    click.echo(f"\n🔐 Phase 3: Verifying API token scopes...")

    client = run_async(get_computor_client(auth))
    api_token_client = client.api_tokens

    # Create reverse mapping: service_id -> service_slug
    service_id_to_slug = {}
    for slug, details in deployed_services.items():
        service_id_to_slug[details["id"]] = slug

    verified_count = 0

    for service_id, course_ids in service_course_mapping.items():
        try:
            service_slug = service_id_to_slug.get(service_id)
            if not service_slug:
                click.echo(f"    ⚠️  Service ID {service_id} not found in deployed services")
                continue

            service_details = deployed_services.get(service_slug)
            if not service_details:
                continue

            token_id = service_details.get("token_id")
            if not token_id:
                click.echo(f"    ⚠️  No token ID found for service: {service_slug}")
                continue

            # Get current token and display scopes
            token = run_async(api_token_client.get_api_tokens_token_id(token_id))
            current_scopes = token.scopes or []

            click.echo(f"    ✅ {service_slug}: {len(current_scopes)} scopes")
            verified_count += 1

        except Exception as e:
            click.echo(f"    ❌ Failed to verify token for service {service_id}: {e}")

    click.echo(f"\n✅ Phase 3 complete: {verified_count} tokens verified")


def _ensure_example_repository(repo_name: str, auth: CLIAuthConfig):
    """Find or create an example repository with MinIO backend."""

    # Use direct HTTP client to avoid pydantic validation issues
    # The generated client tries to validate list responses as ExampleRepositoryGet
    # but the API returns ExampleRepositoryList which doesn't have created_at/updated_at
    import httpx

    async def _find_or_create_repo():
        async with httpx.AsyncClient(base_url=auth.api_url) as http_client:
            # Authenticate first
            if auth.basic:
                auth_response = await http_client.post(
                    "/auth/login",
                    json={"username": auth.basic.username, "password": auth.basic.password}
                )
                auth_response.raise_for_status()
                token = auth_response.json()["access_token"]
                http_client.headers.update({"Authorization": f"Bearer {token}"})
            else:
                raise RuntimeError("Only basic auth is supported for repository lookup")

            # Search for existing repository
            click.echo(f"    🔍 Searching for repository: {repo_name}")
            response = await http_client.get("/example-repositories", params={"name": repo_name})
            response.raise_for_status()

            repos = response.json()
            click.echo(f"    🔍 Found {len(repos)} matching repositories")

            if repos:
                repo = repos[0]
                click.echo(f"    ✅ Using existing repository: {repo['name']} (ID: {repo['id']}, source_url: {repo['source_url']})")
                # Convert to ExampleRepositoryGet-like object
                from types import SimpleNamespace
                return SimpleNamespace(**repo)

            # Create new repository
            click.echo(f"    📦 Creating new repository: {repo_name}")
            create_data = {
                "name": repo_name,
                "description": f"Repository for {repo_name} examples",
                "source_type": "minio",
                "source_url": "examples-bucket",
            }

            response = await http_client.post("/example-repositories", json=create_data)
            response.raise_for_status()

            repo = response.json()
            click.echo(f"    ✅ Created repository: {repo['name']} (ID: {repo['id']})")
            return SimpleNamespace(**repo)

    return run_async(_find_or_create_repo())


def _create_zip_bytes_from_directory(directory_path: Path) -> bytes:
    """Create a zip archive from a directory; ensure meta.yaml exists.

    - Skips hidden files/dirs (starting with '.')
    - If meta.yaml is missing, generates a minimal one
    """
    # Determine if meta.yaml exists
    meta_path = directory_path / "meta.yaml"
    needs_meta = not meta_path.is_file()

    # Prepare in-memory zip
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
        # Add all non-hidden files recursively
        for file_path in directory_path.rglob("*"):
            rel = file_path.relative_to(directory_path)
            # Skip hidden files/dirs
            parts = rel.parts
            if any(part.startswith(".") for part in parts):
                continue
            if file_path.is_file():
                zipf.write(file_path, arcname=str(rel))

        # Inject minimal meta.yaml if missing
        if needs_meta:
            minimal_meta = (
                "title: "
                + directory_path.name.replace('-', ' ').replace('_', ' ').title()
                + "\n"
                + f"description: Example from {directory_path.name}\n"
                + "language: en\n"
            )
            zipf.writestr("meta.yaml", minimal_meta)

    return zip_buffer.getvalue()


def _read_meta_and_dependencies(example_dir: Path) -> tuple[str, list[str]]:
    """Read meta.yaml from a directory and return (slug, dependencies).

    - Slug comes from meta.yaml 'slug' or falls back to directory name mapped to dots
    - Dependencies are read from either 'properties.testDependencies' or 'testDependencies'
      and normalized to a list of slugs
    """
    meta_path = example_dir / "meta.yaml"
    slug = example_dir.name.replace('-', '.').replace('_', '.')
    dependencies: list[str] = []

    if meta_path.is_file():
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = yaml.safe_load(f) or {}
        except Exception:
            meta = {}
        slug = meta.get('slug', slug)

        # testDependencies can be in meta['properties']['testDependencies'] or meta['testDependencies']
        td = None
        if isinstance(meta.get('properties'), dict) and 'testDependencies' in meta['properties']:
            td = meta['properties'].get('testDependencies')
        elif 'testDependencies' in meta:
            td = meta.get('testDependencies')

        if isinstance(td, list):
            for item in td:
                if isinstance(item, str):
                    dependencies.append(item)
                elif isinstance(item, dict) and 'slug' in item:
                    dependencies.append(item['slug'])
    return slug, dependencies


def _toposort_by_dependencies(subdirs: list[Path]) -> list[Path]:
    """Topologically sort example directories so dependencies come first.

    - Builds a graph based on meta.yaml testDependencies slugs
    - Only considers dependencies that are present in the batch
    - On cycles, falls back to appending remaining nodes in stable order
    """
    # Build slug mapping and deps
    slug_to_dir: dict[str, Path] = {}
    deps_map: dict[str, set[str]] = {}

    for d in subdirs:
        slug, deps = _read_meta_and_dependencies(d)
        slug_to_dir[slug] = d
        deps_map[slug] = set(deps)

    # Reduce dependencies to only those within this batch
    for slug, deps in deps_map.items():
        deps_map[slug] = set(dep for dep in deps if dep in slug_to_dir)

    # Compute in-degrees
    in_degree: dict[str, int] = {slug: 0 for slug in slug_to_dir}
    for slug, deps in deps_map.items():
        for dep in deps:
            in_degree[slug] += 1

    # Kahn's algorithm
    queue = [slug for slug, deg in in_degree.items() if deg == 0]
    queue.sort()  # stable order
    ordered_slugs: list[str] = []

    # Build reverse edges: dep -> [slug]
    rev: dict[str, set[str]] = {s: set() for s in slug_to_dir}
    for slug, deps in deps_map.items():
        for dep in deps:
            rev[dep].add(slug)

    while queue:
        s = queue.pop(0)
        ordered_slugs.append(s)
        for nxt in sorted(rev.get(s, [])):
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                queue.append(nxt)

    # If there are nodes left (cycle), append them in deterministic order
    if len(ordered_slugs) < len(slug_to_dir):
        remaining = [s for s in slug_to_dir if s not in ordered_slugs]
        ordered_slugs.extend(sorted(remaining))

    return [slug_to_dir[s] for s in ordered_slugs]


def _upload_extensions_from_config(entries: list, config_dir: Path, auth: CLIAuthConfig, client):
    """Upload VSIX extensions defined in the deployment configuration."""


    client = run_async(get_computor_client(auth))

    for entry in entries:
        entry_path = Path(entry.path)
        resolved_path = entry_path if entry_path.is_absolute() else (config_dir / entry_path).resolve()

        click.echo(f"\n📦 Extension package: {resolved_path}")

        if not resolved_path.exists() or not resolved_path.is_file():
            click.echo(f"  ❌ File not found: {resolved_path}", err=True)
            continue

        try:
            file_bytes = resolved_path.read_bytes()
        except OSError as exc:
            click.echo(f"  ❌ Could not read VSIX file: {exc}", err=True)
            continue

        try:
            manifest = parse_vsix_metadata(file_bytes)
        except VsixManifestError as exc:
            click.echo(f"  ❌ Invalid VSIX package: {exc}", err=True)
            continue

        publisher = entry.publisher or manifest.publisher
        name = entry.name or manifest.name
        identity = f"{publisher}.{name}"
        version = manifest.version

        click.echo(f"  ➡️  Uploading {identity}@{version}")

        engine_range = entry.engine_range or manifest.engine_range
        display_name = entry.display_name or manifest.display_name
        description = entry.description if entry.description is not None else manifest.description

        form_data = {"version": version}
        if engine_range:
            form_data["engine_range"] = engine_range
        if display_name:
            form_data["display_name"] = display_name
        if description:
            form_data["description"] = description

        form_data = {key: str(value) for key, value in form_data.items() if value is not None}

        try:
            # Use the underlying httpx client for multipart/form-data upload
            # Note: client._http is async, so we need to use the sync httpx client
            import httpx
            import io

            # Create file-like object for httpx
            file_obj = io.BytesIO(file_bytes)
            files = {
                "file": (resolved_path.name, file_obj, "application/octet-stream")
            }

            # Build headers with auth token, but remove Content-Type to let httpx set it for multipart
            headers = dict(client._http._default_headers)
            if client._auth_provider.is_authenticated():
                token = client._auth_provider._access_token
                if token:
                    headers["Authorization"] = f"Bearer {token}"
            headers.pop('content-type', None)
            headers.pop('Content-Type', None)

            with httpx.Client(base_url=client._http.base_url, headers=headers) as sync_client:
                response = sync_client.post(
                    f"extensions/{identity}/versions",
                    data=form_data,
                    files=files,
                )
                if response.status_code != 201:
                    click.echo(f"  ❌ Upload failed: HTTP {response.status_code}", err=True)
                    click.echo(f"  Response: {response.text}", err=True)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            click.echo(f"  ❌ Upload failed: {exc}", err=True)
            continue

        uploaded_version = payload.get("version", version)
        sha256 = payload.get("sha256", "<unknown>")
        click.echo(f"  ✅ Uploaded version {uploaded_version} (sha256 {sha256})")


def _upload_examples_from_directory(examples_dir: Path, repo_name: str, auth: CLIAuthConfig, client):
    """Upload each subdirectory in examples_dir as a zipped example to the API.

    The upload order is topologically sorted by dependencies found in meta.yaml.
    """

    client = run_async(get_computor_client(auth))
    custom_client = SyncHTTPWrapper(client)

    if not examples_dir.exists() or not examples_dir.is_dir():
        click.echo(f"⚠️  Examples directory not found or not a directory: {examples_dir}")
        return

    # Ensure repository exists
    repo = _ensure_example_repository(repo_name, auth)
    repo_id = str(repo.id)

    # Collect immediate subdirectories
    subdirs = [d for d in examples_dir.iterdir() if d.is_dir()]
    if not subdirs:
        click.echo(f"ℹ️  No example subdirectories found in {examples_dir}")
        return

    # Sort by dependencies so prerequisites upload first
    ordered_subdirs = _toposort_by_dependencies(subdirs)

    click.echo(f"\n📦 Uploading {len(ordered_subdirs)} example(s) from '{examples_dir}' to repository '{repo_name}'...")

    uploaded = 0
    failed = 0
    for subdir in ordered_subdirs:
        try:
            # Create zip bytes (ensure meta.yaml is included)
            zip_bytes = _create_zip_bytes_from_directory(subdir)
            b64_zip = base64.b64encode(zip_bytes).decode("ascii")

            payload = {
                "repository_id": repo_id,
                "directory": subdir.name,
                "files": {f"{subdir.name}.zip": b64_zip},
            }

            # Upload
            custom_client.create("examples/upload", payload)
            click.echo(f"  ✅ Uploaded example: {subdir.name}")
            uploaded += 1
        except Exception as e:
            click.echo(f"  ❌ Failed to upload {subdir.name}: {e}")
            failed += 1

    click.echo(f"📊 Example upload summary — success: {uploaded}, failed: {failed}, total: {len(subdirs)}")


@deployment.command()
@click.argument('config_file', type=click.Path(exists=True))
@click.option(
    '--dry-run',
    is_flag=True,
    help='Validate configuration without deploying'
)
@click.option(
    '--wait',
    is_flag=True,
    default=True,
    help='Wait for deployment to complete'
)
@authenticate
def apply(config_file: str, dry_run: bool, wait: bool, auth: CLIAuthConfig):
    """
    Apply a deployment configuration to create the hierarchy.
    
    This command reads a YAML deployment configuration and creates the
    organization -> course family -> course structure using Temporal workflows.
    """

    client = run_async(get_computor_client(auth))

    click.echo(f"Loading deployment configuration from {config_file}...")
    
    # Load and parse the YAML file
    try:
        with open(config_file, 'r') as f:
            yaml_data = yaml.safe_load(f)
        
        # Validate by creating the config object
        config = ComputorDeploymentConfig(**yaml_data)
        click.echo("✅ Configuration validated successfully")
        
        if dry_run:
            click.echo("\n--- Deployment Plan (Dry Run) ---")
            
            # Show entity counts
            counts = config.count_entities()
            click.echo(f"Total: {counts['organizations']} organizations, {counts['course_families']} course families, {counts['courses']} courses")
            if counts.get('users', 0) > 0:
                click.echo(f"       {counts['users']} users, {counts['course_members']} course memberships")
            
            # Show execution backends to be created
            # Show hierarchical structure
            for org_idx, org in enumerate(config.organizations):
                click.echo(f"\nOrganization {org_idx + 1}: {org.name} ({org.path})")
                if org.gitlab:
                    click.echo(f"  GitLab: {org.gitlab.url} (parent: {org.gitlab.parent or 'root'})")
                
                for family_idx, family in enumerate(org.course_families):
                    click.echo(f"  Course Family {family_idx + 1}: {family.name} ({family.path})")
                    
                    for course_idx, course in enumerate(family.courses):
                        click.echo(f"    Course {course_idx + 1}: {course.name} ({course.path})")
            
            # Show all paths that will be created
            paths = config.get_deployment_paths()
            if paths:
                click.echo(f"\nPaths to be created:")
                for path in paths:
                    click.echo(f"  - {path}")
            
            # Show users to be created
            if config.users:
                click.echo(f"\nUsers to be created:")
                for user_deployment in config.users:
                    user = user_deployment.user
                    click.echo(f"  - {user.display_name} ({user.username})")
                    if user_deployment.accounts:
                        for account in user_deployment.accounts:
                            click.echo(f"    Account: {account.type} @ {account.provider}")
                    if user_deployment.course_members:
                        for cm in user_deployment.course_members:
                            if cm.is_path_based:
                                member_str = f"    Member: {cm.organization}/{cm.course_family}/{cm.course} as {cm.role}"
                                if cm.group:
                                    member_str += f" (group: {cm.group})"
                                click.echo(member_str)
                            elif cm.is_id_based:
                                member_str = f"    Member: Course {cm.id} as {cm.role}"
                                if cm.group:
                                    member_str += f" (group: {cm.group})"
                                click.echo(member_str)
            
            click.echo("\n✅ Dry run completed. No changes made.")
            return
        
    except Exception as e:
        click.echo(f"❌ Error loading configuration: {e}", err=True)
        sys.exit(1)
    
    # Setup client with authentication
    custom_client = SyncHTTPWrapper(client)

    # Phase 1: Deploy services first (before hierarchy)
    deployed_services = {}
    if config.services:
        deployed_services = _deploy_services(config, auth)
    # Optionally upload VS Code extensions prior to starting hierarchy deployment
    if getattr(config, 'extensions_upload', None):
        cfg_dir = Path(config_file).parent
        click.echo("\n📦 Preparing VSIX uploads...")
        _upload_extensions_from_config(config.extensions_upload, cfg_dir, auth, client)

    # Optionally upload examples prior to starting hierarchy deployment
    if getattr(config, 'examples_upload', None):
        cfg_dir = Path(config_file).parent
        rel_path = Path(config.examples_upload.path)
        resolved_path = rel_path if rel_path.is_absolute() else (cfg_dir / rel_path).resolve()
        click.echo(f"\n🔼 Preparing example uploads from: {resolved_path}")
        _upload_examples_from_directory(resolved_path, config.examples_upload.repository, auth, client)

    # Check if there's anything to deploy
    if not config.organizations and not config.users:
        click.echo("\nℹ️ No hierarchy or users defined in configuration; nothing to deploy.")
        return

    # Deploy hierarchy if it exists
    if config.organizations:
        # Deploy using API endpoint
        click.echo(f"\nStarting hierarchy deployment via API...")

        payload = {
            "deployment_config": config.model_dump(),
            "validate_only": False
        }

        try:
            # Send deployment request
            result = custom_client.create("system/hierarchy/create", payload)

            if result:
                click.echo(f"✅ Deployment workflow started!")
                click.echo(f"  Workflow ID: {result.get('workflow_id')}")
                click.echo(f"  Status: {result.get('status')}")
                click.echo(f"  Path: {result.get('deployment_path')}")

                # Check if Phase 2 is needed (services, content types, contents, or user course assignments)
                needs_phase_2 = False

                # Check for courses with services/content
                for org in config.organizations:
                    for family in org.course_families:
                        for course in family.courses:
                            if course.services or course.content_types or course.contents:
                                needs_phase_2 = True
                                break
                        if needs_phase_2:
                            break
                    if needs_phase_2:
                        break

                # Check for users with course assignments
                if not needs_phase_2 and config.users:
                    for user_config in config.users:
                        if hasattr(user_config, 'course_members') and user_config.course_members:
                            needs_phase_2 = True
                            break

                # Force waiting if Phase 2 is needed
                should_wait = wait or needs_phase_2

                if needs_phase_2 and not wait:
                    click.echo("  ℹ️  Waiting for hierarchy completion (required for subsequent tasks)...")

                if should_wait and result.get('workflow_id'):
                    # Poll for status
                    click.echo("\nWaiting for deployment to complete...")
                    import time
                    workflow_id = result.get('workflow_id')

                    for _ in range(60):  # Wait up to 5 minutes
                        time.sleep(5)
                        try:
                            status_data = custom_client.get(f"system/hierarchy/status/{workflow_id}")
                            if status_data.get('status') == 'completed':
                                click.echo("\n✅ Deployment completed successfully!")

                                # Phase 2: Link services/backends to courses and create contents
                                service_course_mapping = _link_backends_to_deployed_courses(
                                    config, auth, deployed_services, True
                                )

                                # Phase 3: Update token scopes with standardized permissions
                                if service_course_mapping and deployed_services:
                                    _update_token_scopes(service_course_mapping, deployed_services, auth)

                                # Deploy users if configured
                                if config.users:
                                    click.echo(f"\n📥 Creating {len(config.users)} users...")
                                    _deploy_users(config, auth)
                                break
                            elif status_data.get('status') == 'failed':
                                error_msg = status_data.get('error', 'Unknown error')
                                click.echo(f"\n\n❌ Deployment failed!", err=True)
                                click.echo(f"\nError details:", err=True)
                                click.echo(f"  {error_msg}", err=True)

                                # Show workflow ID for debugging
                                if workflow_id:
                                    click.echo(f"\nWorkflow ID: {workflow_id}", err=True)
                                    click.echo(f"Check Temporal UI for more details: http://localhost:8088", err=True)
                                sys.exit(1)
                            click.echo(".", nl=False)
                        except Exception as e:
                            click.echo(f"\n⚠️  Error checking status: {e}")
                            break
                    else:
                        click.echo("\n⚠️  Deployment is still running. Check status later.")

                # If not waiting and Phase 2 not needed, inform user
                if not should_wait:
                    click.echo(f"\n✅ Hierarchy deployment started in background.")
                    click.echo("     No Phase 2 tasks configured (service linking/content creation).")
            else:
                click.echo("❌ Failed to start deployment", err=True)
                sys.exit(1)

        except Exception as e:
            click.echo(f"❌ Error during deployment: {e}", err=True)
            sys.exit(1)
    else:
        # No hierarchy deployment - just deploy users if they exist
        if config.users:
            click.echo(f"\n📥 Deploying {len(config.users)} users (no hierarchy deployment)...")
            _deploy_users(config, auth)
            click.echo("✅ User deployment completed!")


@deployment.command()
@click.argument('config_file', type=click.Path(exists=True))
def validate(config_file: str):
    """
    Validate a deployment configuration file.
    
    This checks that the YAML is valid and all required fields are present.
    """
    click.echo(f"Validating {config_file}...")
    
    try:
        with open(config_file, 'r') as f:
            yaml_data = yaml.safe_load(f)
        
        # Validate by creating the config object
        config = ComputorDeploymentConfig(**yaml_data)
        
        click.echo("✅ Configuration is valid!")
        
        # Show entity counts
        counts = config.count_entities()
        click.echo(f"\nSummary:")
        click.echo(f"  Organizations: {counts['organizations']}")
        click.echo(f"  Course Families: {counts['course_families']}")
        click.echo(f"  Courses: {counts['courses']}")
        if counts.get('users', 0) > 0:
            click.echo(f"  Users: {counts['users']}")
            click.echo(f"  Course Memberships: {counts['course_members']}")
        
        # Show paths
        paths = config.get_deployment_paths()
        if paths:
            click.echo(f"\nPaths:")
            for path in paths:
                click.echo(f"  - {path}")
        
        # Check for potential issues
        warnings = []
        gitlab_configured = any(org.gitlab for org in config.organizations)
        if not gitlab_configured:
            warnings.append("No GitLab configuration specified for any organization")
        
        if warnings:
            click.echo(f"\n⚠️  Warnings:")
            for warning in warnings:
                click.echo(f"  - {warning}")
        
    except yaml.YAMLError as e:
        click.echo(f"❌ Invalid YAML format: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Invalid configuration: {e}", err=True)
        sys.exit(1)


@deployment.command()
def list_examples():
    """List available example deployment formats."""
    click.echo("Available deployment configuration examples:\n")
    
    examples = {
        "minimal": "Single organization with one course family and one course",
        "tutorial": "Simple single organization deployment (default)",
        "full": "Multi-organization deployment with multiple course families and courses"
    }
    
    for name, description in examples.items():
        click.echo(f"  {name:10} - {description}")
    
    click.echo("\nGenerate an example with: ctutor deployment init --format <name>")


# Main command group
@click.group()
def deploy():
    """Deployment management commands."""
    pass


deploy.add_command(deployment, "deployment")
