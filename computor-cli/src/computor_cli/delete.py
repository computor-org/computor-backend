"""
CLI commands for deletion operations.

Provides commands to delete:
- Organizations and all descendant data
- Course families and all descendant courses
- Courses and all course-specific data
- Examples by identifier prefix pattern
"""

import json
import click
from computor_cli.auth import authenticate, get_computor_client
from computor_cli.config import CLIAuthConfig
from computor_cli.crud import handle_api_exceptions
from computor_cli.utils import run_async


def format_counts(counts: dict) -> str:
    """Format entity counts for display."""
    lines = []
    for key, value in counts.items():
        if value > 0:
            # Convert snake_case to Title Case
            label = key.replace("_", " ").title()
            lines.append(f"  {label}: {value}")
    return "\n".join(lines) if lines else "  (none)"


def confirm_deletion(entity_type: str, entity_id: str, counts: dict, force: bool) -> bool:
    """Prompt user for confirmation before deletion."""
    if force:
        return True

    click.echo(f"\n{click.style('WARNING:', fg='yellow', bold=True)} This will permanently delete:")
    click.echo(format_counts(counts))
    click.echo("")

    return click.confirm(
        f"Are you sure you want to delete {entity_type} '{entity_id}' and all its data?",
        default=False
    )


@click.group()
def delete():
    """Delete commands for organizations, courses, and examples."""
    pass


@delete.command("organization")
@click.argument("organization_id")
@click.option("--dry-run", is_flag=True, default=False, help="Preview what would be deleted without actually deleting")
@click.option("--force", "-f", is_flag=True, default=False, help="Skip confirmation prompt")
@authenticate
@handle_api_exceptions
def delete_organization(organization_id: str, dry_run: bool, force: bool, auth: CLIAuthConfig):
    """
    Delete an organization and ALL its descendant data.

    This includes all course families, courses, members, submissions, results,
    example repositories, and student profiles.

    Users and accounts are NOT deleted - only organization-specific data.
    """
    client = run_async(get_computor_client(auth))

    # Make the API request
    params = {"dry_run": "true" if dry_run else "false"}
    response = run_async(
        client._http.delete(f"/organizations/{organization_id}", params=params)
    )
    response.raise_for_status()
    result = response.json()

    if dry_run:
        click.echo(f"\n{click.style('DRY RUN', fg='cyan', bold=True)} - Preview of deletion for organization {organization_id}:")
        click.echo(f"\nEntities that would be deleted:")
        click.echo(format_counts(result.get("deleted_counts", {})))
        click.echo(f"\nUse without --dry-run to perform actual deletion.")
        return

    # Show preview and ask for confirmation
    if not confirm_deletion("organization", organization_id, result.get("deleted_counts", {}), force):
        # Do a dry run to show counts, then abort
        params = {"dry_run": "true"}
        response = run_async(
            client._http.delete(f"/organizations/{organization_id}", params=params)
        )
        response.raise_for_status()
        preview = response.json()
        click.echo(f"\nWould have deleted:")
        click.echo(format_counts(preview.get("deleted_counts", {})))
        click.echo("\nAborted.")
        return

    # Perform actual deletion
    params = {"dry_run": "false"}
    response = run_async(
        client._http.delete(f"/organizations/{organization_id}", params=params)
    )
    response.raise_for_status()
    result = response.json()

    click.echo(f"\n{click.style('SUCCESS', fg='green', bold=True)} - Deleted organization {organization_id}")
    click.echo(f"\nDeleted entities:")
    click.echo(format_counts(result.get("deleted_counts", {})))
    click.echo(f"\nMinIO objects deleted: {result.get('minio_objects_deleted', 0)}")

    if result.get("errors"):
        click.echo(f"\n{click.style('Warnings:', fg='yellow')}")
        for error in result["errors"]:
            click.echo(f"  - {error}")


