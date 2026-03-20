"""
API Token generation and management commands.

Provides CLI commands for generating and managing API tokens for service accounts.
"""

import click
import secrets
import hashlib
import base64
from datetime import datetime, timedelta

from computor_cli.auth import authenticate, get_computor_client
from computor_cli.utils import run_async


def generate_api_token():
    """
    Generate a new API token with the format: ctp_<32_random_chars>

    Returns:
        tuple: (full_token, token_prefix, token_hash)
            - full_token: The complete token to give to the user (show once!)
            - token_prefix: First 12 chars for identification
            - token_hash: SHA-256 hash to store in database
    """
    # Generate random token (32 chars of alphanumeric)
    random_part = secrets.token_urlsafe(24)[:32]  # 32 characters
    full_token = f"ctp_{random_part}"

    # Extract prefix (first 12 chars including 'ctp_')
    token_prefix = full_token[:12]

    # Hash the token for storage (SHA-256)
    token_hash = hashlib.sha256(full_token.encode()).digest()

    return full_token, token_prefix, token_hash


@click.group()
def token():
    """Manage API tokens for service accounts."""
    pass


@token.command()
@click.option('--name', required=True, help='Name/description for this token')
@click.option('--scopes', multiple=True, help='Scopes for the token (e.g., "read:courses", "write:results")')
@click.option('--expires-days', type=int, help='Token expiration in days (optional)')
def generate(name, scopes, expires_days):
    """
    Generate a new API token.

    This generates the token locally and prints the values you need to:
    1. Give to the service (full token - shown only once!)
    2. Store in the database (token_prefix and token_hash)

    Example:
        ctutor token generate --name "Python Worker" --scopes "execute:tests" --expires-days 365
    """
    full_token, token_prefix, token_hash = generate_api_token()

    click.echo("\n" + "="*70)
    click.echo("🔑 API Token Generated Successfully")
    click.echo("="*70)

    click.echo(f"\n📝 Token Name: {name}")

    if scopes:
        click.echo(f"🔒 Scopes: {', '.join(scopes)}")
    else:
        click.echo("🔒 Scopes: [] (none specified)")

    if expires_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_days)
        click.echo(f"⏰ Expires: {expires_at.isoformat()} ({expires_days} days)")
    else:
        click.echo("⏰ Expires: Never")

    click.echo("\n" + "="*70)
    click.echo("🔐 FULL TOKEN (save this - shown only once!):")
    click.echo("="*70)
    click.secho(f"\n{full_token}\n", fg="green", bold=True)

    click.echo("="*70)
    click.echo("💾 Database Values (for manual insertion):")
    click.echo("="*70)
    click.echo(f"\ntoken_prefix:  {token_prefix}")
    click.echo(f"token_hash:    {token_hash.hex()}")

    click.echo("\n" + "="*70)
    click.echo("📋 SQL Example:")
    click.echo("="*70)

    scopes_json = '[' + ', '.join(f'"{s}"' for s in scopes) + ']' if scopes else '[]'
    expires_sql = f"'{expires_at.isoformat()}'::timestamp" if expires_days else 'NULL'

    sql = f"""
INSERT INTO api_token (
    name,
    user_id,
    token_prefix,
    token_hash,
    scopes,
    expires_at
) VALUES (
    '{name}',
    '<user_id_here>',  -- Replace with actual user UUID
    '{token_prefix}',
    '\\\\x{token_hash.hex()}'::bytea,
    '{scopes_json}'::jsonb,
    {expires_sql}
);
"""

    click.echo(sql)

    click.echo("="*70)
    click.echo("⚠️  SECURITY NOTES:")
    click.echo("="*70)
    click.echo("1. The full token is shown only once - save it securely!")
    click.echo("2. Never commit tokens to git or share them publicly")
    click.echo("3. The token_hash is what gets stored in the database")
    click.echo("4. Users authenticate with: X-API-Token: <full_token>")
    click.echo("="*70 + "\n")


