"""
API Token generation and management commands.

Provides CLI commands for generating and managing API tokens for service accounts.
"""

import click
import secrets
import hashlib
from datetime import datetime, timedelta


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
@click.argument('token')
def verify(token):
    """
    Verify token format and show prefix/hash.

    Useful for debugging - shows what the token_prefix and token_hash should be.

    Example:
        ctutor token verify ctp_abc123def456ghi789jkl012mno345pq
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


if __name__ == '__main__':
    token()
