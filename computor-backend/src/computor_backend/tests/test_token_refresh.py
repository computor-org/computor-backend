#!/usr/bin/env python3
"""
Test script to demonstrate SSO token refresh functionality.

NOTE: This is not a pytest test - it's a standalone script.
Run directly with: python test_token_refresh.py
"""

import requests
import json
import sys
import time
import pytest

API_BASE = "http://localhost:8000"

@pytest.mark.skip(reason="Not a pytest test - standalone script for manual token testing")
def test_token_refresh():
    """Placeholder for pytest collection - actual test requires manual token input"""
    pass

def _test_token_refresh(refresh_token, provider="keycloak"):
    """Test the token refresh endpoint."""
    
    print(f"\nTesting token refresh for provider: {provider}")
    print(f"Refresh token: {refresh_token[:20]}...")
    
    # Prepare refresh request
    refresh_data = {
        "refresh_token": refresh_token,
        "provider": provider
    }
    
    # Call refresh endpoint
    try:
        response = requests.post(
            f"{API_BASE}/auth/refresh",
            json=refresh_data
        )
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Token refresh successful!")
            print(f"New access token: {data['access_token'][:20]}...")
            print(f"Expires in: {data.get('expires_in', 'N/A')} seconds")
            
            if data.get('refresh_token'):
                print(f"New refresh token: {data['refresh_token'][:20]}...")
                print("\n⚠️  Note: Provider has rotated the refresh token. Use the new one for next refresh.")
            
            return data['access_token']
        else:
            print("\n❌ Token refresh failed!")
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"\n❌ Request failed: {e}")
        return None

@pytest.mark.skip(reason="Not a pytest test - standalone script for manual token testing")
def test_api_with_new_token():
    """Placeholder for pytest collection - actual test requires manual token input"""
    pass

def _test_api_with_new_token(token):
    """Test API call with the refreshed token."""
    
    print("\n\nTesting API call with refreshed token...")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(f"{API_BASE}/auth/me", headers=headers)
        
        if response.status_code == 200:
            user_data = response.json()
            print("✅ API call successful with refreshed token!")
            print(f"User: {user_data['user']['username']}")
            print(f"Roles: {user_data['roles']}")
        else:
            print(f"❌ API call failed: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

def main():
    print("=== SSO Token Refresh Test ===")
    print("\nThis test demonstrates token refresh functionality.")
    print("\nAfter SSO login, you should have received:")
    print("1. An access token (for API calls)")
    print("2. A refresh token (for getting new access tokens)")
    
    print("\n📝 Instructions:")
    print("1. Login via SSO: http://localhost:8000/auth/keycloak/login")
    print("2. Copy the refresh_token from the redirect URL")
    print("3. Enter it below to test refresh")
    
    print("\nEnter your refresh token: ", end="")
    refresh_token = input().strip()
    
    if not refresh_token:
        print("No refresh token provided!")
        sys.exit(1)
    
    # Test token refresh
    new_token = test_token_refresh(refresh_token)
    
    if new_token:
        # Test API call with new token
        test_api_with_new_token(new_token)
        
        print("\n\n📌 Summary:")
        print("1. Refresh tokens can be used to get new access tokens")
        print("2. This avoids requiring users to re-authenticate")
        print("3. Refresh tokens may be rotated by the provider")
        print("4. Store refresh tokens securely - they're long-lived credentials")

if __name__ == "__main__":
    main()