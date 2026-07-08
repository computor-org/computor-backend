"""Deploy users, accounts, roles, and course memberships."""

import click

from computor_cli.auth import get_computor_client
from computor_client import SyncComputorClient
from computor_cli.config import CLIAuthConfig
from computor_cli.utils import run_async

from computor_types.deployment_config import ComputorDeploymentConfig
from computor_types.users import UserCreate, UserQuery
from computor_types.accounts import AccountCreate, AccountQuery
from computor_types.courses import CourseQuery
from computor_types.course_members import CourseMemberCreate, CourseMemberQuery
from computor_types.course_groups import CourseGroupQuery, CourseGroupCreate
from computor_types.organizations import OrganizationQuery
from computor_types.course_families import CourseFamilyQuery
from computor_types.roles import RoleQuery
from computor_types.user_roles import UserRoleCreate


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
        click.echo(f"\n👤 Processing: {user_dep.display_name} ({user_dep.email})")

        try:
            # Check if user already exists by email
            existing_users = []
            if user_dep.email:
                existing_users.extend(run_async(user_client.list(UserQuery(email=user_dep.email))))

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
                    user_type=user_dep.user_type,
                    properties=user_dep.properties
                )
                
                user = run_async(user_client.create(user_create))
                click.echo(f"  ✅ Created user: {user.display_name}")
                
            # Assign system roles if provided
            if user_dep.roles:
                role_client = client.roles
                user_roles_client = client.user_roles

                for role_id in user_dep.roles:
                    try:
                        # Check if role exists
                        roles = run_async(role_client.list(RoleQuery(id=role_id)))
                        if not roles:
                            click.echo(f"  ⚠️  Role not found: {role_id}")
                            continue

                        # Check if user already has this role
                        # kwargs are passed through as query params by list()
                        existing_user_roles = run_async(user_roles_client.list(
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
                            run_async(user_roles_client.create(user_role_create))
                            click.echo(f"  ✅ Assigned role: {role_id}")
                    except Exception as e:
                        click.echo(f"  ⚠️  Failed to assign role {role_id}: {e}")
                
            # Set password if provided
            if user_dep.password:
                try:
                    # Endpoint has no generated client method; use the sync facade.
                    SyncComputorClient.from_client(client).create(
                        "user/password", {"password": user_dep.password}
                    )
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
