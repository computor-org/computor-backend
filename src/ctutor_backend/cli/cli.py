import click

from .template import template
# from ctutor_backend.cli.experiments import experiment_1
from .crud import rest
from .imports import import_group
# from .release import release
from .auth import change_profile, login
from .test import run_test
from .admin import admin
from .worker import worker
from .generate_types import generate_types
from .generate_clients import generate_clients
from .generate_schema import generate_schema
from .generate_validators import generate_validators_cmd
from .deployment import deployment

@click.group()
def cli():
    pass

cli.add_command(change_profile,"profiles")
cli.add_command(login,"login")
# cli.add_command(release,"release")
cli.add_command(import_group,"import")
cli.add_command(rest,"rest")
cli.add_command(run_test,"test")
# cli.add_command(release_deployment,"apply")
cli.add_command(admin,"admin")
cli.add_command(template,"templates")
cli.add_command(worker,"worker")
cli.add_command(generate_types,"generate-types")
cli.add_command(generate_clients,"generate-clients")
cli.add_command(generate_schema,"generate-schema")
cli.add_command(generate_validators_cmd,"generate-validators")
cli.add_command(deployment,"deployment")
# cli.add_command(experiment_1,"exp")

if __name__ == '__main__':
    cli()
