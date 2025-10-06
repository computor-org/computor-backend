#!/usr/bin/env python3
"""
Test script for Keycloak authentication integration.

Run this after starting the Docker services:
1. docker-compose -f docker-compose-dev.yaml up -d keycloak postgres redis
2. Wait for Keycloak to start (check http://localhost:8180)
3. python test_keycloak.py
"""

import asyncio
import os
from datetime import datetime

# Add the source directory to Python path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from computor_backend.auth.keycloak import KeycloakAuthPlugin, KeycloakConfig
from computor_backend.plugins.base import AuthStatus
import pytest

@pytest.mark.asyncio
@pytest.mark.skipif(os.environ.get("SKIP_KEYCLOAK_TESTS", "true").lower() == "true", 
                    reason="Keycloak service not available")
async def test_keycloak_auth():
    """Test Keycloak authentication functionality."""
    print("Testing Keycloak Authentication Integration")
    print("=" * 50)
    
    # Create configuration
    config = KeycloakConfig(
        server_url=os.environ.get("KEYCLOAK_SERVER_URL", "http://localhost:8180"),
        realm=os.environ.get("KEYCLOAK_REALM", "computor"),
        client_id=os.environ.get("KEYCLOAK_CLIENT_ID", "computor-backend"),
        client_secret=os.environ.get("KEYCLOAK_CLIENT_SECRET", "computor-backend-secret"),
        verify_ssl=False  # For local testing
    )
    
    print(f"Server URL: {config.server_url}")
    print(f"Realm: {config.realm}")
    print(f"Client ID: {config.client_id}")
    print()
    
    # Create plugin instance
    plugin = KeycloakAuthPlugin(config)
    
    try:
        # Initialize plugin
        print("1. Initializing plugin...")
        await plugin.initialize()
        print("   ✓ Plugin initialized successfully")
        print()
        
        # Test login URL generation
        print("2. Testing login URL generation...")
        redirect_uri = "http://localhost:8000/auth/keycloak/callback"
        login_url = plugin.get_login_url(redirect_uri, "test-state")
        print(f"   ✓ Login URL: {login_url}")
        print()
        
        # Test direct authentication (if enabled in Keycloak)
        print("3. Testing direct authentication...")
        result = await plugin.authenticate({
            "username": "demo_admin",
            "password": "admin123"
        })
        
        if result.status == AuthStatus.SUCCESS:
            print("   ✓ Authentication successful!")
            print(f"   - User: {result.user_info.username}")
            print(f"   - Email: {result.user_info.email}")
            print(f"   - Name: {result.user_info.full_name}")
            print(f"   - Groups: {result.user_info.groups}")
            print(f"   - Token expires: {result.expires_at}")
            
            # Test get user info
            print()
            print("4. Testing get user info...")
            if result.access_token:
                user_info = await plugin.get_user_info(result.access_token)
                print("   ✓ User info retrieved successfully")
                print(f"   - Provider ID: {user_info.provider_id}")
                print(f"   - Email verified: {user_info.attributes.get('email_verified')}")
        else:
            print(f"   ✗ Authentication failed: {result.error_message}")
            print("   Note: Direct password authentication may be disabled in Keycloak.")
            print("   Use the OAuth flow instead via the web interface.")
        
        print()
        print("5. Testing metadata...")
        metadata = plugin.metadata
        print(f"   - Provider: {metadata.provider_name}")
        print(f"   - Type: {metadata.provider_type.value}")
        print(f"   - Version: {metadata.version}")
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        print("   Make sure Keycloak is running and accessible at", config.server_url)
        print("   Check that the realm and client are properly configured.")
    
    finally:
        # Shutdown plugin
        await plugin.shutdown()
        print()
        print("Test completed!")


if __name__ == "__main__":
    # Load environment variables if .env exists
    from pathlib import Path
    env_file = Path(__file__).parent / ".env.dev"
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
        print(f"Loaded environment from {env_file}")
        print()
    
    # Run the test
    asyncio.run(test_keycloak_auth())