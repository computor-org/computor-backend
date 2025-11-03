"""
CLI commands for documents repository operations.

This module provides commands for syncing documents repositories from GitLab
to the shared filesystem for static file serving.
"""

import click
import re
from functools import wraps
from httpx import ConnectError, HTTPStatusError
from computor_cli.auth import authenticate, get_computor_client
from computor_cli.config import CLIAuthConfig
from computor_cli.utils import run_async


def handle_api_exceptions(func):
    """Handle API exceptions with friendly error messages."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ConnectError as e:
            click.echo(f"Connection to [{click.style(kwargs['auth'].api_url, fg='red')}] could not be established.")
        except HTTPStatusError as e:
            try:
                error_detail = e.response.json()
                message = error_detail.get("detail", str(error_detail))
            except:
                message = e.response.text or str(e)
            click.echo(f"[{click.style(str(e.response.status_code), fg='red')}] {message}")
        except Exception as e:
            click.echo(f"[{click.style('500', fg='red')}] {e.args if e.args != () else 'Internal Server Error'}")

    return wrapper


class SyncHTTPWrapper:
    """Wrapper to make sync HTTP calls using ComputorClient's httpx client configuration."""

    def __init__(self, computor_client):
        """Initialize with a ComputorClient instance."""
        import httpx
        self._client = httpx.Client(
            base_url=str(computor_client._client.base_url),
            headers=dict(computor_client._client.headers),
            timeout=computor_client._client.timeout
        )

    def post(self, path: str, data: dict = None, params: dict = None):
        """POST request."""
        response = self._client.post(path, json=data or {}, params=params)
        response.raise_for_status()
        return response.json() if response.content else None

    def __del__(self):
        """Close client on deletion."""
        if hasattr(self, '_client'):
            self._client.close()


@click.group()
def documents():
    """Manage documents repositories."""
    pass


@documents.command()
@click.argument('course_family_identifier')
@click.option('--force', is_flag=True, help='Force re-sync (delete and re-clone)')
@authenticate
@handle_api_exceptions
def sync(course_family_identifier: str, force: bool, auth: CLIAuthConfig):
    """
    Sync documents repository from GitLab to filesystem.

    This command triggers a Temporal workflow that:
    1. Clones the documents repository from the course family's GitLab group
    2. Filters out sensitive files (.git, .env, etc.)
    3. Syncs files to ${SYSTEM_DEPLOYMENT_PATH}/shared/documents/{org}/{family}/
    4. Makes files accessible via static-server at /docs/{org}/{family}/

    COURSE_FAMILY_IDENTIFIER can be:
    - Course family UUID
    - Course family path (e.g., "tu-graz/programming-in-c")

    Examples:
        # Sync by path
        computor documents sync tu-graz/programming-in-c

        # Sync by UUID with force update
        computor documents sync a1b2c3d4-... --force
    """
    # Authenticate and sync
    async def authenticate_and_sync():
        computor_client = await get_computor_client(auth)

        # Try to find course family by path or UUID
        click.echo(f"🔍 Looking up course family: {course_family_identifier}")

        from computor_types.course_families import CourseFamilyQuery

        # Check if it's a UUID or path
        is_uuid = re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', course_family_identifier, re.IGNORECASE)

        if is_uuid:
            course_family_id = course_family_identifier
            # Fetch the course family to verify it exists
            course_family = await computor_client.course_families.get(course_family_id)
            if not course_family:
                click.secho(f"❌ Course family not found: {course_family_identifier}", fg="red", err=True)
                return
        else:
            # It's a path - query by path
            query = CourseFamilyQuery(path=course_family_identifier)
            results = await computor_client.course_families.list(query)

            if not results or len(results) == 0:
                click.secho(f"❌ Course family not found with path: {course_family_identifier}", fg="red", err=True)
                click.echo("💡 Tip: Use 'computor rest list -t course-families' to see available course families")
                return

            course_family = results[0]
            course_family_id = course_family.id

        click.echo(f"✅ Found course family: {course_family.path}")
        if course_family.organization:
            click.echo(f"   Organization: {course_family.organization.display_name}")

        # Trigger the sync
        click.echo(f"\n🚀 Starting documents sync workflow...")
        if force:
            click.echo("⚠️  Force mode enabled - will delete and re-clone")

        # Use sync wrapper for POST request
        sync_wrapper = SyncHTTPWrapper(computor_client)

        try:
            response = sync_wrapper.post(
                f"/system/course-families/{course_family_id}/sync-documents",
                params={"force_update": force}
            )

            workflow_id = response.get("workflow_id")
            status = response.get("status")

            click.echo(f"\n✅ Workflow started successfully!")
            click.echo(f"   Workflow ID: {workflow_id}")
            click.echo(f"   Status: {status}")

            # Show where files will be accessible (using ltree dot notation)
            org_path = course_family.organization.path if course_family.organization else 'unknown'
            family_path_parts = course_family.path.split('.')
            family_slug = family_path_parts[-1] if family_path_parts else course_family.path

            click.echo(f"\n📁 Files will be accessible at:")
            click.echo(f"   /docs/{org_path}/{family_slug}/")

            click.echo(f"\n💡 Monitor workflow progress:")
            click.echo(f"   - Temporal UI: http://localhost:8088 (search for workflow ID)")
            click.echo(f"   - Check logs: docker logs -f temporal-worker-1")

        except Exception as e:
            click.secho(f"\n❌ Failed to start sync workflow: {e}", fg="red", err=True)
            raise

    try:
        run_async(authenticate_and_sync())
    except Exception as e:
        click.secho(f"❌ Error: {e}", fg="red", err=True)
        import sys
        sys.exit(1)


