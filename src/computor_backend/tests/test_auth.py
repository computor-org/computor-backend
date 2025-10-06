#!/usr/bin/env python3
"""
Test script to verify Keycloak authentication flow
"""

import asyncio
import sys
import os
import json

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from computor_backend.plugins.registry import get_plugin_registry, initialize_plugin_registry
from computor_backend.database import get_db
from computor_backend.model.auth import User, Account
import pytest

@pytest.mark.asyncio
@pytest.mark.skip(reason="Keycloak testing is not configured yet")
async def test_keycloak_plugin():
    """Test that the Keycloak plugin can be initialized and used"""
    print("🔧 Testing Keycloak plugin initialization...")
    
    # Initialize plugin registry
    registry = await initialize_plugin_registry()
    
    # Get Keycloak plugin
    keycloak_plugin = registry.get_plugin("keycloak")
    if not keycloak_plugin:
        print("❌ Keycloak plugin not found!")
        return False
    
    print("✅ Keycloak plugin loaded successfully!")
    
    # Test login URL generation
    redirect_uri = "http://localhost:8000/auth/keycloak/callback"
    login_url = keycloak_plugin.get_login_url(redirect_uri, state="test123")
    print(f"✅ Login URL: {login_url}")
    
    # Verify the login URL contains expected parameters
    expected_params = ["client_id=computor-backend", "response_type=code", "scope=openid"]
    for param in expected_params:
        if param not in login_url:
            print(f"❌ Missing parameter in login URL: {param}")
            return False
    
    print("✅ Login URL contains all expected parameters!")
    return True

async def check_database_setup():
    """Check that database tables exist and are accessible"""
    print("🗄️  Testing database setup...")
    
    try:
        db = next(get_db())
        
        # Check if we can query the users table
        user_count = db.query(User).count()
        print(f"✅ Users table accessible, current count: {user_count}")
        
        # Check if we can query the accounts table
        account_count = db.query(Account).count()
        print(f"✅ Accounts table accessible, current count: {account_count}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

async def main():
    print("🚀 Testing Keycloak SSO Authentication Setup\n")
    
    # Test 1: Plugin initialization
    plugin_ok = await test_keycloak_plugin()
    
    # Test 2: Database setup
    db_ok = await check_database_setup()
    
    print(f"\n📋 Test Results:")
    print(f"   Plugin System: {'✅ PASS' if plugin_ok else '❌ FAIL'}")
    print(f"   Database Setup: {'✅ PASS' if db_ok else '❌ FAIL'}")
    
    if plugin_ok and db_ok:
        print(f"\n🎉 All tests passed! Ready to test authentication flow.")
        print(f"   1. Visit: http://localhost:8000/auth/keycloak/login")
        print(f"   2. Login with: demo_student / student123")
        print(f"   3. Check database for new user record")
        return True
    else:
        print(f"\n❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)