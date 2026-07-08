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
    from computor_types.yaml_config import read_model_from_yaml_file

    path = get_profile_path()
    if not os.path.exists(path):
        return None
    try:
        return read_model_from_yaml_file(CLIAuthConfig, path)
    except Exception:
        return None


def _verify_token(base_url: str, token: str) -> bool:
    """Verify an API token via GET /user with X-API-Token header."""
    from computor_client import SyncComputorClient
    from computor_client.exceptions import ComputorClientError

    try:
        with SyncComputorClient(base_url, headers={"X-API-Token": token}) as client:
            client.get("/user")
            return True
    except ComputorClientError:
        # A 4xx (e.g. invalid/expired token) means the token is not valid.
        return False
    except Exception as e:
        click.echo(e)
        return False


def _save_profile(config: CLIAuthConfig):
    """Save profile to disk."""
    init_filesystem()
    config.write_yaml(get_profile_path())
    clear_client_cache()


@click.command()
def status():
    """Show the currently active profile."""
    profile = read_active_profile()
    if profile is None:
        click.echo("Not logged in. Run 'computor login' to authenticate.")
        return

    click.echo(f"API:  {profile.api_url}")
    if profile.token is not None:
        click.echo(f"Auth: token ({profile.token[:12]}...)")
    else:
        click.echo("Auth: none")


@click.command()
@click.option("--base-url", "-b", prompt="API url")
@click.option("--token", "-t", help="API token (created in the web UI or via 'computor token')")
def login(base_url, token):
    """Authenticate with a Computor API server using an API token.

    Create a token in the web UI (or with 'computor token') and paste it here.
    """
    if token is None:
        token = click.prompt("API token", hide_input=True)

    if not _verify_token(base_url, token):
        click.echo("Authentication failed: invalid token.")
        return False

    _save_profile(CLIAuthConfig(api_url=base_url, token=token))
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
        from computor_types.yaml_config import read_model_from_yaml_file

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

        auth: CLIAuthConfig = read_model_from_yaml_file(CLIAuthConfig, file)
        kwargs["auth"] = auth
        return func(*args, **kwargs)

    return wrapper

# Global cache for authenticated clients
_client_cache = {}


async def get_computor_client(auth: CLIAuthConfig, force_new: bool = False):
    """Create and return an authenticated ComputorClient."""
    from computor_client import ComputorClient

    if auth.token is None:
        raise NotImplementedError("No API token configured; run 'computor login'")

    cache_key = f"{auth.api_url}:token:{auth.token[:8]}"
    if not force_new and cache_key in _client_cache:
        return _client_cache[cache_key]

    client = ComputorClient(
        base_url=auth.api_url,
        headers={"X-API-Token": auth.token},
    )
    _client_cache[cache_key] = client
    return client


def clear_client_cache():
    """Clear the cached clients."""
    global _client_cache
    _client_cache = {}
