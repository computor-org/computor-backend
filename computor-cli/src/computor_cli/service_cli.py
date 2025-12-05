"""
Service account management CLI commands.

Provides CLI commands for creating and managing service accounts via the REST API.
"""

import click
from datetime import datetime, timedelta

from computor_cli.auth import authenticate, get_computor_client
from computor_cli.config import CLIAuthConfig
from computor_cli.utils import run_async
from computor_types.services import ServiceCreate, ServiceQuery, ServiceUpdate
from computor_types.api_tokens import ApiTokenCreate, ApiTokenQuery


@click.group()
def service():
    """Manage service accounts."""
    pass


@service.command()
@click.option('--slug', required=True, help='Unique identifier for the service (lowercase, alphanumeric, dots, hyphens)')
@click.option('--name', required=True, help='Human-readable service name')
@click.option('--service-type', required=True, help='Service type path (e.g., "testing.temporal", "testing.matlab")')
@click.option('--description', help='Service description')
@click.option('--username', help='Username for service user (defaults to slug)')
@click.option('--email', help='Email for service user')
@click.option('--enabled/--disabled', default=True, help='Whether the service is enabled (default: enabled)')
@click.option('--create-token', is_flag=True, help='Also create an API token for this service')
@click.option('--token-name', help='Name for the API token (used with --create-token)')
@click.option('--token-expires-days', type=int, default=365, help='Token expiration in days (default: 365)')
@authenticate
def create(slug, name, service_type, description, username, email, enabled, create_token, token_name, token_expires_days, auth: CLIAuthConfig):
    """
    Create a new service account via the REST API.

    This creates a service account with an associated user (is_service=True).

    Examples:
        # Basic service creation
        computor service create --slug my-worker --name "My Worker" --service-type testing.temporal

        # With API token
        computor service create --slug my-worker --name "My Worker" --service-type testing.temporal \\
            --create-token --token-name "Worker Token"

        # Full options
        computor service create \\
            --slug temporal-worker-python \\
            --name "Python Testing Worker" \\
            --service-type testing.temporal \\
            --description "Temporal worker for Python test execution" \\
            --email worker-python@service.local \\
            --create-token \\
            --token-name "Python Worker Token" \\
            --token-expires-days 365
    """
    client = run_async(get_computor_client(auth))

    click.echo(f"\n{'='*70}")
    click.echo("🤖 Creating Service Account")
    click.echo(f"{'='*70}")

    # Build service creation payload
    service_create = ServiceCreate(
        slug=slug,
        name=name,
        service_type=service_type,
        description=description,
        username=username or slug,
        email=email,
        enabled=enabled,
    )

    click.echo(f"\n📝 Service Details:")
    click.echo(f"   Slug:         {slug}")
    click.echo(f"   Name:         {name}")
    click.echo(f"   Type:         {service_type}")
    click.echo(f"   Username:     {username or slug}")
    if description:
        click.echo(f"   Description:  {description}")
    if email:
        click.echo(f"   Email:        {email}")
    click.echo(f"   Enabled:      {enabled}")

    try:
        # Create service via API
        service_result = run_async(client.services.create(service_create))

        click.echo(f"\n✅ Service created successfully!")
        click.echo(f"   Service ID:   {service_result.id}")
        click.echo(f"   User ID:      {service_result.user_id}")

        # Create API token if requested
        if create_token:
            click.echo(f"\n{'='*70}")
            click.echo("🔑 Creating API Token")
            click.echo(f"{'='*70}")

            token_create = ApiTokenCreate(
                name=token_name or f"{name} Token",
                description=f"API token for {name}",
                user_id=str(service_result.user_id),
                scopes=[],  # Backend assigns default scopes based on service type
                expires_at=datetime.utcnow() + timedelta(days=token_expires_days) if token_expires_days else None,
            )

            token_result = run_async(client.api_tokens.create(token_create))

            click.echo(f"\n✅ API Token created!")
            click.echo(f"   Token ID:     {token_result.id}")
            click.echo(f"   Prefix:       {token_result.token_prefix}...")
            click.echo(f"   Scopes:       {token_result.scopes}")
            if token_result.expires_at:
                click.echo(f"   Expires:      {token_result.expires_at.isoformat()}")

            click.echo(f"\n{'='*70}")
            click.echo("🔐 FULL TOKEN (save this - shown only once!):")
            click.echo(f"{'='*70}")
            click.secho(f"\n{token_result.token}\n", fg="green", bold=True)

            click.echo(f"{'='*70}")
            click.echo("📋 Environment Variable:")
            click.echo(f"{'='*70}")
            env_name = slug.upper().replace('-', '_').replace('.', '_')
            click.echo(f"\nexport {env_name}_TOKEN='{token_result.token}'")

        click.echo(f"\n{'='*70}")
        click.echo("✅ Service account setup complete!")
        click.echo(f"{'='*70}\n")

    except Exception as e:
        click.secho(f"\n❌ Failed to create service: {e}", fg="red", err=True)
        raise click.Abort()


