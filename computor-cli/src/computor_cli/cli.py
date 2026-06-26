import click

# Commands that work with computor-types/computor-client (NO backend dependency)
from computor_cli.auth import login, logout, status
from computor_cli.crud import rest
from computor_cli.deployment import deployment
from computor_cli.api_token_cli import token
from computor_cli.documents import documents
from computor_cli.service_cli import service
from computor_cli.delete import delete
from computor_cli.grading import grading


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

cli.add_command(login, "login")
cli.add_command(logout, "logout")
cli.add_command(status, "status")
cli.add_command(rest, "rest")
cli.add_command(deployment, "deployment")
cli.add_command(token, "token")
cli.add_command(documents, "documents")
cli.add_command(service, "service")
cli.add_command(delete, "delete")
cli.add_command(grading, "grading")

if __name__ == '__main__':
    cli()