@delete.command("course-family")
@click.argument("course_family_id")
@click.option("--dry-run", is_flag=True, default=False, help="Preview what would be deleted without actually deleting")
@click.option("--force", "-f", is_flag=True, default=False, help="Skip confirmation prompt")
@authenticate
@handle_api_exceptions
def delete_course_family(course_family_id: str, dry_run: bool, force: bool, auth: CLIAuthConfig):
    """
    Delete a course family and ALL its descendant courses.

    This includes all courses, members, submissions, results, and messages.
    """
    client = run_async(get_computor_client(auth))

    if dry_run:
        params = {"dry_run": "true"}
        response = run_async(
            client._http.delete(f"/course-families/{course_family_id}", params=params)
        )
        response.raise_for_status()
        result = response.json()

        click.echo(f"\n{click.style('DRY RUN', fg='cyan', bold=True)} - Preview of deletion for course family {course_family_id}:")
        click.echo(f"\nEntities that would be deleted:")
        click.echo(format_counts(result.get("deleted_counts", {})))
        click.echo(f"\nUse without --dry-run to perform actual deletion.")
        return

    # Get preview for confirmation
    params = {"dry_run": "true"}
    response = run_async(
        client._http.delete(f"/course-families/{course_family_id}", params=params)
    )
    response.raise_for_status()
    preview = response.json()

    if not confirm_deletion("course family", course_family_id, preview.get("deleted_counts", {}), force):
        click.echo("Aborted.")
        return

    # Perform actual deletion
    params = {"dry_run": "false"}
    response = run_async(
        client._http.delete(f"/course-families/{course_family_id}", params=params)
    )
    response.raise_for_status()
    result = response.json()

    click.echo(f"\n{click.style('SUCCESS', fg='green', bold=True)} - Deleted course family {course_family_id}")
    click.echo(f"\nDeleted entities:")
    click.echo(format_counts(result.get("deleted_counts", {})))
    click.echo(f"\nMinIO objects deleted: {result.get('minio_objects_deleted', 0)}")

    if result.get("errors"):
        click.echo(f"\n{click.style('Warnings:', fg='yellow')}")
        for error in result["errors"]:
            click.echo(f"  - {error}")


@delete.command("course")
@click.argument("course_id")
@click.option("--dry-run", is_flag=True, default=False, help="Preview what would be deleted without actually deleting")
@click.option("--force", "-f", is_flag=True, default=False, help="Skip confirmation prompt")
@authenticate
@handle_api_exceptions
def delete_course(course_id: str, dry_run: bool, force: bool, auth: CLIAuthConfig):
    """
    Delete a course and ALL its data.

    This includes all members, groups, contents, submissions, results, and messages.
    Users are NOT deleted - only course-specific data.
    """
    client = run_async(get_computor_client(auth))

    if dry_run:
        params = {"dry_run": "true"}
        response = run_async(
            client._http.delete(f"/courses/{course_id}", params=params)
        )
        response.raise_for_status()
        result = response.json()

        click.echo(f"\n{click.style('DRY RUN', fg='cyan', bold=True)} - Preview of deletion for course {course_id}:")
        click.echo(f"\nEntities that would be deleted:")
        click.echo(format_counts(result.get("deleted_counts", {})))
        click.echo(f"\nUse without --dry-run to perform actual deletion.")
        return

    # Get preview for confirmation
    params = {"dry_run": "true"}
    response = run_async(
        client._http.delete(f"/courses/{course_id}", params=params)
    )
    response.raise_for_status()
    preview = response.json()

    if not confirm_deletion("course", course_id, preview.get("deleted_counts", {}), force):
        click.echo("Aborted.")
        return

    # Perform actual deletion
    params = {"dry_run": "false"}
    response = run_async(
        client._http.delete(f"/courses/{course_id}", params=params)
    )
    response.raise_for_status()
    result = response.json()

    click.echo(f"\n{click.style('SUCCESS', fg='green', bold=True)} - Deleted course {course_id}")
    click.echo(f"\nDeleted entities:")
    click.echo(format_counts(result.get("deleted_counts", {})))
    click.echo(f"\nMinIO objects deleted: {result.get('minio_objects_deleted', 0)}")

    if result.get("errors"):
        click.echo(f"\n{click.style('Warnings:', fg='yellow')}")
        for error in result["errors"]:
            click.echo(f"  - {error}")