@token.command()
@click.option('--name', '-n', default=None, help='Human-readable token name')
@click.option('--scopes', '-s', multiple=True, help='Token scopes (e.g., "read:courses", "execute:tests"). Repeatable.')
@click.option('--user-id', '-u', default=None, help='User ID to create the token for (admin only, defaults to yourself)')
@click.option('--expires-days', '-e', type=int, default=None, help='Token expiration in days (default: never)')
@click.option('--description', '-d', default=None, help='Token description/purpose')
@click.option('--quiet', '-q', is_flag=True, help='Output only the token string (for scripting)')
@authenticate
def create(name, scopes, user_id, expires_days, description, quiet, auth):
    """
    Create an API token via the backend API.

    Requires an active login session (run 'computor login' first).
    The token is generated server-side and shown only once.
    Prompts for any field not provided via flags.

    \b
    Examples:
        # Interactive — prompts for everything
        computor token create

        # With scopes and expiry
        computor token create -n "worker" -s "execute:tests" -s "read:courses" -e 365

        # For another user (admin only)
        computor token create -n "service-token" -u <user-uuid> -s "execute:tests"

        # Quiet mode (for scripts)
        export TOKEN=$(computor token create -n "ci" -q)
    """
    if name is None:
        name = click.prompt("Token name")

    if not scopes:
        scopes_input = click.prompt(
            "Scopes (comma-separated, or empty for none)",
            default="", show_default=False,
        )
        scopes = tuple(s.strip() for s in scopes_input.split(",") if s.strip()) if scopes_input else ()

    if user_id is None and not quiet:
        user_id_input = click.prompt("User ID (enter for yourself)", default="me", show_default=True)
        user_id = None if user_id_input.lower() == "me" else user_id_input

    if expires_days is None and not quiet:
        expires_input = click.prompt("Expires in days (enter for never)", default="never", show_default=True)
        expires_days = None if expires_input.lower() == "never" else int(expires_input)

    if description is None and not quiet:
        description = click.prompt("Description (optional)", default="", show_default=False) or None

    from computor_types.api_tokens import ApiTokenCreate

    expires_at = None
    if expires_days is not None:
        expires_at = datetime.utcnow() + timedelta(days=expires_days)

    token_data = ApiTokenCreate(
        name=name,
        scopes=list(scopes),
        user_id=user_id,
        expires_at=expires_at,
        description=description,
    )

    client = run_async(get_computor_client(auth))
    try:
        result = run_async(client.tokens.api_tokens(data=token_data))
    except Exception as e:
        click.secho(f"Error creating token: {e}", fg="red", err=True)
        raise SystemExit(1)

    if quiet:
        click.echo(result.token)
        return

    click.echo()
    click.echo("=" * 60)
    click.echo("API Token Created")
    click.echo("=" * 60)
    click.secho(f"\n  {result.token}\n", fg="green", bold=True)
    click.echo("=" * 60)
    click.echo(f"  ID:       {result.id}")
    click.echo(f"  Name:     {result.name}")
    click.echo(f"  Prefix:   {result.token_prefix}")
    click.echo(f"  User:     {result.user_id}")
    click.echo(f"  Scopes:   {', '.join(result.scopes) if result.scopes else '(none)'}")
    if result.expires_at:
        click.echo(f"  Expires:  {result.expires_at.isoformat()}")
    else:
        click.echo(f"  Expires:  never")
    click.echo("=" * 60)
    click.echo("  Save this token now — it cannot be retrieved later.")
    click.echo("=" * 60)
    click.echo()


@token.command()
@authenticate
def list_tokens(auth):
    """
    List your API tokens.

    Shows all active tokens for the authenticated user.
    """
    client = run_async(get_computor_client(auth))
    try:
        tokens = run_async(client.tokens.get_api_tokens())
    except Exception as e:
        click.secho(f"Error listing tokens: {e}", fg="red", err=True)
        raise SystemExit(1)

    if not tokens:
        click.echo("No API tokens found.")
        return

    click.echo(f"\n{'Name':<30} {'Prefix':<15} {'Scopes':<30} {'Expires':<20}")
    click.echo("-" * 95)
    for t in tokens:
        expires = t.expires_at.strftime("%Y-%m-%d") if t.expires_at else "never"
        scopes = ", ".join(t.scopes) if t.scopes else "(none)"
        revoked = " [REVOKED]" if t.revoked_at else ""
        click.echo(f"{t.name:<30} {t.token_prefix:<15} {scopes:<30} {expires:<20}{revoked}")
    click.echo()


@token.command()
@click.argument('token_id')
@click.option('--reason', '-r', default=None, help='Revocation reason')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation')
@authenticate
def revoke(token_id, reason, yes, auth):
    """
    Revoke an API token by ID.

    The token will be immediately invalidated.

    Example:
        computor token revoke <token-uuid>
    """
    if not yes:
        click.confirm(f"Revoke token {token_id}?", abort=True)

    client = run_async(get_computor_client(auth))
    try:
        params = {}
        if reason:
            params["reason"] = reason
        run_async(client.tokens.delete_api_tokens(token_id=token_id, **params))
    except Exception as e:
        click.secho(f"Error revoking token: {e}", fg="red", err=True)
        raise SystemExit(1)

    click.secho(f"Token {token_id} revoked.", fg="yellow")


