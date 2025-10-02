import click
import yaml
from pathlib import Path
from ctutor_backend.cli.auth import authenticate
from ctutor_backend.cli.config import CLIAuthConfig
from ctutor_backend.cli.crud import handle_api_exceptions
from ctutor_backend.interface.deployments_refactored import UsersDeploymentConfig

@click.command()
@click.option("--file", "-f", required=True, help="Path to users deployment YAML file")
@click.option("--dry-run", is_flag=True, help="Preview what would be imported without making changes")
@authenticate
@handle_api_exceptions
def import_users_yaml(file, dry_run, auth: CLIAuthConfig):
    """Import users from a YAML deployment file into the system."""
    
    # Check if file exists
    yaml_file = Path(file)
    if not yaml_file.exists():
        click.echo(f"Error: File {file} not found", err=True)
        return
    
    # Load and parse the YAML file
    try:
        with open(yaml_file, 'r') as f:
            config_data = yaml.safe_load(f)
        deployment = UsersDeploymentConfig(**config_data)
    except Exception as e:
        click.echo(f"Error loading deployment file: {e}", err=True)
        return
    
    click.echo(f"Loading users from: {yaml_file}")
    click.echo(f"Found {deployment.count_users()} users to import")
    
    if dry_run:
        click.echo(f"\n{click.style('DRY RUN MODE - No changes will be made', fg='yellow')}")
    
    click.echo("-" * 60)
    
    created_users = []
    failed_users = []
    
    for user_account_deployment in deployment.users:
        user_dep = user_account_deployment.user
        gitlab_account = user_account_deployment.get_primary_gitlab_account()
        
        click.echo(f"\nProcessing: {user_dep.display_name} ({user_dep.username})")
        
        if dry_run:
            click.echo(f"  Would create user: {user_dep.email}")
            if gitlab_account:
                click.echo(f"  Would create GitLab account: {gitlab_account.provider_account_id}")
            created_users.append(user_dep)
            continue
        
        # Create the user and account
        try:
            user = create_user_from_deployment(auth, user_dep, gitlab_account)
            if user:
                created_users.append(user_dep)
            else:
                failed_users.append(user_dep)
        except Exception as e:
            click.echo(f"  Error: {e}")
            failed_users.append(user_dep)
    
    # Summary
    click.echo(f"\n{'=' * 60}")
    click.echo("IMPORT SUMMARY")
    click.echo(f"{'=' * 60}")
    click.echo(f"Total users processed: {len(deployment.users)}")
    click.echo(f"Successful: {len(created_users)}")
    click.echo(f"Failed: {len(failed_users)}")
    
    if failed_users:
        click.echo(f"\nFailed users:")
        for user_dep in failed_users:
            click.echo(f"  - {user_dep.display_name} ({user_dep.email})")


@click.group()
def import_group():
    pass

# import_group.add_command(import_users,"users")
import_group.add_command(import_users_yaml,"users-yaml")
