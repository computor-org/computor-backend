import click
from computor_cli.auth import authenticate, get_computor_client
from computor_cli.config import CLIAuthConfig
from computor_cli.crud import handle_api_exceptions
from computor_cli.utils import run_async

@click.command()
@click.option("--username", "-u", "username", prompt=True)
@click.option("--password", "-p", "password", prompt=True, hide_input=True)
@authenticate
@handle_api_exceptions
def change_password(username, password, auth: CLIAuthConfig):

  client = run_async(get_computor_client(auth))

  # Use the users client to change password
  result = client.users.change_password({"username": username, "password": password})
  print(result)

@click.group()
def admin():
    pass

admin.add_command(change_password,"password")