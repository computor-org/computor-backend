#!/usr/bin/env python3
"""
GitLab User Creation Script

This script creates GitLab users based on UserDeployment configurations.
It can be used standalone or imported as a module for automated user provisioning.

Usage:
    python create_gitlab_users.py --config users.yaml
    python create_gitlab_users.py --config users.yaml --dry-run
    python create_gitlab_users.py --interactive
"""

import argparse
import sys
import yaml
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path

# Add the src directory to Python path for module imports
script_path = Path(__file__).resolve()
if script_path.parent.name == 'computor-fullstack':
    # Script is in root directory
    sys.path.insert(0, str(script_path.parent / 'src'))
else:
    # Script is in src/computor_backend/scripts/
    sys.path.insert(0, str(script_path.parent.parent.parent))

# GitLab API client
try:
    from gitlab import Gitlab, GitlabHttpError
except ImportError:
    print("Error: python-gitlab package is required. Install with: pip install python-gitlab")
    sys.exit(1)

# Import our deployment classes
from computor_backend.interface.deployments_refactored import (
    UsersDeploymentConfig, 
    UserAccountDeployment, 
    UserDeployment, 
    AccountDeployment,
    DeploymentFactory
)


@dataclass
class GitLabUserCreationResult:
    """Result of creating a GitLab user."""
    success: bool
    user_id: Optional[int] = None
    username: Optional[str] = None
    email: Optional[str] = None
    error_message: Optional[str] = None
    created_new_user: bool = False
    existing_user: bool = False