@service.command()
@click.option('--slug', help='Filter by service slug')
@click.option('--enabled/--disabled', default=None, help='Filter by enabled status')
@click.option('--format', '-f', type=click.Choice(['table', 'json', 'simple']), default='table', help='Output format')
@authenticate
def list(slug, enabled, format, auth: CLIAuthConfig):
    """
    List service accounts.

    Examples:
        # List all services
        computor service list

        # Filter by slug
        computor service list --slug temporal-worker

        # Only enabled services
        computor service list --enabled

        # JSON output
        computor service list --format json
    """
    client = run_async(get_computor_client(auth))

    query = ServiceQuery(
        slug=slug,
        enabled=enabled,
    )

    try:
        services = run_async(client.services.list(query))

        if format == 'json':
            import json
            output = [s.model_dump(mode='json') for s in services]
            click.echo(json.dumps(output, indent=2, default=str))
            return

        if not services:
            click.echo("No services found.")
            return

        if format == 'simple':
            for svc in services:
                status = "✅" if svc.enabled else "❌"
                click.echo(f"{status} {svc.slug} ({svc.name})")
            return

        # Table format
        click.echo(f"\n{'='*90}")
        click.echo(f"{'Slug':<30} {'Name':<25} {'Enabled':<10} {'Last Seen':<20}")
        click.echo(f"{'='*90}")

        for svc in services:
            status = "Yes" if svc.enabled else "No"
            last_seen = svc.last_seen_at.strftime("%Y-%m-%d %H:%M") if svc.last_seen_at else "Never"
            click.echo(f"{svc.slug:<30} {svc.name:<25} {status:<10} {last_seen:<20}")

        click.echo(f"{'='*90}")
        click.echo(f"Total: {len(services)} service(s)\n")

    except Exception as e:
        click.secho(f"\n❌ Failed to list services: {e}", fg="red", err=True)
        raise click.Abort()


@service.command()
@click.argument('slug')
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table', help='Output format')
@authenticate
def get(slug, format, auth: CLIAuthConfig):
    """
    Get details of a service account by slug.

    Examples:
        computor service get temporal-worker-python
        computor service get temporal-worker-python --format json
    """
    client = run_async(get_computor_client(auth))

    try:
        # Find service by slug
        services = run_async(client.services.list(ServiceQuery(slug=slug)))

        if not services:
            click.secho(f"❌ Service not found: {slug}", fg="red", err=True)
            raise click.Abort()

        svc = services[0]

        if format == 'json':
            import json
            click.echo(json.dumps(svc.model_dump(mode='json'), indent=2, default=str))
            return

        # Table format
        click.echo(f"\n{'='*70}")
        click.echo(f"🤖 Service: {svc.name}")
        click.echo(f"{'='*70}")
        click.echo(f"   ID:           {svc.id}")
        click.echo(f"   Slug:         {svc.slug}")
        click.echo(f"   Name:         {svc.name}")
        click.echo(f"   Description:  {svc.description or '(none)'}")
        click.echo(f"   User ID:      {svc.user_id}")
        click.echo(f"   Enabled:      {'Yes' if svc.enabled else 'No'}")
        click.echo(f"   Last Seen:    {svc.last_seen_at.strftime('%Y-%m-%d %H:%M:%S') if svc.last_seen_at else 'Never'}")
        click.echo(f"   Config:       {svc.config}")
        click.echo(f"{'='*70}\n")

        # Also show tokens for this service
        try:
            tokens = run_async(client.api_tokens.list(ApiTokenQuery(user_id=str(svc.user_id))))
            if tokens:
                click.echo(f"🔑 API Tokens ({len(tokens)}):")
                for token in tokens:
                    status = "🔴 Revoked" if token.revoked_at else "🟢 Active"
                    expires = token.expires_at.strftime("%Y-%m-%d") if token.expires_at else "Never"
                    click.echo(f"   {status} {token.token_prefix}... - {token.name} (expires: {expires})")
                click.echo("")
        except Exception:
            pass  # Ignore token listing errors

    except click.Abort:
        raise
    except Exception as e:
        click.secho(f"\n❌ Failed to get service: {e}", fg="red", err=True)
        raise click.Abort()


