import click

# Commands that work with computor-types/computor-client (NO backend dependency)
from computor_cli.auth import change_profile, login
from computor_cli.crud import rest
from computor_cli.deployment import deployment

# Commands that require computor_backend (DISABLED - use backend directly for these)
# from computor_cli.admin import admin
# from computor_cli.worker import worker
# from computor_cli.generate_types import generate_types
# from computor_cli.generate_clients import generate_clients
# from computor_cli.generate_schema import generate_schema
# from computor_cli.generate_validators import generate_validators_cmd

# These commands need additional refactoring to use computor_client (future work)
# from computor_cli.template import template
# from computor_cli.imports import import_group
# from computor_cli.test import run_test

@click.group()
@click.option(
    '--profile',
    envvar='COMPUTOR_PROFILE',
    type=click.Path(exists=True),
    help='Path to custom profile YAML file (overrides ~/.computor/active_profile.yaml)'
)
@click.pass_context
def cli(ctx, profile):
    """Computor CLI - Manage courses, users, and deployments."""
    # Store profile path in context for subcommands to access
    ctx.ensure_object(dict)
    ctx.obj['PROFILE_PATH'] = profile

# Available commands (no backend dependency)
cli.add_command(change_profile, "profiles")
cli.add_command(login, "login")
cli.add_command(rest, "rest")
cli.add_command(deployment, "deployment")

# Backend-dependent commands (commented out - use from backend package instead)
# cli.add_command(admin, "admin")
# cli.add_command(worker, "worker")
# cli.add_command(generate_types, "generate-types")
# cli.add_command(generate_clients, "generate-clients")
# cli.add_command(generate_schema, "generate-schema")
# cli.add_command(generate_validators_cmd, "generate-validators")

# Future commands (not yet refactored to use computor_client)
# cli.add_command(import_group, "import")
# cli.add_command(run_test, "test")
# cli.add_command(template, "templates")

if __name__ == '__main__':
    cli()