class GitLabUserManager:
    """Manager for GitLab user operations."""
    
    def __init__(self, gitlab_url: str, admin_token: str):
        """
        Initialize GitLab user manager.
        
        Args:
            gitlab_url: GitLab instance URL
            admin_token: Admin API token for user creation
        """
        print(f"Connecting to GitLab at: {gitlab_url}")
        self.gitlab = Gitlab(gitlab_url, private_token=admin_token)
        self.gitlab.auth()  # Authenticate the connection
        
        # Verify admin permissions
        try:
            current_user = self.gitlab.user
            print(current_user)
            if not current_user.is_admin:
                raise ValueError("Provided token does not have admin privileges")
            print(f"Connected to GitLab as admin user: {current_user.username}")
        except Exception as e:
            raise ValueError(f"Failed to authenticate or verify admin permissions: {e}")
    
    def user_exists(self, username: str = None, email: str = None) -> Optional[Dict[str, Any]]:
        """
        Check if a user exists in GitLab.
        
        Args:
            username: Username to check
            email: Email to check
            
        Returns:
            User data if exists, None otherwise
        """
        try:
            if username:
                users = self.gitlab.users.list(username=username)
                if users:
                    return users[0]._attrs
            
            if email:
                users = self.gitlab.users.list(search=email)
                for user in users:
                    if user.email == email:
                        return user._attrs
            
            return None
        except GitlabHttpError as e:
            print(f"Error checking user existence: {e}")
            return None
    
    def create_user(self, user_deployment: UserDeployment, account_deployment: Optional[AccountDeployment] = None) -> GitLabUserCreationResult:
        """
        Create a GitLab user from deployment configuration.
        
        Args:
            user_deployment: User deployment configuration
            account_deployment: Optional GitLab account configuration
            
        Returns:
            GitLabUserCreationResult with creation details
        """
        # Determine GitLab-specific values
        gitlab_username = (account_deployment.gitlab_username if account_deployment 
                          else user_deployment.gitlab_username or user_deployment.username)
        gitlab_email = (account_deployment.gitlab_email if account_deployment 
                       else user_deployment.gitlab_email or user_deployment.email)
        
        if not gitlab_username or not gitlab_email:
            return GitLabUserCreationResult(
                success=False,
                error_message="Missing required username or email for GitLab user creation"
            )
        
        # Check if user already exists
        existing_user = self.user_exists(username=gitlab_username, email=gitlab_email)
        if existing_user:
            return GitLabUserCreationResult(
                success=True,
                user_id=existing_user['id'],
                username=existing_user['username'],
                email=existing_user['email'],
                existing_user=True,
                error_message=f"User already exists with ID {existing_user['id']}"
            )
        
        # Prepare user creation data
        user_data = {
            'username': gitlab_username,
            'email': gitlab_email,
            'name': user_deployment.full_name or gitlab_username,
            'password': user_deployment.password or 'ChangeMe123!',
            'skip_confirmation': True,  # Auto-confirm email
            'admin': account_deployment.is_admin if account_deployment else False,
            'can_create_group': account_deployment.can_create_group if account_deployment else True,
            'projects_limit': 1000,  # Default project limit
            'confirm': False,  # Don't require email confirmation
            'approved': True,  # Auto-approve the user
            'external': False,  # Internal user
        }
        
        # Add optional fields if available
        if user_deployment.properties:
            # Add custom properties to bio or external fields
            if 'bio' in user_deployment.properties:
                user_data['bio'] = user_deployment.properties['bio']
            if 'location' in user_deployment.properties:
                user_data['location'] = user_deployment.properties['location']
        
        try:
            # Create the user
            gitlab_user = self.gitlab.users.create(user_data)
            
            # Ensure user is active and unblocked
            try:
                if hasattr(gitlab_user, 'state') and gitlab_user.state == 'blocked':
                    gitlab_user.unblock()
                    print(f"  Unblocked user: {gitlab_user.username}")
                
                # Confirm the user if needed
                if not gitlab_user.confirmed_at:
                    # Force confirm the user by updating them
                    gitlab_user.confirmed_at = True
                    gitlab_user.save()
                    print(f"  Confirmed user: {gitlab_user.username}")
                    
            except Exception as post_create_error:
                print(f"  Warning: Post-creation setup failed: {post_create_error}")
            
            return GitLabUserCreationResult(
                success=True,
                user_id=gitlab_user.id,
                username=gitlab_user.username,
                email=gitlab_user.email,
                created_new_user=True
            )
            
        except GitlabHttpError as e:
            error_msg = f"GitLab API error: {e.error_message}"
            if hasattr(e, 'response_body') and e.response_body:
                error_msg += f" - {e.response_body}"
            
            return GitLabUserCreationResult(
                success=False,
                error_message=error_msg
            )
        except Exception as e:
            return GitLabUserCreationResult(
                success=False,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    def create_users_from_deployment(self, deployment: UsersDeploymentConfig, dry_run: bool = False) -> List[GitLabUserCreationResult]:
        """
        Create multiple GitLab users from a deployment configuration.
        
        Args:
            deployment: Users deployment configuration
            dry_run: If True, only validate and print what would be done
            
        Returns:
            List of creation results
        """
        results = []
        
        print(f"Processing {deployment.count_users()} users...")
        if dry_run:
            print("DRY RUN MODE - No users will be created")
        
        for user_account_deployment in deployment.users:
            user = user_account_deployment.user
            gitlab_account = user_account_deployment.get_primary_gitlab_account()
            
            print(f"\nProcessing user: {user.display_name} ({user.username})")
            
            if dry_run:
                print(f"  Would create GitLab user: {user.username} <{user.email}>")
                if gitlab_account:
                    print(f"  GitLab username: {gitlab_account.gitlab_username}")
                    print(f"  Admin privileges: {gitlab_account.is_admin}")
                    print(f"  Can create groups: {gitlab_account.can_create_group}")
                results.append(GitLabUserCreationResult(
                    success=True,
                    username=user.username,
                    email=user.email
                ))
                continue
            
            # Create the user
            result = self.create_user(user, gitlab_account)
            results.append(result)
            
            if result.success:
                if result.existing_user:
                    print(f"  ✓ User already exists: {result.username} (ID: {result.user_id})")
                else:
                    print(f"  ✓ Created user: {result.username} (ID: {result.user_id})")
            else:
                print(f"  ✗ Failed to create user: {result.error_message}")
        
        return results


def load_deployment_config(config_path: str) -> UsersDeploymentConfig:
    """Load users deployment configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        return UsersDeploymentConfig(**config_data)
    except Exception as e:
        raise ValueError(f"Failed to load deployment configuration: {e}")


def interactive_mode() -> UsersDeploymentConfig:
    """Interactive mode for creating a simple user deployment."""
    print("Interactive GitLab User Creation")
    print("=" * 40)
    
    users = []
    
    while True:
        print(f"\nUser #{len(users) + 1}")
        
        given_name = input("Given name: ").strip()
        family_name = input("Family name: ").strip()
        email = input("Email: ").strip()
        username = input("Username: ").strip()
        
        # Validate required fields
        if not email or not username:
            print("Email and username are required!")
            continue
        
        password = input("Password (leave empty for default): ").strip()
        if not password:
            password = "ChangeMe123!"
        
        is_admin = input("Admin user? (y/N): ").strip().lower() == 'y'
        can_create_group = input("Can create groups? (Y/n): ").strip().lower() != 'n'
        
        user = UserDeployment(
            given_name=given_name or None,
            family_name=family_name or None,
            email=email,
            username=username,
            password=password
        )
        
        account = AccountDeployment(
            provider="gitlab",
            type="oauth",
            provider_account_id=username,
            gitlab_username=username,
            gitlab_email=email,
            is_admin=is_admin,
            can_create_group=can_create_group
        )
        
        users.append(UserAccountDeployment(user=user, accounts=[account]))
        
        add_more = input("\nAdd another user? (y/N): ").strip().lower()
        if add_more != 'y':
            break
    
    return UsersDeploymentConfig(users=users)


def test_connection(gitlab_url: str, admin_token: str):
    """Test GitLab connection and display user info."""
    try:
        GitLabUserManager(gitlab_url, admin_token)
        print("\n✓ Connection test successful!")
        return True
    except Exception as e:
        print(f"\n✗ Connection test failed: {e}")
        return False


def list_users(gitlab_url: str, admin_token: str, show_details: bool = True):
    """List all GitLab users and their status."""
    try:
        manager = GitLabUserManager(gitlab_url, admin_token)
        users = manager.gitlab.users.list(all=True)
        
        print(f"\nFound {len(users)} users in GitLab:")
        print("-" * 80)
        
        for user in users:
            status_info = []
            if hasattr(user, 'state') and user.state:
                status_info.append(f"State: {user.state}")
            if hasattr(user, 'confirmed_at'):
                status_info.append(f"Confirmed: {'Yes' if user.confirmed_at else 'No'}")
            if hasattr(user, 'is_admin') and user.is_admin:
                status_info.append("Admin")
            
            status_str = f" [{', '.join(status_info)}]" if status_info else ""
            
            print(f"  {user.id:3d}: {user.username:20s} <{user.email or 'no-email':30s}>{status_str}")
            
            if show_details and hasattr(user, 'state') and user.state == 'blocked':
                print(f"       ⚠ User is BLOCKED - this may be why they don't appear in UI")
        
        return True
    except Exception as e:
        print(f"Error listing users: {e}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Create GitLab users from deployment configuration')
    parser.add_argument('--config', type=str, help='Path to users deployment YAML file')
    parser.add_argument('--interactive', action='store_true', help='Interactive mode')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no actual user creation)')
    parser.add_argument('--test-connection', action='store_true', help='Test GitLab connection only')
    parser.add_argument('--list-users', action='store_true', help='List all GitLab users and their status')
    parser.add_argument('--gitlab-url', type=str, help='GitLab instance URL')
    parser.add_argument('--admin-token', type=str, help='GitLab admin API token')
    
    args = parser.parse_args()
    
    # Handle test connection mode
    if args.test_connection:
        gitlab_url = args.gitlab_url or input("GitLab URL: ").strip()
        admin_token = args.admin_token or input("Admin API token: ").strip()
        
        # Fix URL format if needed
        if gitlab_url and not gitlab_url.startswith(('http://', 'https://')):
            if 'localhost' in gitlab_url or gitlab_url.startswith('127.0.0.1'):
                gitlab_url = f"http://{gitlab_url}"
            else:
                gitlab_url = f"https://{gitlab_url}"
            print(f"Fixed GitLab URL: {gitlab_url}")
        
        success = test_connection(gitlab_url, admin_token)
        sys.exit(0 if success else 1)
    
    # Handle list users mode
    if args.list_users:
        gitlab_url = args.gitlab_url or input("GitLab URL: ").strip()
        admin_token = args.admin_token or input("Admin API token: ").strip()
        
        # Fix URL format if needed
        if gitlab_url and not gitlab_url.startswith(('http://', 'https://')):
            if 'localhost' in gitlab_url or gitlab_url.startswith('127.0.0.1'):
                gitlab_url = f"http://{gitlab_url}"
            else:
                gitlab_url = f"https://{gitlab_url}"
            print(f"Fixed GitLab URL: {gitlab_url}")
        
        success = list_users(gitlab_url, admin_token)
        sys.exit(0 if success else 1)
    
    # Load deployment configuration
    if args.interactive:
        deployment = interactive_mode()
    elif args.config:
        if not Path(args.config).exists():
            print(f"Error: Configuration file {args.config} not found")
            sys.exit(1)
        deployment = load_deployment_config(args.config)
    else:
        print("Error: Either --config, --interactive, --test-connection, or --list-users must be specified")
        parser.print_help()
        sys.exit(1)
    
    # Get GitLab connection details
    gitlab_url = args.gitlab_url
    admin_token = args.admin_token

    if not gitlab_url:
        gitlab_url = input("GitLab URL: ").strip()
    
    # Fix URL format if protocol is missing
    if gitlab_url and not gitlab_url.startswith(('http://', 'https://')):
        # Default to http for localhost, https for others
        if 'localhost' in gitlab_url or gitlab_url.startswith('127.0.0.1'):
            gitlab_url = f"http://{gitlab_url}"
        else:
            gitlab_url = f"https://{gitlab_url}"
        print(f"Fixed GitLab URL: {gitlab_url}")
    
    if not admin_token and not args.dry_run:
        admin_token = input("Admin API token: ").strip()
    
    if not gitlab_url:
        print("Error: GitLab URL is required")
        sys.exit(1)
    
    if not admin_token and not args.dry_run:
        print("Error: Admin API token is required (unless using --dry-run)")
        sys.exit(1)
    
    # Create GitLab user manager
    if not args.dry_run:
        try:
            gitlab_manager = GitLabUserManager(gitlab_url, admin_token)
        except Exception as e:
            print(f"Error connecting to GitLab: {e}")
            sys.exit(1)
    else:
        gitlab_manager = None  # Not needed for dry run
        print(f"Dry run mode - would connect to: {gitlab_url}")
    
    # Create users
    if args.dry_run:
        # For dry run, create a mock manager that just validates
        class MockGitLabUserManager:
            def create_users_from_deployment(self, deployment, dry_run=True):
                results = []
                print(f"Processing {len(deployment.users)} users in dry-run mode...")
                for user_account in deployment.users:
                    user = user_account.user
                    print(f"  Would create: {user.display_name} ({user.username}) - {user.email}")
                    results.append(GitLabUserCreationResult(
                        success=True,
                        username=user.username,
                        email=user.email
                    ))
                return results
        
        gitlab_manager = MockGitLabUserManager()
    
    results = gitlab_manager.create_users_from_deployment(deployment, dry_run=args.dry_run)
    
    # Summary
    print(f"\n{'=' * 50}")
    print("SUMMARY")
    print(f"{'=' * 50}")
    
    successful = len([r for r in results if r.success])
    failed = len([r for r in results if not r.success])
    existing = len([r for r in results if r.existing_user])
    created = len([r for r in results if r.created_new_user])
    
    print(f"Total users processed: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    if not args.dry_run:
        print(f"Existing users: {existing}")
        print(f"New users created: {created}")
    
    # Show failed users
    failed_results = [r for r in results if not r.success]
    if failed_results:
        print(f"\nFailed users:")
        for result in failed_results:
            print(f"  - {result.username}: {result.error_message}")
    
    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()