@service.command()
@click.argument('slug')
@click.option('--name', help='Update service name')
@click.option('--description', help='Update service description')
@click.option('--enabled/--disabled', default=None, help='Enable or disable the service')
@authenticate
def update(slug, name, description, enabled, auth: CLIAuthConfig):
    """
    Update a service account.

    Examples:
        # Update name
        computor service update temporal-worker-python --name "New Name"

        # Disable service
        computor service update temporal-worker-python --disabled

        # Update multiple fields
        computor service update temporal-worker-python --name "Updated Worker" --description "New description"
    """
    client = run_async(get_computor_client(auth))

    # Check if any update fields are provided
    if name is None and description is None and enabled is None:
        click.secho("❌ No update fields provided. Use --name, --description, or --enabled/--disabled.", fg="red", err=True)
        raise click.Abort()

    try:
        # Find service by slug
        services = run_async(client.services.list(ServiceQuery(slug=slug)))

        if not services:
            click.secho(f"❌ Service not found: {slug}", fg="red", err=True)
            raise click.Abort()

        svc = services[0]

        # Build update payload
        update_data = ServiceUpdate(
            name=name,
            description=description,
            enabled=enabled,
        )

        # Update service
        updated = run_async(client.services.update(str(svc.id), update_data))

        click.echo(f"\n✅ Service updated: {slug}")
        if name:
            click.echo(f"   Name: {updated.name}")
        if description is not None:
            click.echo(f"   Description: {updated.description}")
        if enabled is not None:
            click.echo(f"   Enabled: {'Yes' if updated.enabled else 'No'}")
        click.echo("")

    except click.Abort:
        raise
    except Exception as e:
        click.secho(f"\n❌ Failed to update service: {e}", fg="red", err=True)
        raise click.Abort()


@service.command()
@click.argument('slug')
@click.option('--name', help='Token name (default: "{service name} Token")')
@click.option('--expires-days', type=int, default=365, help='Token expiration in days (default: 365, 0 for never)')
@authenticate
def create_token(slug, name, expires_days, auth: CLIAuthConfig):
    """
    Create a new API token for an existing service.

    Examples:
        # Create token with default settings
        computor service create-token temporal-worker-python

        # Custom token name
        computor service create-token temporal-worker-python --name "Production Token"

        # Token that never expires
        computor service create-token temporal-worker-python --expires-days 0
    """
    client = run_async(get_computor_client(auth))

    try:
        # Find service by slug
        services = run_async(client.services.list(ServiceQuery(slug=slug)))

        if not services:
            click.secho(f"❌ Service not found: {slug}", fg="red", err=True)
            raise click.Abort()

        svc = services[0]

        # Create token
        token_name = name or f"{svc.name} Token"
        expires_at = datetime.utcnow() + timedelta(days=expires_days) if expires_days > 0 else None

        token_create = ApiTokenCreate(
            name=token_name,
            description=f"API token for {svc.name}",
            user_id=str(svc.user_id),
            scopes=[],  # Backend assigns default scopes
            expires_at=expires_at,
        )

        token_result = run_async(client.api_tokens.create(token_create))

        click.echo(f"\n{'='*70}")
        click.echo(f"🔑 API Token Created for: {svc.name}")
        click.echo(f"{'='*70}")
        click.echo(f"\n   Token ID:     {token_result.id}")
        click.echo(f"   Name:         {token_result.name}")
        click.echo(f"   Prefix:       {token_result.token_prefix}...")
        click.echo(f"   Scopes:       {token_result.scopes}")
        if token_result.expires_at:
            click.echo(f"   Expires:      {token_result.expires_at.isoformat()}")
        else:
            click.echo(f"   Expires:      Never")

        click.echo(f"\n{'='*70}")
        click.echo("🔐 FULL TOKEN (save this - shown only once!):")
        click.echo(f"{'='*70}")
        click.secho(f"\n{token_result.token}\n", fg="green", bold=True)

        click.echo(f"{'='*70}")
        click.echo("📋 Environment Variable:")
        click.echo(f"{'='*70}")
        env_name = slug.upper().replace('-', '_').replace('.', '_')
        click.echo(f"\nexport {env_name}_TOKEN='{token_result.token}'\n")

    except click.Abort:
        raise
    except Exception as e:
        click.secho(f"\n❌ Failed to create token: {e}", fg="red", err=True)
        raise click.Abort()


