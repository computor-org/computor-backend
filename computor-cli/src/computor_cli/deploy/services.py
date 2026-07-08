"""Deploy services, link them to courses, and verify API token scopes."""

import click

from computor_cli.auth import get_computor_client
from computor_client import SyncComputorClient
from computor_cli.config import CLIAuthConfig
from computor_cli.utils import run_async

from computor_types.deployment_config import ComputorDeploymentConfig
from computor_types.services import ServiceCreate, ServiceUpdate
from computor_types.courses import CourseQuery
from computor_types.course_members import CourseMemberCreate, CourseMemberQuery
from computor_types.course_groups import CourseGroupQuery
from computor_types.organizations import OrganizationQuery
from computor_types.course_families import CourseFamilyQuery

from computor_cli.deploy.contents import (
    _deploy_course_content_types,
    _deploy_course_contents,
)
from computor_cli.deploy.templates import _generate_student_templates


def _deploy_services(config: ComputorDeploymentConfig, auth: CLIAuthConfig) -> dict:
    """
    Deploy services from configuration (Phase 1, after hierarchy deployment).

    Creates services with users, API tokens, and course memberships.
    Services are deployed AFTER hierarchy so that courses exist for course_member assignments.

    Returns mapping of service slugs to IDs for use in Phase 2 (service linking and token scope updates).

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

    click.echo(f"\n🔧 Phase 1: Deploying {len(config.services)} services (after hierarchy)...")

    client = run_async(get_computor_client(auth))
    service_client = client.services
    user_client = client.user
    api_token_client = client.api_tokens
    service_type_client = client.service_types
    custom_client = SyncComputorClient.from_client(client)

    # API clients for course_members processing
    course_member_client = client.course_members
    course_client = client.courses
    course_group_client = client.course_groups
    org_client = client.organizations
    family_client = client.course_families

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

                # Update service config if provided in deployment YAML
                if service_config.config:
                    try:
                        service_update = ServiceUpdate(config=service_config.config)
                        updated_service = run_async(service_client.patch_service_accounts(
                            str(service.id),
                            service_update
                        ))
                        click.echo(f"    ✅ Updated service config")
                        service = updated_service  # Use updated service object
                    except Exception as e:
                        click.echo(f"    ⚠️  Failed to update service config: {e}")

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
                        # Don't continue - still need to process course_members below
                else:
                    # Service exists but no token - need to create one
                    click.echo(f"    ⚠️  No token found for service, creating new token...")
                    need_to_create_token = True

            # Only create service if it doesn't exist yet
            if not existing_services or len(existing_services) == 0:
                # 1. Look up ServiceType by path
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
                    email=service_config.user.email,
                    given_name=service_config.user.given_name,
                    family_name=service_config.user.family_name,
                    config=service_config.config or {},
                    enabled=True
                )

                service = run_async(service_client.service_accounts(service_create))
                click.echo(f"    ✅ Created service: {service_config.slug}")
                need_to_create_token = True  # New service always needs a token

            # 4. Create API Token (if needed)
            if need_to_create_token:
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

                    # Debug: Log what we're sending
                    payload = token_create.model_dump(mode='json')
                    click.echo(f"    🔍 Debug - Token creation payload:")
                    click.echo(f"       user_id: {payload.get('user_id')}")
                    click.echo(f"       token length: {len(payload.get('predefined_token', ''))}")
                    click.echo(f"       scopes: {payload.get('scopes')}")
                    click.echo(f"       expires_at: {payload.get('expires_at')}")

                    # Call admin endpoint (use mode='json' to serialize datetime objects)
                    token_response = custom_client.create("api-tokens/admin/create", payload)
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

            # 5. Process course memberships for this service's user
            if service_config.course_members:
                click.echo(f"    📚 Processing {len(service_config.course_members)} course memberships...")
                for cm_dep in service_config.course_members:
                    try:
                        course = None

                        # Resolve course by path or ID
                        if cm_dep.is_path_based:
                            # Find organization
                            orgs = run_async(org_client.list(OrganizationQuery(path=cm_dep.organization)))
                            if not orgs:
                                click.echo(f"      ⚠️  Organization not found: {cm_dep.organization}")
                                continue
                            org = orgs[0]

                            # Find course family
                            families = run_async(family_client.list(CourseFamilyQuery(
                                organization_id=str(org.id),
                                path=cm_dep.course_family
                            )))
                            if not families:
                                click.echo(f"      ⚠️  Course family not found: {cm_dep.course_family}")
                                continue
                            family = families[0]

                            # Find course
                            courses = run_async(course_client.list(CourseQuery(
                                course_family_id=str(family.id),
                                path=cm_dep.course
                            )))
                            if not courses:
                                click.echo(f"      ⚠️  Course not found: {cm_dep.course}")
                                continue
                            course = courses[0]

                        elif cm_dep.is_id_based:
                            # Direct course lookup by ID
                            course = run_async(course_client.get(cm_dep.id))
                            if not course:
                                click.echo(f"      ⚠️  Course not found: {cm_dep.id}")
                                continue

                        if course:
                            # Handle course group (typically services don't need groups, but support it)
                            course_group_id = None
                            if cm_dep.group:
                                groups = run_async(course_group_client.list(CourseGroupQuery(
                                    course_id=str(course.id),
                                    title=cm_dep.group
                                )))
                                if groups:
                                    course_group_id = str(groups[0].id)

                            # Check if course member already exists
                            existing_members = run_async(course_member_client.list(CourseMemberQuery(
                                user_id=str(service.user_id),
                                course_id=str(course.id)
                            )))

                            if existing_members:
                                existing_member = existing_members[0]
                                # Check if we need to update role
                                if existing_member.course_role_id != cm_dep.role:
                                    member_update = {'course_role_id': cm_dep.role}
                                    if course_group_id:
                                        member_update['course_group_id'] = course_group_id
                                    run_async(course_member_client.update(str(existing_member.id), member_update))
                                    click.echo(f"      ✅ Updated course membership: {course.path} as {cm_dep.role}")
                                else:
                                    click.echo(f"      ℹ️  Already member of course: {course.path} as {cm_dep.role}")
                            else:
                                # Create new course member
                                member_create = CourseMemberCreate(
                                    user_id=str(service.user_id),
                                    course_id=str(course.id),
                                    course_role_id=cm_dep.role,
                                    course_group_id=course_group_id
                                )

                                run_async(course_member_client.create(member_create))
                                click.echo(f"      ✅ Added to course: {course.path} as {cm_dep.role}")

                    except Exception as e:
                        click.echo(f"      ⚠️  Failed to add course membership: {e}")

        except Exception as e:
            click.echo(f"    ❌ Failed to deploy service {service_config.slug}: {e}")
            import traceback
            click.echo(f"    {traceback.format_exc()}")

    click.echo(f"\n✅ Phase 1 complete: {len(deployed_services)} services deployed")
    return deployed_services


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

    click.echo(f"\n🔗 Phase 2: Linking services to courses and creating contents...")

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
