import os
import click
import yaml
from functools import wraps
from computor_cli.config import CLIAuthConfig

HOME_DIR = os.path.expanduser("~") or os.environ.get("HOME") or os.environ.get("USERPROFILE")
COMPUTOR_DIR = os.path.join(HOME_DIR,".computor")
AUTH_FILE = "active_profile.yaml"
PROFILES_FILE = "profiles.yaml"

def init_filesystem():
    if not os.path.exists(COMPUTOR_DIR):
        os.makedirs(COMPUTOR_DIR,exist_ok=True)

    if not os.path.exists(os.path.join(COMPUTOR_DIR,PROFILES_FILE)):
        open(os.path.join(COMPUTOR_DIR,PROFILES_FILE), "x")

def api_heartbeat(client) -> bool:
    try:
        response = client.get("user")
        if response.status_code == 200:
            return True
    except Exception as e:
        click.echo(e)

    return False

def read_auth_profiles() -> list[CLIAuthConfig]:
    init_filesystem()

    filename = os.path.join(COMPUTOR_DIR,PROFILES_FILE)

    with open(filename, "r") as file:
        objs = yaml.safe_load(file)

        if objs == None:
            return []

        entities = []
        for obj in objs:
            entities.append(CLIAuthConfig(**obj))

        return entities

def write_auth_profiles(profiles: list[CLIAuthConfig]):
    profiles_dict = []

    for profile in profiles:
        profiles_dict.append(profile.model_dump(exclude_unset=True))

    filename = os.path.join(COMPUTOR_DIR,PROFILES_FILE)

    with open(filename, "w") as file:
        file.write(yaml.safe_dump(profiles_dict))

@click.command()
def change_profile():
    profiles = read_auth_profiles()

    profile_dict = {}
    for idx, profile in enumerate(profiles):
        idx_str = str(idx+1)

        if profile.gitlab != None:
            click.echo(f"({idx_str}): {profile.gitlab.url}")
        elif profile.basic != None:
            click.echo(f"({idx_str}): {profile.basic.username}")
        else:
            continue

        profile_dict[idx_str] = profile
    
    profile = click.prompt('Profile', type=click.Choice(profile_dict.keys()))

    profile_dict[profile].write_deployment(os.path.join(COMPUTOR_DIR,AUTH_FILE))

    click.echo("Changed profile!")

@click.command()
@click.option("--auth-method", "-a", type=click.Choice(['basic', 'gitlab', 'github']), prompt="Auth method")
@click.option("--base-url", "-b", prompt="API url")
@click.option("--username", "-u")
@click.option("--password", "-p")
@click.option("--gitlab-host")
@click.option("--gitlab-token")
def login(auth_method,base_url,username,password,gitlab_host,gitlab_token):

    from httpx import Client

    if base_url == None:
        base_url = click.prompt('API url')

    from computor_types.auth import BasicAuthConfig, GLPAuthConfig

    profiles = read_auth_profiles()

    cli_auth_config = None

    if auth_method == 'basic':
        username = username if username != None else click.prompt('Username')
        password = password if password != None else click.prompt('Password', hide_input=True)

        basic_auth = (username,password)

        client = Client(base_url=base_url,auth=basic_auth)

        cli_auth_config = CLIAuthConfig(api_url=base_url, basic=BasicAuthConfig(username=username,password=password))

    elif auth_method == 'gitlab':
        gitlab_host = gitlab_host if gitlab_host != None else click.prompt('Gitlab host')
        gitlab_token = gitlab_token if gitlab_token != None else click.prompt('Token', hide_input=True)

        glp_auth = GLPAuthConfig(url=gitlab_host,token=gitlab_token)

        client = Client(base_url=base_url)

        from base64 import b64encode

        crypt = b64encode(bytes(glp_auth.model_dump_json(),encoding="utf-8"))
        client.headers.update({"GLP-CREDS": str(crypt,"utf-8") })

        cli_auth_config = CLIAuthConfig(api_url=base_url, gitlab=glp_auth)

    elif auth_method == 'github':
        click.echo("Not implemented yet")
        return False

    profile_exist = None
    profile_override = False

    for idx, pc in enumerate(profiles):
        if cli_auth_config.api_url != pc.api_url:
            continue

        if cli_auth_config.basic != None and pc.basic != None:
            if pc.basic.username == cli_auth_config.basic.username:
                
                if pc.basic.password != cli_auth_config.basic.password:
                    profile_override = True
                    profiles[idx].basic.password = cli_auth_config.basic.password

                profile_exist = pc
                break

        elif cli_auth_config.gitlab != None and pc.gitlab != None:
            if pc.gitlab.url == cli_auth_config.gitlab.url:

                if pc.gitlab.token != cli_auth_config.gitlab.token:
                    profile_override = True
                    profiles[idx].gitlab.token = cli_auth_config.gitlab.token

                profile_exist = pc
                break
        else:
            continue

    connection = api_heartbeat(client)

    if profile_exist != None and profile_override == False:
        click.echo("Changed profile!")
        return True

    elif profile_exist != None and profile_override == True and connection == True:
        init_filesystem()

        write_auth_profiles(profiles)

        cli_auth_config.write_deployment(os.path.join(COMPUTOR_DIR,AUTH_FILE))

        click.echo("Updated profile!")
        return True

    if connection == True and cli_auth_config != None:
        init_filesystem()

        profiles.append(cli_auth_config)
        write_auth_profiles(profiles)

        cli_auth_config.write_deployment(os.path.join(COMPUTOR_DIR,AUTH_FILE))

        click.echo("Authentication successful!")
        return True

    else:
        click.echo("Authentication failed.")
        return False


def authenticate(func):
    @wraps(func)
    def wrapper(*args, **kwargs):

        file = os.path.join(COMPUTOR_DIR,AUTH_FILE)

        from click import get_current_context
        from computor_types.deployments import DeploymentFactory

        if not os.path.exists(file):
            click.echo("You are not logged in. Please login")
            auth_method = click.prompt("Auth method", type=click.Choice(['basic', 'gitlab', 'github']))

            get_current_context().invoke(login,auth_method=auth_method)

        auth: CLIAuthConfig = DeploymentFactory.read_deployment_from_file(CLIAuthConfig,file)

        kwargs["auth"] = auth

        return func(*args, **kwargs)
    
    return wrapper

async def get_computor_client(auth: CLIAuthConfig):
    """
    Create and authenticate a ComputorClient instance (async).

    Args:
        auth: CLI authentication configuration

    Returns:
        Authenticated ComputorClient instance
    """
    from computor_client import ComputorClient

    # Create client
    client = ComputorClient(base_url=auth.api_url)

    # Authenticate based on auth type
    if auth.basic is not None:
        await client.authenticate(
            username=auth.basic.username,
            password=auth.basic.password
        )
    elif auth.gitlab is not None:
        # For GitLab auth, set custom header
        if hasattr(auth.gitlab, 'token') and auth.gitlab.token:
            client._client.headers["X-GitLab-Auth"] = auth.gitlab.token
    else:
        raise NotImplementedError("No authentication method configured")

    return client