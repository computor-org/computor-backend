import os
import click
from functools import wraps
from computor_cli.config import CLIAuthConfig

HOME_DIR = os.path.expanduser("~") or os.environ.get("HOME") or os.environ.get("USERPROFILE")
COMPUTOR_DIR = os.path.join(HOME_DIR, ".computor")
AUTH_FILE = "active_profile.yaml"


def init_filesystem():
    if not os.path.exists(COMPUTOR_DIR):
        os.makedirs(COMPUTOR_DIR, exist_ok=True)


def get_profile_path() -> str:
    return os.path.join(COMPUTOR_DIR, AUTH_FILE)


def read_active_profile() -> CLIAuthConfig | None:
    from computor_types.deployments_refactored import DeploymentFactory

    path = get_profile_path()
    if not os.path.exists(path):
        return None
    try:
        return DeploymentFactory.read_deployment_from_file(CLIAuthConfig, path)
    except Exception:
        return None


def api_heartbeat(client) -> bool:
    try:
        response = client.get("user")
        if response.status_code == 200:
            return True
    except Exception as e:
        click.echo(e)
    return False


@click.command()
def status():
    """Show the currently active profile."""
    profile = read_active_profile()
    if profile is None:
        click.echo("Not logged in. Run 'computor login' to authenticate.")
        return

    click.echo(f"API: {profile.api_url}")
    if profile.basic is not None:
        click.echo(f"Auth: basic (user: {profile.basic.username})")
    elif profile.gitlab is not None:
        click.echo(f"Auth: gitlab ({profile.gitlab.url})")
    else:
        click.echo("Auth: none")


@click.command()
@click.option("--auth-method", "-a", type=click.Choice(['basic', 'gitlab']), prompt="Auth method")
@click.option("--base-url", "-b", prompt="API url")
@click.option("--username", "-u")
@click.option("--password", "-p")
@click.option("--gitlab-host")
@click.option("--gitlab-token")
def login(auth_method, base_url, username, password, gitlab_host, gitlab_token):
    """Authenticate with a Computor API server."""
    from httpx import Client
    from computor_types.auth import BasicAuthConfig, GLPAuthConfig

    if auth_method == 'basic':
        username = username if username is not None else click.prompt('Username')
        password = password if password is not None else click.prompt('Password', hide_input=True)

        client = Client(base_url=base_url, auth=(username, password))
        cli_auth_config = CLIAuthConfig(
            api_url=base_url,
            basic=BasicAuthConfig(username=username, password=password),
        )

    elif auth_method == 'gitlab':
        gitlab_host = gitlab_host if gitlab_host is not None else click.prompt('Gitlab host')
        gitlab_token = gitlab_token if gitlab_token is not None else click.prompt('Token', hide_input=True)

        glp_auth = GLPAuthConfig(url=gitlab_host, token=gitlab_token)
        client = Client(base_url=base_url)

        from base64 import b64encode
        crypt = b64encode(bytes(glp_auth.model_dump_json(), encoding="utf-8"))
        client.headers.update({"GLP-CREDS": str(crypt, "utf-8")})

        cli_auth_config = CLIAuthConfig(api_url=base_url, gitlab=glp_auth)

    if not api_heartbeat(client):
        click.echo("Authentication failed.")
        return False

    init_filesystem()
    cli_auth_config.write_deployment(get_profile_path())
    clear_client_cache()

    click.echo("Authentication successful!")
    return True


@click.command()
def logout():
    """Remove the active profile and log out."""
    path = get_profile_path()
    if os.path.exists(path):
        os.remove(path)
        clear_client_cache()
        click.echo("Logged out.")
    else:
        click.echo("Not logged in.")


def authenticate(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        from click import get_current_context
        from computor_types.deployments_refactored import DeploymentFactory

        ctx = get_current_context()

        custom_profile = None
        if ctx.obj and 'PROFILE_PATH' in ctx.obj:
            custom_profile = ctx.obj['PROFILE_PATH']

        if custom_profile:
            file = custom_profile
        else:
            file = get_profile_path()

        if not os.path.exists(file):
            if custom_profile:
                click.echo(f"Profile file not found: {custom_profile}")
                raise click.Abort()
            else:
                click.echo("Not logged in. Run 'computor login' to authenticate.")
                raise click.Abort()

        auth: CLIAuthConfig = DeploymentFactory.read_deployment_from_file(CLIAuthConfig, file)
        kwargs["auth"] = auth
        return func(*args, **kwargs)

    return wrapper

# Global cache for authenticated clients (keyed by API URL + auth type)
_client_cache = {}

async def get_computor_client(auth: CLIAuthConfig, force_new: bool = False):
    """
    Create and authenticate a ComputorClient instance (async).

    Clients are cached per API URL and authentication credentials to avoid
    repeated login requests that can trigger rate limiting.

    Args:
        auth: CLI authentication configuration
        force_new: If True, bypass cache and create a new client

    Returns:
        Authenticated ComputorClient instance
    """
    from computor_client import ComputorClient

    # Create a cache key based on API URL and auth credentials
    if auth.basic is not None:
        cache_key = f"{auth.api_url}:basic:{auth.basic.username}"
    elif auth.gitlab is not None:
        cache_key = f"{auth.api_url}:gitlab:{auth.gitlab.url}"
    else:
        cache_key = auth.api_url

    # Return cached client if available and not forcing new
    if not force_new and cache_key in _client_cache:
        return _client_cache[cache_key]

    # Create client
    client = ComputorClient(base_url=auth.api_url)

    # Authenticate based on auth type
    if auth.basic is not None:
        await client.login(
            username=auth.basic.username,
            password=auth.basic.password
        )
    elif auth.gitlab is not None:
        # For GitLab auth, set custom header
        if hasattr(auth.gitlab, 'token') and auth.gitlab.token:
            client._http._headers["X-GitLab-Auth"] = auth.gitlab.token
    else:
        raise NotImplementedError("No authentication method configured")

    # Cache the authenticated client
    _client_cache[cache_key] = client

    return client


def clear_client_cache():
    """Clear the cached clients. Useful when authentication credentials change."""
    global _client_cache
    _client_cache = {}