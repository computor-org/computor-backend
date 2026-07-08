"""
CLI commands for deployment operations.

This module provides commands for working with ComputorDeploymentConfig,
including generating example configurations and deploying hierarchies.

Domain orchestration helpers live in the ``computor_cli.deploy`` package
(split out in TASK-503); this module is the thin click-command layer.
"""

import sys
import os
import yaml
import click
from pathlib import Path

from computor_types.deployment_config import (
    ComputorDeploymentConfig,
    HierarchicalOrganizationConfig,
    HierarchicalCourseFamilyConfig,
    HierarchicalCourseConfig,
    EXAMPLE_DEPLOYMENT,
    EXAMPLE_MULTI_DEPLOYMENT,
)
from computor_cli.auth import authenticate, get_computor_client
from computor_client import SyncComputorClient
from computor_cli.config import CLIAuthConfig
from computor_cli.utils import run_async

from computor_cli.deploy.users import _deploy_users
from computor_cli.deploy.services import (
    _deploy_services,
    _link_backends_to_deployed_courses,
    _update_token_scopes,
)
from computor_cli.deploy.examples import _upload_examples_from_directory
from computor_cli.deploy.extensions import _upload_extensions_from_config


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
        # Use the example from deployment_config.py
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
        # Expand ${ENV_VAR} in per-course git tokens from the operator's shell
        # (client-side, like the service tokens below) so the backend receives a
        # real GitLab credential rather than a literal placeholder.
        for _org in config.organizations:
            for _family in _org.course_families:
                for _course in _family.courses:
                    if _course.git and _course.git.token:
                        _course.git.token = os.path.expandvars(_course.git.token)
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
                        if course.git:
                            g = course.git
                            if g.delivery == "download":
                                click.echo(f"      Git: download (provider: {g.provider or 'none'})")
                            else:
                                where = g.provider or "unconfigured"
                                if g.base_url:
                                    where += f" @ {g.base_url}"
                                modes = ", ".join(g.student_repo_modes or []) or "none"
                                click.echo(f"      Git: {where} — modes: {modes}")

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
                    click.echo(f"  - {user.display_name} ({user.email})")
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
    custom_client = SyncComputorClient.from_client(client)

    # Services will be deployed AFTER hierarchy creation (so courses exist for course_members)
    deployed_services = {}

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
    if not config.organizations and not config.users and not config.services:
        click.echo("\nℹ️ No hierarchy, services, or users defined in configuration; nothing to deploy.")
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

                # Check if post-hierarchy phases are needed (services, content types, contents, or user course assignments)
                needs_post_hierarchy = False

                # Check for services (always need to wait since services are deployed after hierarchy)
                if config.services:
                    needs_post_hierarchy = True

                # Check for courses with services/content
                if not needs_post_hierarchy:
                    for org in config.organizations:
                        for family in org.course_families:
                            for course in family.courses:
                                if course.services or course.content_types or course.contents:
                                    needs_post_hierarchy = True
                                    break
                            if needs_post_hierarchy:
                                break
                        if needs_post_hierarchy:
                            break

                # Check for users with course assignments
                if not needs_post_hierarchy and config.users:
                    for user_config in config.users:
                        if hasattr(user_config, 'course_members') and user_config.course_members:
                            needs_post_hierarchy = True
                            break

                # Force waiting if Phase 2 is needed
                should_wait = wait or needs_post_hierarchy

                if needs_post_hierarchy and not wait:
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
                                click.echo("\n✅ Hierarchy deployment completed successfully!")

                                # Phase 1: Deploy services (AFTER hierarchy, so courses exist for course_members)
                                if config.services:
                                    deployed_services = _deploy_services(config, auth)

                                # Phase 2: Link services/backends to courses and create contents
                                service_course_mapping = _link_backends_to_deployed_courses(
                                    config, auth, deployed_services, True
                                )

                                # Phase 3: Update token scopes with standardized permissions
                                if service_course_mapping and deployed_services:
                                    _update_token_scopes(service_course_mapping, deployed_services, auth)

                                # Phase 4: Deploy users if configured
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
                    click.echo("     No post-hierarchy tasks configured (services, content creation, users).")
            else:
                click.echo("❌ Failed to start deployment", err=True)
                sys.exit(1)

        except Exception as e:
            click.echo(f"❌ Error during deployment: {e}", err=True)
            sys.exit(1)
    else:
        # No hierarchy deployment - deploy services and users if they exist
        if config.services:
            click.echo(f"\n🔧 Deploying {len(config.services)} services (no hierarchy deployment)...")
            deployed_services = _deploy_services(config, auth)
            click.echo("✅ Service deployment completed!")

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