@documents.command()
@click.argument('course_family_identifier')
@authenticate
@handle_api_exceptions
def info(course_family_identifier: str, auth: CLIAuthConfig):
    """
    Show information about a course family's documents repository.

    COURSE_FAMILY_IDENTIFIER can be:
    - Course family UUID
    - Course family path (e.g., "tu-graz/programming-in-c")

    Examples:
        computor documents info tu-graz/programming-in-c
        computor documents info a1b2c3d4-...
    """
    # Authenticate and get info
    async def authenticate_and_get_info():
        computor_client = await get_computor_client(auth)

        # Try to find course family by path or UUID
        from computor_types.course_families import CourseFamilyQuery

        # Check if it's a UUID or path
        is_uuid = re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', course_family_identifier, re.IGNORECASE)

        if is_uuid:
            course_family_id = course_family_identifier
            course_family = await computor_client.course_families.get(course_family_id)
            if not course_family:
                click.secho(f"❌ Course family not found: {course_family_identifier}", fg="red", err=True)
                return
        else:
            query = CourseFamilyQuery(path=course_family_identifier)
            results = await computor_client.course_families.list(query)

            if not results or len(results) == 0:
                click.secho(f"❌ Course family not found with path: {course_family_identifier}", fg="red", err=True)
                return

            course_family = results[0]

        click.echo("\n" + "="*70)
        click.echo("📚 Documents Repository Information")
        click.echo("="*70)

        # Use the correct attributes from CourseFamilyGet
        click.echo(f"\n🏷️  Course Family: {course_family.title or 'N/A'}")
        click.echo(f"📂 Path: {course_family.path}")

        # Get organization info from CourseFamilyGet.organization (OrganizationGet)
        if course_family.organization:
            org = course_family.organization
            click.echo(f"🏛️  Organization: {org.display_name}")
            org_path = org.path
        else:
            org_path = 'unknown'

        # Determine family slug from path (using dot notation for ltree)
        family_path_parts = course_family.path.split('.')
        family_slug = family_path_parts[-1] if family_path_parts else course_family.path

        # Show GitLab info if available in properties
        if course_family.properties and course_family.properties.gitlab:
            gitlab_config = course_family.properties.gitlab
            click.echo(f"\n🦊 GitLab:")
            if gitlab_config.full_path:
                click.echo(f"   Group Path: {gitlab_config.full_path}")
                if gitlab_config.url:
                    click.echo(f"   Documents Repo: {gitlab_config.url}/{gitlab_config.full_path}/documents")

        click.echo(f"\n🌐 Static File Server:")
        click.echo(f"   URL: /docs/{org_path}/{family_slug}/")
        click.echo(f"   Filesystem: ${{SYSTEM_DEPLOYMENT_PATH}}/shared/documents/{org_path}/{family_slug}/")

        click.echo(f"\n💡 To sync documents:")
        click.echo(f"   computor documents sync {course_family.path}")

        click.echo("="*70 + "\n")

    try:
        run_async(authenticate_and_get_info())
    except Exception as e:
        click.secho(f"❌ Error: {e}", fg="red", err=True)
        import sys
        sys.exit(1)


if __name__ == '__main__':
    documents()