@token.command()
@click.option('--count', '-n', default=1, type=int, help='Number of tokens to generate (default: 1)')
@click.option('--quiet', '-q', is_flag=True, help='Output only the token (for scripts/env files)')
def generate_token(count, quiet):
    """
    Generate API token(s) for environment variables.

    This is a simple command that generates valid API tokens you can immediately
    use in .env files, Docker Compose, or deployment.yaml.

    Examples:
        # Generate one token
        computor token generate-token

        # Generate two tokens (e.g., for Python and MATLAB workers)
        computor token generate-token --count 2

        # Generate token for scripting (quiet mode)
        export MY_TOKEN=$(computor token generate-token --quiet)
    """
    if quiet:
        for _ in range(count):
            full_token, _, _ = generate_api_token()
            click.echo(full_token)
    else:
        click.echo("\n" + "="*70)
        click.echo("🔑 API Token Generator")
        click.echo("="*70)
        click.echo("\nGenerate valid API tokens for use in:")
        click.echo("  • .env files")
        click.echo("  • Docker Compose environment variables")
        click.echo("  • deployment.yaml predefined tokens")
        click.echo("\n" + "="*70)

        tokens = []
        for i in range(count):
            full_token, token_prefix, _ = generate_api_token()
            tokens.append(full_token)

            if count > 1:
                click.echo(f"\n🔐 Token {i+1}/{count}:")
            else:
                click.echo(f"\n🔐 Token:")
            click.secho(f"   {full_token}", fg="green", bold=True)

        if count > 1:
            click.echo("\n" + "="*70)
            click.echo("💾 Copy to .env file:")
            click.echo("="*70)
            for i, token in enumerate(tokens, 1):
                click.echo(f"TOKEN_{i}={token}")

        click.echo("\n" + "="*70)
        click.echo("📋 Usage in deployment.yaml:")
        click.echo("="*70)
        click.echo("""
services:
  - slug: my-service
    api_token:
      token: "${MY_SERVICE_TOKEN}"
""")

        click.echo("="*70)
        click.echo("⚠️  IMPORTANT:")
        click.echo("="*70)
        click.echo("  • Store tokens securely!")
        click.echo("  • Never commit tokens to git")
        click.echo("  • Tokens shown here are valid and ready to use")
        click.echo("="*70 + "\n")


@token.command()
@click.argument('token')
def verify(token):
    """
    Verify token format and show prefix/hash.

    Useful for debugging - shows what the token_prefix and token_hash should be.

    Example:
        computor token verify ctp_abc123def456ghi789jkl012mno345pq
    """
    if not token.startswith('ctp_'):
        click.secho("❌ Invalid token format! Token must start with 'ctp_'", fg="red", err=True)
        return

    if len(token) != 36:  # ctp_ (4) + 32 chars = 36
        click.secho(f"⚠️  Warning: Token length is {len(token)}, expected 36 characters", fg="yellow")

    token_prefix = token[:12]
    token_hash = hashlib.sha256(token.encode()).digest()

    click.echo("\n" + "="*70)
    click.echo("🔍 Token Verification")
    click.echo("="*70)
    click.echo(f"\nFull Token:    {token}")
    click.echo(f"Token Prefix:  {token_prefix}")
    click.echo(f"Token Hash:    {token_hash.hex()}")
    click.echo("\n" + "="*70 + "\n")


