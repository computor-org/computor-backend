"""
Test API endpoints and interfaces.
"""

import pytest


@pytest.mark.unit
class TestAPIImports:
    """Test that API modules can be imported."""
    
    def test_import_user_api(self):
        """Test importing user API module."""
        import computor_backend.api.user
        assert computor_backend.api.user is not None
    
    def test_import_courses_api(self):
        """Test importing courses API module."""
        import computor_backend.api.courses
        assert computor_backend.api.courses is not None
    
    def test_import_organizations_api(self):
        """Test importing organizations API module."""
        import computor_backend.api.organizations
        assert computor_backend.api.organizations is not None
    
    def test_import_permissions_module(self):
        """Test importing permissions module."""
        import computor_backend.permissions
        import computor_backend.permissions.core
        import computor_backend.permissions.auth
        assert computor_backend.permissions is not None
        assert computor_backend.permissions.core is not None
        assert computor_backend.permissions.auth is not None


@pytest.mark.unit
class TestInterfaceImports:
    """Test that interface schemas can be imported."""
    
    def test_import_courses_interface(self):
        """Test importing courses interface."""
        import computor_types.courses
        assert computor_backend.interface.courses is not None
    
    def test_import_users_interface(self):
        """Test importing users interface."""
        import computor_types.users
        assert computor_backend.interface.users is not None
    
    def test_import_organizations_interface(self):
        """Test importing organizations interface."""
        import computor_types.organizations
        assert computor_backend.interface.organizations is not None