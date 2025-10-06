#!/usr/bin/env python3
"""
Test script to demonstrate SSO authentication with API calls.

This script shows how to:
1. Login via SSO and get a session token
2. Use the token to make authenticated API calls

NOTE: This is not a pytest test - it's a standalone script.
Run directly with: python test_sso_api.py
"""

import requests
import sys
from urllib.parse import urlparse, parse_qs
import pytest

# API base URL
API_BASE = "http://localhost:8000"

@pytest.mark.skip(reason="SSO is not fully implemented yet and requires manual interaction")
def test_sso_login():
    """Simulate SSO login flow and extract token."""
    print("Testing SSO login flow...")
    
    # Note: In a real application, this would be done through a browser
    # For testing, you need to:
    # 1. Navigate to http://localhost:8000/auth/keycloak/login in a browser
    # 2. Login with credentials
    # 3. Copy the token from the redirect URL
    
    print("\nTo get a token:")
    print("1. Open: http://localhost:8000/auth/keycloak/login")
    print("2. Login with: admin/admin")
    print("3. Copy the 'token' parameter from the redirect URL")
    print("\nEnter the token: ", end="")
    
    token = input().strip()
    
    if not token:
        print("No token provided!")
        sys.exit(1)
    
    return token

@pytest.mark.skip(reason="Not a pytest test - standalone script for manual SSO testing")
def test_api_with_token():
    """Placeholder for pytest collection - actual test requires manual token input"""
    pass

def _test_api_with_token(token):
    """Test API calls using the SSO token."""
    print(f"\nTesting API with token: {token[:20]}...")
    
    # Headers with Bearer token
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Test endpoints
    endpoints = [
        "/users/me",  # Get current user info
        "/roles",     # List roles (requires auth)
        "/courses",   # List courses
    ]
    
    for endpoint in endpoints:
        print(f"\nTesting {endpoint}...")
        try:
            response = requests.get(f"{API_BASE}{endpoint}", headers=headers)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                print("Response:", response.json())
            else:
                print("Error:", response.text)
                
        except Exception as e:
            print(f"Request failed: {e}")

@pytest.mark.skip(reason="Not a pytest test - standalone script for manual SSO testing")
def test_protected_endpoint():
    """Placeholder for pytest collection - actual test requires manual token input"""
    pass

def _test_protected_endpoint(token):
    """Test a protected admin endpoint."""
    print("\n\nTesting protected admin endpoint...")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Try to list auth providers (admin only)
    response = requests.get(f"{API_BASE}/auth/admin/plugins", headers=headers)
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("Success! User has admin access.")
        print("Available plugins:", response.json())
    elif response.status_code == 401:
        print("Unauthorized - invalid or expired token")
    elif response.status_code == 403:
        print("Forbidden - user doesn't have admin role")
    else:
        print("Error:", response.text)

def main():
    """Main test flow."""
    print("=== SSO API Authentication Test ===\n")
    
    # Get token from SSO login
    token = test_sso_login()
    
    # Test API calls with token
    test_api_with_token(token)
    
    # Test protected endpoint
    test_protected_endpoint(token)
    
    print("\n\n=== Test Complete ===")
    print("\nTo use the token in your own code:")
    print(f'headers = {{"Authorization": "Bearer {token[:20]}..."}}')
    print('response = requests.get("http://localhost:8000/users/me", headers=headers)')

if __name__ == "__main__":
    main()