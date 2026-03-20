import os
import click
from functools import wraps
from computor_cli.config import CLIAuthConfig, CredentialsAuth

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


def _verify_credentials(base_url: str, username: str, password: str) -> bool:
    """Test credentials via POST /auth/login."""
    from httpx import Client

    try:
        with Client(base_url=base_url) as client:
            response = client.post("/auth/login", json={"username": username, "password": password})
            return response.status_code == 200
    except Exception as e:
        click.echo(e)
        return False


def _verify_token(base_url: str, token: str) -> bool:
    """Verify an API token via GET /user with X-API-Token header."""
    from httpx import Client

    try:
        with Client(base_url=base_url, headers={"X-API-Token": token}) as client:
            response = client.get("/user")
            return response.status_code == 200
    except Exception as e:
        click.echo(e)
        return False


def _create_token_with_credentials(base_url: str, username: str, password: str) -> str | None:
    """Login with credentials, create an API token, and return it."""
    from httpx import Client

    try:
        with Client(base_url=base_url) as client:
            login_resp = client.post("/auth/login", json={"username": username, "password": password})
            if login_resp.status_code != 200:
                click.echo("Login failed: invalid credentials.")
                return None

            bearer_token = login_resp.json()["access_token"]

            client.headers.update({"Authorization": f"Bearer {bearer_token}"})
            token_resp = client.post("/api-tokens", json={
                "name": f"cli-{username}",
                "description": "Created by computor CLI login",
            })
            if token_resp.status_code != 201:
                click.echo(f"Failed to create API token: {token_resp.text}")
                return None

            return token_resp.json()["token"]

    except Exception as e:
        click.echo(e)
        return None


def _save_profile(config: CLIAuthConfig):
    """Save profile to disk."""
    init_filesystem()
    config.write_deployment(get_profile_path())
    clear_client_cache()


@click.command()
def status():
    """Show the currently active profile."""
    profile = read_active_profile()
    if profile is None:
        click.echo("Not logged in. Run 'computor login' to authenticate.")
        return

    click.echo(f"API:  {profile.api_url}")
    if profile.credentials is not None:
        click.echo(f"Auth: credentials (user: {profile.credentials.username})")
    elif profile.token is not None:
        click.echo(f"Auth: token ({profile.token[:12]}...)")
    else:
        click.echo("Auth: none")


@click.command()
@click.option("--auth-method", "-a", type=click.Choice(["credentials", "token"]), prompt="Auth method")
@click.option("--base-url", "-b", prompt="API url")
@click.option("--username", "-u")
@click.option("--password", "-p")
@click.option("--token", "-t", help="Existing API token (for token auth method)")
def login(auth_method, base_url, username, password, token):
    """Authenticate with a Computor API server.

    \b
    Auth methods:
      credentials  - Store username/password, authenticate via bearer token per request
      token        - Store an API token, either by pasting one (--token) or by
                     logging in with credentials (--username) to create one
    """

    if auth_method == "credentials":
        username = username if username is not None else click.prompt("Username")
        password = password if password is not None else click.prompt("Password", hide_input=True)

        if not _verify_credentials(base_url, username, password):
            click.echo("Authentication failed.")
            return False

        _save_profile(CLIAuthConfig(
            api_url=base_url,
            credentials=CredentialsAuth(username=username, password=password),
        ))
        click.echo("Authentication successful!")
        return True

    elif auth_method == "token":
        if token is None and username is None:
            method = click.prompt(
                "Provide a token or create one with credentials?",
                type=click.Choice(["paste", "create"]),
            )
            if method == "paste":
                token = click.prompt("API token", hide_input=True)
            else:
                username = click.prompt("Username")

        if token is not None:
            if not _verify_token(base_url, token):
                click.echo("Authentication failed: invalid token.")
                return False

            _save_profile(CLIAuthConfig(api_url=base_url, token=token))
            click.echo("Authentication successful!")
            return True
        else:
            password = password if password is not None else click.prompt("Password", hide_input=True)

            token = _create_token_with_credentials(base_url, username, password)
            if token is None:
                return False

            _save_profile(CLIAuthConfig(api_url=base_url, token=token))
            click.echo("Authentication successful! API token created and saved.")
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

# Global cache for authenticated clients
_client_cache = {}


async def get_computor_client(auth: CLIAuthConfig, force_new: bool = False):
    """Create and return an authenticated ComputorClient."""
    from computor_client import ComputorClient

    if auth.token is not None:
        cache_key = f"{auth.api_url}:token:{auth.token[:8]}"
    elif auth.credentials is not None:
        cache_key = f"{auth.api_url}:credentials:{auth.credentials.username}"
    else:
        cache_key = auth.api_url

    if not force_new and cache_key in _client_cache:
        return _client_cache[cache_key]

    if auth.token is not None:
        client = ComputorClient(
            base_url=auth.api_url,
            headers={"X-API-Token": auth.token},
        )
    elif auth.credentials is not None:
        client = ComputorClient(base_url=auth.api_url)
        await client.login(
            username=auth.credentials.username,
            password=auth.credentials.password,
        )
    else:
        raise NotImplementedError("No authentication method configured")

    _client_cache[cache_key] = client
    return client


def clear_client_cache():
    """Clear the cached clients."""
    global _client_cache
    _client_cache = {}