@delete.command("examples")
@click.argument("identifier_pattern")
@click.option("--repository-id", "-r", default=None, help="Scope deletion to specific repository")
@click.option("--dry-run", is_flag=True, default=False, help="Preview what would be deleted without actually deleting")
@click.option("--force-old", is_flag=True, default=False, help="Delete if deployments are only in archived courses")
@click.option("--force-all", is_flag=True, default=False, help="Delete even if actively deployed (requires confirmation)")
@click.option("--yes", "-y", is_flag=True, default=False, help="Skip confirmation prompt")
@authenticate
@handle_api_exceptions
def delete_examples(identifier_pattern: str, repository_id: str, dry_run: bool, force_old: bool, force_all: bool, yes: bool, auth: CLIAuthConfig):
    """
    Delete examples matching an identifier pattern.

    IDENTIFIER_PATTERN uses Ltree matching with * wildcard:

    \b
    Examples:
      itpcp.progphys.py.*   - all examples under itpcp.progphys.py
      itpcp.*               - all examples under itpcp
      section.topic.ex1     - exact match for section.topic.ex1

    Force levels:
      (no flag)     - Blocks if any active deployments exist
      --force-old   - Allows deletion if deployments are only in archived courses
      --force-all   - Deletes even if actively deployed (orphans deployments)
    """
    client = run_async(get_computor_client(auth))

    # Determine force level
    if force_all:
        force_level = "all"
    elif force_old:
        force_level = "old"
    else:
        force_level = "none"

    # Build query parameters
    params = {
        "identifier_pattern": identifier_pattern,
        "dry_run": "true" if dry_run else "false",
        "force_level": force_level
    }
    if repository_id:
        params["repository_id"] = repository_id

    # Make the API request
    response = run_async(
        client._http.delete("/examples/by-pattern", params=params)
    )
    response.raise_for_status()
    result = response.json()

    if dry_run:
        click.echo(f"\n{click.style('DRY RUN', fg='cyan', bold=True)} - Preview of deletion for pattern '{identifier_pattern}':")
        click.echo(f"\nExamples that would be deleted: {result.get('examples_affected', 0)}")
        click.echo(f"Versions that would be deleted: {result.get('versions_deleted', 0)}")
        click.echo(f"Dependencies that would be deleted: {result.get('dependencies_deleted', 0)}")
        click.echo(f"Deployments that would be orphaned: {result.get('deployment_references_orphaned', 0)}")

        if result.get("examples"):
            click.echo(f"\nExamples:")
            for ex in result["examples"]:
                click.echo(f"  - {ex.get('identifier')} ({ex.get('title', 'No title')})")
                click.echo(f"    Repository: {ex.get('repository_name')}")
                click.echo(f"    Versions: {ex.get('version_count')}")
                if ex.get('deployment_references', 0) > 0:
                    dep_count = ex.get('deployment_references')
                    click.echo(f"    {click.style(f'Deployments: {dep_count}', fg='yellow')}")

        if result.get("errors"):
            click.echo(f"\n{click.style('Errors:', fg='red')}")
            for error in result["errors"]:
                click.echo(f"  - {error}")

        click.echo(f"\nUse without --dry-run to perform actual deletion.")
        return

    # Check for errors (like deployment references without force)
    if result.get("errors") and result.get("examples_affected", 0) == 0:
        click.echo(f"\n{click.style('Cannot delete:', fg='red')}")
        for error in result["errors"]:
            click.echo(f"  - {error}")
        return

    # Confirm deletion
    if not yes:
        click.echo(f"\nThis will delete {result.get('examples_affected', 0)} examples matching '{identifier_pattern}'")

        # Special confirmation for force-all deletion with deployment references
        if force_all and result.get('deployment_references_orphaned', 0) > 0:
            click.echo(click.style(
                f"\n⚠️  DANGER: {result.get('deployment_references_orphaned')} deployment(s) will be ORPHANED!",
                fg='red', bold=True
            ))
            click.echo(click.style(
                "This will break course content that uses these examples.",
                fg='red'
            ))
            click.echo("\nTo confirm this destructive action, type exactly: " + click.style("DELETE AND ORPHAN", fg='yellow', bold=True))

            confirmation = click.prompt("Confirmation", type=str, default="")
            if confirmation != "DELETE AND ORPHAN":
                click.echo("Aborted - confirmation did not match.")
                return
        elif result.get('deployment_references_orphaned', 0) > 0:
            click.echo(click.style(
                f"WARNING: {result.get('deployment_references_orphaned')} deployment(s) will be orphaned!",
                fg='yellow'
            ))

        if not click.confirm("Proceed with deletion?", default=False):
            click.echo("Aborted.")
            return

    # If we got here from a non-dry-run request that succeeded, result already has the deletion info
    click.echo(f"\n{click.style('SUCCESS', fg='green', bold=True)} - Deleted examples matching '{identifier_pattern}'")
    click.echo(f"\nExamples deleted: {result.get('examples_affected', 0)}")
    click.echo(f"Versions deleted: {result.get('versions_deleted', 0)}")
    click.echo(f"Dependencies deleted: {result.get('dependencies_deleted', 0)}")
    click.echo(f"Storage objects deleted: {result.get('storage_objects_deleted', 0)}")

    if result.get('deployment_references_orphaned', 0) > 0:
        click.echo(click.style(
            f"Deployments orphaned: {result.get('deployment_references_orphaned')}",
            fg='yellow'
        ))

    if result.get("errors"):
        click.echo(f"\n{click.style('Warnings:', fg='yellow')}")
        for error in result["errors"]:
            click.echo(f"  - {error}")
