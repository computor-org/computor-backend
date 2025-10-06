"""
Tests for computed properties and advanced DTO functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from computor_types.users import UserGet, UserList
from computor_types.organizations import OrganizationGet, OrganizationType
from computor_types.profiles import ProfileGet
from computor_types.sessions import SessionGet, SessionList
from computor_types.user_groups import UserGroupGet
from computor_types.group_claims import GroupClaimGet
from computor_types.accounts import AccountGet


class TestComputedProperties:
    """Test computed properties across all DTOs"""
    
    def test_user_display_names(self):
        """Test User display name logic"""
        # Full name available
        user_full = UserGet(
            id="123",
            given_name="John",
            family_name="Doe",
            email="john@example.com"
        )
        assert user_full.full_name == "John Doe"
        assert user_full.display_name == "John Doe"
        
        # Only given name
        user_given = UserGet(
            id="123",
            given_name="John",
            email="john@example.com"
        )
        assert user_given.full_name == "John"
        assert user_given.display_name == "John"
        
        # Only username
        user_username = UserGet(
            id="123",
            username="johndoe",
            email="john@example.com"
        )
        assert user_username.full_name == ""
        assert user_username.display_name == "johndoe"
        
        # Fallback to user ID
        user_minimal = UserGet(
            id="123456789",
            email="john@example.com"
        )
        assert user_minimal.full_name == ""
        assert user_minimal.display_name == "User 12345678"
    
    def test_user_list_display_names(self):
        """Test UserList display name logic"""
        # Full name
        user_list = UserList(
            id="123",
            given_name="Jane",
            family_name="Smith",
            email="jane@example.com"
        )
        assert user_list.display_name == "Jane Smith"
        
        # Username fallback
        user_list_username = UserList(
            id="123",
            username="janesmith",
            email="jane@example.com"
        )
        assert user_list_username.display_name == "janesmith"
        
        # ID fallback
        user_list_minimal = UserList(
            id="123456789",
            email="jane@example.com"
        )
        assert user_list_minimal.display_name == "User 12345678"
    
    def test_organization_path_properties(self):
        """Test Organization path-related properties"""
        org = OrganizationGet(
            id="123",
            path="acme.corp.engineering.backend",
            title="Backend Team",
            organization_type=OrganizationType.organization
        )
        
        assert org.path_components == ["acme", "corp", "engineering", "backend"]
        assert org.parent_path == "acme.corp.engineering"
        assert org.display_name == "Backend Team"
        
        # Root organization
        root_org = OrganizationGet(
            id="456",
            path="acme",
            title="ACME Corporation",
            organization_type=OrganizationType.organization
        )
        assert root_org.path_components == ["acme"]
        assert root_org.parent_path is None
        
        # User organization
        user_org = OrganizationGet(
            id="789",
            path="user.johndoe",
            organization_type=OrganizationType.user,
            user_id="user-123"
        )
        assert user_org.display_name == "User Organization (user.johndoe)"
    
    def test_profile_avatar_properties(self):
        """Test Profile avatar-related properties"""
        # Profile with color and image
        profile = ProfileGet(
            id="123",
            user_id="user-123",
            nickname="johndoe",
            avatar_color=16711680,  # Red
            avatar_image="https://example.com/avatar.jpg"
        )
        
        assert profile.avatar_color_hex == "#ff0000"
        assert profile.has_custom_avatar is True
        assert profile.display_name == "johndoe"
        
        # Profile with only color
        profile_color_only = ProfileGet(
            id="123",
            user_id="user-123",
            avatar_color=65280  # Green
        )
        assert profile_color_only.avatar_color_hex == "#00ff00"
        assert profile_color_only.has_custom_avatar is False
        
        # Profile without color
        profile_no_color = ProfileGet(
            id="123456789",
            user_id="user-123"
        )
        assert profile_no_color.avatar_color_hex is None
        assert profile_no_color.display_name == "Profile 12345678"
    
    def test_session_activity_properties(self):
        """Test Session activity-related properties"""
        base_time = datetime(2023, 1, 1, 10, 0, 0)
        
        # Active session
        active_session = SessionGet(
            id="123",
            user_id="user-123",
            session_id="session-active-123456789",
            ip_address="192.168.1.1",
            created_at=base_time
        )
        assert active_session.is_active is True
        assert active_session.session_duration is None
        assert "session-" in active_session.display_name
        assert "Active" in active_session.display_name
        
        # Logged out session
        logged_out_session = SessionGet(
            id="456",
            user_id="user-123",
            session_id="session-logged-out-123456789",
            ip_address="192.168.1.2",
            created_at=base_time,
            logout_time=base_time + timedelta(hours=2, minutes=30)
        )
        assert logged_out_session.is_active is False
        assert logged_out_session.session_duration == 9000  # 2.5 hours in seconds
        assert "Logged out" in logged_out_session.display_name
    
    def test_session_list_properties(self):
        """Test SessionList properties"""
        session_list = SessionList(
            id="123",
            user_id="user-123",
            session_id="session-123",
            ip_address="10.0.0.1",
            logout_time=datetime.now()
        )
        assert session_list.is_active is False
        assert "10.0.0.1" in session_list.display_name
        assert "Logged out" in session_list.display_name
        
        # Active session
        active_session_list = SessionList(
            id="456",
            user_id="user-123",
            session_id="session-456",
            ip_address="10.0.0.2"
        )
        assert active_session_list.is_active is True
        assert "Active" in active_session_list.display_name
    
    def test_user_group_membership_properties(self):
        """Test UserGroup membership properties"""
        # Transient membership
        transient_membership = UserGroupGet(
            user_id="user-123",
            group_id="group-456",
            transient=True
        )
        assert transient_membership.membership_type == "Transient"
        assert transient_membership.membership_identifier == "user-123:group-456"
        
        # Permanent membership
        permanent_membership = UserGroupGet(
            user_id="user-789",
            group_id="group-101",
            transient=False
        )
        assert permanent_membership.membership_type == "Permanent"
        assert permanent_membership.membership_identifier == "user-789:group-101"
        
        # Default (None) should be permanent
        default_membership = UserGroupGet(
            user_id="user-abc",
            group_id="group-def"
        )
        assert default_membership.membership_type == "Permanent"
    
    def test_group_claim_properties(self):
        """Test GroupClaim properties"""
        claim = GroupClaimGet(
            group_id="group-123",
            claim_type="permissions",
            claim_value="read_documents"
        )
        assert claim.display_name == "permissions: read_documents"
        assert claim.claim_identifier == "group-123:permissions:read_documents"
    
    def test_account_display_properties(self):
        """Test Account display properties"""
        account = AccountGet(
            id="123",
            provider="google",
            type="oauth",
            provider_account_id="google-user-12345",
            user_id="user-123"
        )
        assert account.display_name == "google (oauth): google-user-12345"


class TestPropertyEdgeCases:
    """Test edge cases for computed properties"""
    
    def test_empty_string_handling(self):
        """Test handling of empty strings in properties"""
        user = UserGet(
            id="123",
            given_name="",
            family_name="",
            username="",
            email="test@example.com"
        )
        assert user.full_name == ""
        assert user.display_name == "User 123"
    
    def test_whitespace_handling(self):
        """Test handling of whitespace in computed properties"""
        profile = ProfileGet(
            id="123",
            user_id="user-123",
            nickname=""
        )
        assert profile.display_name == "Profile 123"
    
    def test_none_handling(self):
        """Test handling of None values"""
        user = UserGet(
            id="123",
            given_name=None,
            family_name=None,
            username=None,
            email="test@example.com"
        )
        assert user.full_name == ""
        assert user.display_name == "User 123"
    
    def test_organization_single_component_path(self):
        """Test organization with single component path"""
        org = OrganizationGet(
            id="123",
            path="root",
            title="Root Organization",
            organization_type=OrganizationType.organization
        )
        assert org.path_components == ["root"]
        assert org.parent_path is None
    
    def test_session_duration_edge_cases(self):
        """Test session duration edge cases"""
        base_time = datetime(2023, 1, 1, 10, 0, 0)
        
        # Same time login/logout (immediate logout)
        immediate_logout = SessionGet(
            id="123",
            user_id="user-123",
            session_id="session-123",
            ip_address="192.168.1.1",
            created_at=base_time,
            logout_time=base_time
        )
        assert immediate_logout.session_duration == 0
        
        # Very short session (1 second)
        short_session = SessionGet(
            id="456",
            user_id="user-123",
            session_id="session-456",
            ip_address="192.168.1.1",
            created_at=base_time,
            logout_time=base_time + timedelta(seconds=1)
        )
        assert short_session.session_duration == 1


class TestPropertyConsistency:
    """Test consistency of properties across different DTO types"""
    
    def test_display_name_consistency(self):
        """Test that display_name is consistent across Get and List DTOs"""
        # User consistency
        user_get = UserGet(
            id="123",
            given_name="John",
            family_name="Doe",
            email="john@example.com"
        )
        user_list = UserList(
            id="123",
            given_name="John",
            family_name="Doe",
            email="john@example.com"
        )
        assert user_get.display_name == user_list.display_name
        
        # Session consistency
        session_get = SessionGet(
            id="123",
            user_id="user-123",
            session_id="session-abc",
            ip_address="192.168.1.1"
        )
        session_list = SessionList(
            id="123",
            user_id="user-123",
            session_id="session-abc",
            ip_address="192.168.1.1"
        )
        # Both should indicate active session
        assert "Active" in session_get.display_name
        assert "Active" in session_list.display_name
    
    def test_id_property_usage(self):
        """Test consistent use of ID in computed properties"""
        short_id = "123"
        long_id = "123456789012345"
        
        user_short = UserGet(id=short_id, email="test@example.com")
        user_long = UserGet(id=long_id, email="test@example.com")
        
        # Should use first 8 characters (or full ID if shorter)
        assert user_short.display_name == "User 123"
        assert user_long.display_name == "User 12345678"
    
    def test_boolean_property_consistency(self):
        """Test consistent boolean property behavior"""
        # Session active property
        active_session = SessionGet(
            id="123",
            user_id="user-123",
            session_id="session-123",
            ip_address="192.168.1.1",
            logout_time=None
        )
        assert active_session.is_active is True
        
        # Profile avatar property
        profile_with_avatar = ProfileGet(
            id="123",
            user_id="user-123",
            avatar_image="https://example.com/avatar.jpg"
        )
        profile_without_avatar = ProfileGet(
            id="123",
            user_id="user-123",
            avatar_image=None
        )
        assert profile_with_avatar.has_custom_avatar is True
        assert profile_without_avatar.has_custom_avatar is False


class TestPropertyPerformance:
    """Test that computed properties don't cause performance issues"""
    
    def test_property_caching(self):
        """Test that properties can be called multiple times efficiently"""
        user = UserGet(
            id="123",
            given_name="John",
            family_name="Doe",
            email="john@example.com"
        )
        
        # Call properties multiple times
        for _ in range(100):
            _ = user.full_name
            _ = user.display_name
        
        # Should not raise any exceptions or cause performance issues
        assert user.full_name == "John Doe"
        assert user.display_name == "John Doe"
    
    def test_complex_property_calculation(self):
        """Test more complex property calculations"""
        org = OrganizationGet(
            id="123",
            path="a.very.deep.organizational.structure.with.many.levels",
            title="Deep Organization",
            organization_type=OrganizationType.organization
        )
        
        # These should be efficient even with deep paths
        components = org.path_components
        parent = org.parent_path
        
        assert len(components) == 8
        assert parent == "a.very.deep.organizational.structure.with.many"
