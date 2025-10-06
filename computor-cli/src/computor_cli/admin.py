import click
from computor_cli.auth import authenticate, get_custom_client
from computor_cli.config import CLIAuthConfig
from computor_cli.crud import handle_api_exceptions

@click.command()
@click.option("--username", "-u", "username", prompt=True)
@click.option("--password", "-p", "password", prompt=True, hide_input=True)
@authenticate
@handle_api_exceptions
def change_password(username, password, auth: CLIAuthConfig):

  resp = get_custom_client(auth)

  print(resp.create("/user/password",{"username": username,"password": password}))

@click.group()
def admin():
    pass

admin.add_command(change_password,"password")