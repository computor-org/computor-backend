import os
import click
from functools import wraps
from computor_cli.config import CLIAuthConfig, CredentialsAuth, ApiTokenAuth

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


def _heartbeat_credentials(base_url: str, username: str, password: str) -> bool:
    """Test credentials by calling POST /auth/login (bearer token flow)."""
    from httpx import Client

    try:
        with Client(base_url=base_url) as client:
            response = client.post("/auth/login", json={"username": username, "password": password})
            return response.status_code == 200
    except Exception as e:
        click.echo(e)
        return False


def _heartbeat_api_token(base_url: str, token: str) -> bool:
    """Test an API token by calling GET /user with the X-API-Token header."""
    from httpx import Client

    try:
        with Client(base_url=base_url, headers={"X-API-Token": token}) as client:
            response = client.get("/user")
            return response.status_code == 200
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
    if profile.credentials is not None:
        click.echo(f"Auth: credentials (user: {profile.credentials.username})")
    elif profile.api_token is not None:
        click.echo(f"Auth: api-token ({profile.api_token.token[:8]}...)")
    else:
        click.echo("Auth: none")


@click.command()
@click.option("--auth-method", "-a", type=click.Choice(["credentials", "token"]), prompt="Auth method")
@click.option("--base-url", "-b", prompt="API url")
@click.option("--username", "-u")
@click.option("--password", "-p")
@click.option("--token", "-t")
def login(auth_method, base_url, username, password, token):
    """Authenticate with a Computor API server."""

    if auth_method == "credentials":
        username = username if username is not None else click.prompt("Username")
        password = password if password is not None else click.prompt("Password", hide_input=True)

        if not _heartbeat_credentials(base_url, username, password):
            click.echo("Authentication failed.")
            return False

        config = CLIAuthConfig(
            api_url=base_url,
            credentials=CredentialsAuth(username=username, password=password),
        )

    elif auth_method == "token":
        token = token if token is not None else click.prompt("API token", hide_input=True)

        if not _heartbeat_api_token(base_url, token):
            click.echo("Authentication failed.")
            return False

        config = CLIAuthConfig(
            api_url=base_url,
            api_token=ApiTokenAuth(token=token),
        )

    init_filesystem()
    config.write_deployment(get_profile_path())
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
    """
    from computor_client import ComputorClient

    if auth.credentials is not None:
        cache_key = f"{auth.api_url}:credentials:{auth.credentials.username}"
    elif auth.api_token is not None:
        cache_key = f"{auth.api_url}:token:{auth.api_token.token[:8]}"
    else:
        cache_key = auth.api_url

    if not force_new and cache_key in _client_cache:
        return _client_cache[cache_key]

    if auth.credentials is not None:
        client = ComputorClient(base_url=auth.api_url)
        await client.login(
            username=auth.credentials.username,
            password=auth.credentials.password,
        )
    elif auth.api_token is not None:
        client = ComputorClient(
            base_url=auth.api_url,
            headers={"X-API-Token": auth.api_token.token},
        )
    else:
        raise NotImplementedError("No authentication method configured")

    _client_cache[cache_key] = client
    return client


def clear_client_cache():
    """Clear the cached clients. Useful when authentication credentials change."""
    global _client_cache
    _client_cache = {}