@token.command()
@click.option('--service-name', required=True, help='Name of the service')
@click.option('--token-name', required=True, help='Name/description for the token')
@click.option('--scopes', multiple=True, help='Token scopes')
@click.option('--expires-days', type=int, default=365, help='Token expiration in days (default: 365)')
def generate_for_service(service_name, token_name, scopes, expires_days):
    """
    Generate a token with instructions for creating a service account.

    This is a helper that generates a token AND shows you the full workflow
    for creating a service account with the token.

    Example:
        ctutor token generate-for-service \\
            --service-name "temporal-worker-python" \\
            --token-name "Python Worker Token" \\
            --scopes "execute:tests" "read:courses" \\
            --expires-days 365
    """
    full_token, token_prefix, token_hash = generate_api_token()

    click.echo("\n" + "="*70)
    click.echo("🤖 Service Account + API Token Generator")
    click.echo("="*70)

    click.echo(f"\n🏷️  Service Name: {service_name}")
    click.echo(f"🔑 Token Name: {token_name}")

    if scopes:
        click.echo(f"🔒 Scopes: {', '.join(scopes)}")
    else:
        scopes = ["execute:tests", "read:courses"]  # Sensible defaults
        click.echo(f"🔒 Scopes (auto): {', '.join(scopes)}")

    expires_at = datetime.utcnow() + timedelta(days=expires_days)
    click.echo(f"⏰ Expires: {expires_at.isoformat()} ({expires_days} days)")

    click.echo("\n" + "="*70)
    click.echo("🔐 FULL TOKEN (save this - shown only once!):")
    click.echo("="*70)
    click.secho(f"\n{full_token}\n", fg="green", bold=True)

    click.echo("="*70)
    click.echo("📋 Complete Setup SQL:")
    click.echo("="*70)

    scopes_json = '[' + ', '.join(f'"{s}"' for s in scopes) + ']'

    sql = f"""
-- 1. Create service user
INSERT INTO "user" (
    username,
    given_name,
    family_name,
    email,
    is_service
) VALUES (
    '{service_name}',
    '{service_name}',
    'Service',
    '{service_name}@computor.local',
    true
) RETURNING id;  -- Save this ID for next steps

-- 2. Create service metadata (use the UUID from step 1)
INSERT INTO service (
    slug,
    name,
    service_type,
    user_id,
    enabled
) VALUES (
    '{service_name}',
    '{service_name}',
    'temporal_worker',  -- Change if different type
    '<user_id_from_step_1>',
    true
);

-- 3. Create API token (use the UUID from step 1)
INSERT INTO api_token (
    name,
    user_id,
    token_prefix,
    token_hash,
    scopes,
    expires_at
) VALUES (
    '{token_name}',
    '<user_id_from_step_1>',
    '{token_prefix}',
    '\\\\x{token_hash.hex()}'::bytea,
    '{scopes_json}'::jsonb,
    '{expires_at.isoformat()}'::timestamp
);
"""

    click.echo(sql)

    click.echo("="*70)
    click.echo("🚀 Usage Instructions:")
    click.echo("="*70)
    click.echo(f"1. Run the SQL above to create the service account")
    click.echo(f"2. Set environment variable for the service:")
    click.secho(f"   export COMPUTOR_API_TOKEN='{full_token}'", fg="cyan")
    click.echo(f"3. The service authenticates with:")
    click.secho(f"   X-API-Token: {full_token}", fg="cyan")
    click.echo("="*70 + "\n")


@token.command()
@click.option('--count', '-n', default=1, type=int, help='Number of secrets to generate (default: 1)')
@click.option('--quiet', '-q', is_flag=True, help='Output only the secret (for scripts/env files)')
def generate_secret(count, quiet):
    """
    Generate TOKEN_SECRET for environment variables.

    Generates Fernet-compatible secret keys (base64-encoded 32 bytes) for use
    in TOKEN_SECRET environment variable.

    Note: TOKEN_SECRET is used for deprecated password encryption. New systems
    should use Argon2 hashing instead. However, this is still needed for
    backward compatibility.

    Examples:
        # Generate one secret
        computor token generate-secret

        # Generate multiple secrets
        computor token generate-secret --count 3

        # Generate secret for scripting (quiet mode)
        export TOKEN_SECRET=$(computor token generate-secret --quiet)
    """
    if quiet:
        for _ in range(count):
            secret = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
            click.echo(secret)
    else:
        click.echo("\n" + "="*70)
        click.echo("🔒 TOKEN_SECRET Generator")
        click.echo("="*70)
        click.echo("\nGenerate Fernet-compatible secret keys for:")
        click.echo("  • TOKEN_SECRET environment variable")
        click.echo("  • Password encryption (deprecated - use Argon2 instead)")
        click.echo("  • .env files and Docker Compose")
        click.echo("\n" + "="*70)

        secrets_list = []
        for i in range(count):
            secret = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
            secrets_list.append(secret)

            if count > 1:
                click.echo(f"\n🔑 Secret {i+1}/{count}:")
            else:
                click.echo(f"\n🔑 Secret:")
            click.secho(f"   {secret}", fg="yellow", bold=True)

        if count > 1:
            click.echo("\n" + "="*70)
            click.echo("💾 Copy to .env file:")
            click.echo("="*70)
            for i, secret in enumerate(secrets_list, 1):
                click.echo(f"TOKEN_SECRET_{i}={secret}")

        click.echo("\n" + "="*70)
        click.echo("📋 Usage in .env file:")
        click.echo("="*70)
        click.echo('TOKEN_SECRET="<your_secret_here>"')

        click.echo("\n" + "="*70)
        click.echo("⚠️  SECURITY NOTES:")
        click.echo("="*70)
        click.echo("  • Store secrets securely!")
        click.echo("  • Never commit secrets to git")
        click.echo("  • TOKEN_SECRET is for legacy password encryption")
        click.echo("  • New systems should use Argon2 hashing instead")
        click.echo("="*70 + "\n")


if __name__ == '__main__':
    token()
