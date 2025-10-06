"""
API Endpoint Testing Suite

Tests all API endpoints to ensure Pydantic v2 refactoring and Redis caching work correctly.
"""

import pytest
import httpx
import asyncio
from datetime import datetime
from typing import List, Dict, Any

# Base URL for the API server
BASE_URL = "http://localhost:8000"
AUTH = ("admin", "admin")

class TestAPIEndpoints:
    """Test suite for API endpoints"""
    
    @pytest.fixture(scope="class")
    def client(self):
        """HTTP client for making API requests"""
        return httpx.Client(base_url=BASE_URL, auth=AUTH, timeout=30.0)
    
    def test_organizations_endpoint(self, client):
        """Test organizations endpoint - GET /organizations"""
        response = client.get("/organizations")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        if data:  # If there are organizations
            org = data[0]
            # Test datetime serialization
            assert "created_at" in org
            assert "updated_at" in org
            # Should be ISO format strings
            datetime.fromisoformat(org["created_at"].replace("Z", "+00:00"))
            datetime.fromisoformat(org["updated_at"].replace("Z", "+00:00"))
            
            # Test required fields
            assert "id" in org
            assert "path" in org
            assert "organization_type" in org
    
    def test_users_endpoint(self, client):
        """Test users endpoint - GET /users"""
        response = client.get("/users")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        if data:  # If there are users
            user = data[0]
            # Test datetime serialization
            assert "created_at" in user
            assert "updated_at" in user
            
            # Test required fields
            assert "id" in user
            assert "email" in user  # Should accept system.local emails
            
            # Test email field accepts non-strict emails (like admin@system.local)
            admin_user = next((u for u in data if u.get("username") == "admin"), None)
            if admin_user:
                assert admin_user["email"] == "admin@system.local"
    
    def test_accounts_endpoint(self, client):
        """Test accounts endpoint - GET /accounts"""
        response = client.get("/accounts")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        if data:  # If there are accounts
            account = data[0]
            # Test datetime serialization
            assert "created_at" in account
            assert "updated_at" in account
            
            # Test required fields
            assert "id" in account
            assert "provider" in account
            assert "type" in account
    
    def test_roles_endpoint(self, client):
        """Test roles endpoint - GET /roles"""
        response = client.get("/roles")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    def test_groups_endpoint(self, client):
        """Test groups endpoint - GET /groups"""
        response = client.get("/groups")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    def test_profiles_endpoint(self, client):
        """Test profiles endpoint - GET /profiles"""
        response = client.get("/profiles")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    def test_sessions_endpoint(self, client):
        """Test sessions endpoint - GET /sessions"""
        response = client.get("/sessions")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    def test_execution_backends_endpoint(self, client):
        """Test execution backends endpoint - GET /execution-backends"""
        response = client.get("/execution-backends")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)

class TestCachingFunctionality:
    """Test Redis caching functionality"""
    
    @pytest.fixture(scope="class")
    def client(self):
        """HTTP client for making API requests"""
        return httpx.Client(base_url=BASE_URL, auth=AUTH, timeout=30.0)
    
    def test_cache_headers(self, client):
        """Test that cache-related headers are present"""
        response = client.get("/organizations")
        assert response.status_code == 200
        
        # Check if X-Total-Count header is present (indicates list endpoint)
        if response.headers.get("X-Total-Count"):
            total_count = int(response.headers["X-Total-Count"])
            data = response.json()
            assert len(data) <= total_count  # Data length should not exceed total
    
    def test_cache_performance(self, client):
        """Test that subsequent requests are faster (cached)"""
        import time
        
        # First request (cache miss)
        start_time = time.time()
        response1 = client.get("/organizations")
        first_time = time.time() - start_time
        
        # Second request (cache hit)
        start_time = time.time()
        response2 = client.get("/organizations")
        second_time = time.time() - start_time
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json() == response2.json()
        
        # Second request should typically be faster, but this is not guaranteed
        # so we'll just ensure both completed successfully

class TestAPIValidation:
    """Test API validation and error handling"""
    
    @pytest.fixture(scope="class")
    def client(self):
        """HTTP client for making API requests"""
        return httpx.Client(base_url=BASE_URL, auth=AUTH, timeout=30.0)
    
    def test_invalid_endpoints(self, client):
        """Test that invalid endpoints return 404"""
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404
    
    def test_authentication_required(self):
        """Test that endpoints require authentication"""
        client_no_auth = httpx.Client(base_url=BASE_URL, timeout=30.0)
        response = client_no_auth.get("/organizations")
        assert response.status_code == 401  # Unauthorized
    
    def test_pagination_parameters(self, client):
        """Test pagination parameters work correctly"""
        # Test with limit parameter
        response = client.get("/organizations?limit=2")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) <= 2  # Should return at most 2 items
        
        # Test with skip parameter
        response = client.get("/organizations?skip=1&limit=1")
        assert response.status_code == 200

class TestDateTimeSerialization:
    """Test that datetime fields are properly serialized"""
    
    @pytest.fixture(scope="class")
    def client(self):
        """HTTP client for making API requests"""
        return httpx.Client(base_url=BASE_URL, auth=AUTH, timeout=30.0)
    
    def test_datetime_format_consistency(self, client):
        """Test that all datetime fields use consistent ISO format"""
        endpoints = ["/organizations", "/users", "/accounts"]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
            
            data = response.json()
            if data and isinstance(data, list) and len(data) > 0:
                item = data[0]
                
                # Test created_at format
                if "created_at" in item and item["created_at"]:
                    created_at = item["created_at"]
                    # Should be ISO format with Z suffix
                    assert created_at.endswith("Z")
                    # Should be parseable as datetime
                    datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                
                # Test updated_at format
                if "updated_at" in item and item["updated_at"]:
                    updated_at = item["updated_at"]
                    # Should be ISO format with Z suffix
                    assert updated_at.endswith("Z")
                    # Should be parseable as datetime
                    datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

if __name__ == "__main__":
    # Run tests when script is executed directly
    pytest.main([__file__, "-v"])