@service.command()
@click.argument('slug')
@click.option('--token-prefix', help='Specific token prefix to revoke (e.g., "ctp_abc123")')
@click.option('--all', 'revoke_all', is_flag=True, help='Revoke all tokens for this service')
@click.option('--reason', help='Reason for revocation')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation')
@authenticate
def revoke_tokens(slug, token_prefix, revoke_all, reason, yes, auth: CLIAuthConfig):
    """
    Revoke API tokens for a service.

    Examples:
        # Revoke a specific token
        computor service revoke-tokens temporal-worker-python --token-prefix ctp_abc123

        # Revoke all tokens
        computor service revoke-tokens temporal-worker-python --all

        # With reason
        computor service revoke-tokens temporal-worker-python --all --reason "Security rotation"
    """
    client = run_async(get_computor_client(auth))

    if not token_prefix and not revoke_all:
        click.secho("❌ Specify --token-prefix or --all", fg="red", err=True)
        raise click.Abort()

    try:
        # Find service by slug
        services = run_async(client.services.list(ServiceQuery(slug=slug)))

        if not services:
            click.secho(f"❌ Service not found: {slug}", fg="red", err=True)
            raise click.Abort()

        svc = services[0]

        # Get tokens for this service
        tokens = run_async(client.api_tokens.list(ApiTokenQuery(user_id=str(svc.user_id), revoked=False)))

        if not tokens:
            click.echo(f"No active tokens found for service: {slug}")
            return

        # Filter tokens to revoke
        tokens_to_revoke = []
        if revoke_all:
            tokens_to_revoke = tokens
        else:
            for token in tokens:
                if token.token_prefix.startswith(token_prefix):
                    tokens_to_revoke.append(token)

        if not tokens_to_revoke:
            click.echo(f"No matching tokens found.")
            return

        # Confirmation
        if not yes:
            click.echo(f"\nTokens to revoke ({len(tokens_to_revoke)}):")
            for token in tokens_to_revoke:
                click.echo(f"  - {token.token_prefix}... ({token.name})")

            if not click.confirm("\nProceed with revocation?"):
                click.echo("Cancelled.")
                return

        # Revoke tokens
        revoked_count = 0
        for token in tokens_to_revoke:
            try:
                run_async(client.api_tokens.revoke(str(token.id)))
                click.echo(f"  ✅ Revoked: {token.token_prefix}...")
                revoked_count += 1
            except Exception as e:
                click.echo(f"  ❌ Failed to revoke {token.token_prefix}...: {e}")

        click.echo(f"\n✅ Revoked {revoked_count} token(s) for service: {slug}\n")

    except click.Abort:
        raise
    except Exception as e:
        click.secho(f"\n❌ Failed to revoke tokens: {e}", fg="red", err=True)
        raise click.Abort()


@service.command()
@authenticate
def list_types(auth: CLIAuthConfig):
    """
    List available service types.

    Examples:
        computor service list-types
    """
    client = run_async(get_computor_client(auth))

    try:
        service_types = run_async(client.service_types.list())

        if not service_types:
            click.echo("No service types found.")
            return

        click.echo(f"\n{'='*70}")
        click.echo("📋 Available Service Types")
        click.echo(f"{'='*70}")
        click.echo(f"\n{'Path':<30} {'Name':<30}")
        click.echo(f"{'-'*30} {'-'*30}")

        for st in service_types:
            click.echo(f"{st.path:<30} {st.name:<30}")

        click.echo(f"\nTotal: {len(service_types)} service type(s)\n")

    except Exception as e:
        click.secho(f"\n❌ Failed to list service types: {e}", fg="red", err=True)
        raise click.Abort()


if __name__ == '__main__':
    service()
