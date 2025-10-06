"""
Tests for edge cases and error handling in DTO validation and functionality.
"""

import pytest
from pydantic import ValidationError
from datetime import datetime

from computor_types.users import UserCreate, UserGet, UserUpdate
from computor_types.organizations import OrganizationCreate, OrganizationType
from computor_types.accounts import AccountCreate, AccountUpdate
from computor_types.profiles import ProfileCreate, ProfileUpdate
from computor_types.sessions import SessionCreate
from computor_types.groups import GroupCreate
from computor_types.group_claims import GroupClaimCreate


class TestValidationEdgeCases:
    """Test validation edge cases and boundary conditions"""
    
    def test_max_length_boundaries(self):
        """Test field length boundaries"""
        # Test exactly at max length
        user = UserCreate(given_name="a" * 255)  # Exactly 255 chars
        assert len(user.given_name) == 255
        
        # Test one character over max length
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(given_name="a" * 256)  # 256 chars - should fail
        assert "at most 255 characters" in str(exc_info.value)
    
    def test_min_length_boundaries(self):
        """Test minimum length boundaries"""
        # Test exactly at min length
        user = UserCreate(username="abc")  # Exactly 3 chars
        assert user.username == "abc"
        
        # Test one character under min length
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(username="ab")  # 2 chars - should fail
        assert "at least 3 characters" in str(exc_info.value)
    
    def test_unicode_and_special_characters(self):
        """Test handling of Unicode and special characters"""
        # Unicode characters in names
        user = UserCreate(
            given_name="José",
            family_name="Müller"
        )
        assert user.given_name == "José"
        assert user.family_name == "Müller"
        
        # Emoji and special Unicode
        user_emoji = UserCreate(
            given_name="John 👋",
            family_name="Smith 🚀"
        )
        assert "👋" in user_emoji.given_name
        assert "🚀" in user_emoji.family_name
        
        # Unicode in organization title
        org = OrganizationCreate(
            path="unicode.test",
            organization_type=OrganizationType.organization,
            title="测试组织 (Test Organization)"
        )
        assert "测试组织" in org.title
    
    def test_whitespace_edge_cases(self):
        """Test various whitespace scenarios"""
        # Leading/trailing whitespace should be stripped
        user = UserCreate(given_name="  John  ", family_name="  Doe  ")
        assert user.given_name == "John"
        assert user.family_name == "Doe"
        
        # Only whitespace should fail validation
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(given_name="   ")
        assert "Name cannot be empty or only whitespace" in str(exc_info.value)
        
        # Mixed whitespace
        with pytest.raises(ValidationError):
            UserCreate(given_name="  \t\n  ")
    
    def test_rgb_color_boundaries(self):
        """Test RGB color value boundaries"""
        # Valid boundaries
        profile_min = ProfileCreate(user_id="user-123", avatar_color=0)
        profile_max = ProfileCreate(user_id="user-123", avatar_color=16777215)
        
        assert profile_min.avatar_color == 0
        assert profile_max.avatar_color == 16777215
        
        # Invalid boundaries
        with pytest.raises(ValidationError):
            ProfileCreate(user_id="user-123", avatar_color=-1)
        
        with pytest.raises(ValidationError):
            ProfileCreate(user_id="user-123", avatar_color=16777216)
    
    def test_email_edge_cases(self):
        """Test email validation edge cases"""
        # Valid complex emails
        valid_emails = [
            "user@example.com",
            "user.name@example.com",
            "user+tag@example.com",
            "user123@sub.example.com",
            "a@b.co",  # Minimal valid email
        ]
        
        for email in valid_emails:
            user = UserCreate(email=email)
            assert user.email == email
        
        # Invalid emails
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user..name@example.com",
            "user name@example.com",  # Space in local part
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValidationError):
                UserCreate(email=email)
    
    def test_url_validation_edge_cases(self):
        """Test URL validation edge cases"""
        # Valid URLs
        valid_urls = [
            "https://example.com",
            "http://example.com",
            "https://sub.example.com/path",
            "https://example.com:8080/path?query=value",
        ]
        
        for url in valid_urls:
            profile = ProfileCreate(user_id="user-123", url=url)
            assert profile.url == url
        
        # Invalid URLs
        invalid_urls = [
            "ftp://example.com",  # Wrong protocol
            "example.com",  # Missing protocol
            "https://",  # Incomplete
            "not-a-url",
        ]
        
        for url in invalid_urls:
            with pytest.raises(ValidationError):
                ProfileCreate(user_id="user-123", url=url)


class TestDataTypeEdgeCases:
    """Test edge cases related to data types"""
    
    def test_none_vs_empty_string_handling(self):
        """Test distinction between None and empty string"""
        # None should be preserved
        user_none = UserCreate(given_name=None)
        assert user_none.given_name is None
        
        # Empty string should be handled by validation
        with pytest.raises(ValidationError):
            UserCreate(given_name="")  # Empty string should fail after strip
    
    def test_boolean_edge_cases(self):
        """Test boolean field edge cases"""
        # Explicit boolean values
        account = AccountCreate(
            provider="test",
            type="oauth",
            provider_account_id="123",
            user_id="user-123"
        )
        # builtin should default to False
        assert hasattr(account, 'provider')
        
        # Test transient in UserGroup
        from computor_types.user_groups import UserGroupCreate
        
        user_group_true = UserGroupCreate(
            user_id="user-123",
            group_id="group-456",
            transient=True
        )
        user_group_false = UserGroupCreate(
            user_id="user-123",
            group_id="group-456",
            transient=False
        )
        user_group_default = UserGroupCreate(
            user_id="user-123",
            group_id="group-456"
        )
        
        assert user_group_true.transient is True
        assert user_group_false.transient is False
        assert user_group_default.transient is False  # Default value
    
    def test_datetime_edge_cases(self):
        """Test datetime handling edge cases"""
        # Test various datetime formats in properties
        profile = ProfileCreate(
            user_id="user-123",
            properties={"last_login": "2023-01-01T10:00:00Z"}
        )
        assert isinstance(profile.properties, dict)
        
        # Test None datetime
        from computor_types.sessions import SessionGet
        session = SessionGet(
            id="123",
            user_id="user-123",
            session_id="session-123",
            ip_address="192.168.1.1",
            logout_time=None
        )
        assert session.logout_time is None
        assert session.is_active is True
    
    def test_json_properties_edge_cases(self):
        """Test JSON properties field edge cases"""
        # Empty dict
        user = UserCreate(properties={})
        assert user.properties == {}
        
        # Complex nested structure
        complex_props = {
            "preferences": {
                "theme": "dark",
                "notifications": {
                    "email": True,
                    "push": False
                }
            },
            "metadata": {
                "last_login": "2023-01-01T10:00:00Z",
                "login_count": 42
            }
        }
        user_complex = UserCreate(properties=complex_props)
        assert user_complex.properties == complex_props
        
        # None should be preserved
        user_none_props = UserCreate(properties=None)
        assert user_none_props.properties is None


class TestValidationErrorMessages:
    """Test that validation error messages are clear and helpful"""
    
    def test_field_specific_error_messages(self):
        """Test that error messages are field-specific and clear"""
        # Username validation error
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(username="user@name!")
        error_msg = str(exc_info.value)
        assert "username" in error_msg.lower()
        assert "alphanumeric" in error_msg.lower()
        
        # Email validation error
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(email="invalid-email")
        error_msg = str(exc_info.value)
        assert "email" in error_msg.lower()
        assert "valid" in error_msg.lower()
        
        # Path validation error
        with pytest.raises(ValidationError) as exc_info:
            OrganizationCreate(
                path="invalid path with spaces",
                organization_type=OrganizationType.organization,
                title="Test"
            )
        error_msg = str(exc_info.value)
        assert "path" in error_msg.lower()
        assert "ltree" in error_msg.lower()
    
    def test_multiple_validation_errors(self):
        """Test handling of multiple validation errors"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                given_name="",  # Empty name
                email="invalid-email",  # Invalid email
                username="ab"  # Too short username
            )
        
        error_msg = str(exc_info.value)
        # Should mention multiple field errors
        assert "given_name" in error_msg or "email" in error_msg or "username" in error_msg
    
    def test_business_logic_error_messages(self):
        """Test business logic validation error messages"""
        # User organization with title should fail
        with pytest.raises(ValidationError) as exc_info:
            OrganizationCreate(
                path="user.test",
                organization_type=OrganizationType.user,
                title="Should not have title",
                user_id="user-123"
            )
        error_msg = str(exc_info.value)
        assert "User organizations cannot have a title" in error_msg
        
        # Organization without title should fail
        with pytest.raises(ValidationError) as exc_info:
            OrganizationCreate(
                path="org.test",
                organization_type=OrganizationType.organization
            )
        error_msg = str(exc_info.value)
        assert "Non-user organizations must have a title" in error_msg


class TestCornerCases:
    """Test unusual corner cases and boundary conditions"""
    
    def test_very_long_valid_inputs(self):
        """Test with maximum allowed input lengths"""
        # Create user with maximum length fields
        max_user = UserCreate(
            given_name="a" * 255,
            family_name="b" * 255,
            email="c" * 50 + "@example.com",  # Reasonable email length
            username="d" * 50,  # Maximum username length
            number="e" * 255
        )
        
        assert len(max_user.given_name) == 255
        assert len(max_user.family_name) == 255
        assert len(max_user.username) == 50
        assert len(max_user.number) == 255
    
    def test_ip_address_edge_cases(self):
        """Test IP address validation edge cases"""
        # Valid IPv4 edge cases
        valid_ipv4s = [
            "0.0.0.0",
            "127.0.0.1",
            "255.255.255.255",
            "192.168.1.1"
        ]
        
        for ip in valid_ipv4s:
            session = SessionCreate(
                user_id="user-123",
                session_id="session-123",
                ip_address=ip
            )
            assert session.ip_address == ip
        
        # Valid IPv6 edge cases
        valid_ipv6s = [
            "::1",  # Localhost
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334",  # Full form
            "2001:db8:85a3::8a2e:370:7334",  # Compressed form
            "::",  # All zeros
        ]
        
        for ip in valid_ipv6s:
            session = SessionCreate(
                user_id="user-123",
                session_id="session-123",
                ip_address=ip
            )
            assert session.ip_address == ip
        
        # Invalid IP addresses
        invalid_ips = [
            "256.256.256.256",  # Invalid IPv4
            "192.168.1",  # Incomplete IPv4
            "not.an.ip.address",
            "192.168.1.1.1",  # Too many octets
            "",  # Empty
        ]
        
        for ip in invalid_ips:
            with pytest.raises(ValidationError):
                SessionCreate(
                    user_id="user-123",
                    session_id="session-123",
                    ip_address=ip
                )
    
    def test_ltree_path_edge_cases(self):
        """Test ltree path validation edge cases"""
        # Valid paths
        valid_paths = [
            "root",  # Single component
            "a.b",  # Two components
            "org_name",  # Underscore
            "org-name",  # Hyphen
            "org123",  # Numbers
            "a.b.c.d.e.f.g.h.i.j",  # Many components
        ]
        
        for path in valid_paths:
            org = OrganizationCreate(
                path=path,
                organization_type=OrganizationType.organization,
                title="Test Organization"
            )
            assert org.path == path
        
        # Invalid paths
        invalid_paths = [
            "",  # Empty
            "org with spaces",  # Spaces
            "org.with.spaces in.component",  # Spaces in component
            "org..double.dot",  # Double dots
            ".starts.with.dot",  # Starts with dot
            "ends.with.dot.",  # Ends with dot
            "org!special",  # Special characters
        ]
        
        for path in invalid_paths:
            with pytest.raises(ValidationError):
                OrganizationCreate(
                    path=path,
                    organization_type=OrganizationType.organization,
                    title="Test Organization"
                )
    
    def test_enum_edge_cases(self):
        """Test enum validation edge cases"""
        # Valid enum values
        valid_account_types = [
            "oauth",
            "saml",
            "ldap",
            "local",
            "token"
        ]
        
        for acc_type in valid_account_types:
            account = AccountCreate(
                provider="test",
                type=acc_type,
                provider_account_id="123",
                user_id="user-123"
            )
            assert account.type == acc_type
        
        # Test string values work due to use_enum_values=True
        account_str = AccountCreate(
            provider="test",
            type="oauth",  # String instead of enum
            provider_account_id="123",
            user_id="user-123"
        )
        assert account_str.type == "oauth"


class TestUpdateValidation:
    """Test validation for update DTOs"""
    
    def test_partial_updates(self):
        """Test that update DTOs allow partial data"""
        # Update with only one field
        user_update = UserUpdate(given_name="NewName")
        assert user_update.given_name == "NewName"
        assert user_update.family_name is None
        assert user_update.email is None
        
        # Update with multiple fields
        user_update_multi = UserUpdate(
            given_name="John",
            email="john.new@example.com"
        )
        assert user_update_multi.given_name == "John"
        assert user_update_multi.email == "john.new@example.com"
        assert user_update_multi.family_name is None
    
    def test_update_validation_still_applies(self):
        """Test that validation still applies to update DTOs"""
        # Invalid email in update
        with pytest.raises(ValidationError):
            UserUpdate(email="invalid-email")
        
        # Invalid username in update
        with pytest.raises(ValidationError):
            UserUpdate(username="ab")  # Too short
        
        # Invalid avatar color in profile update
        with pytest.raises(ValidationError):
            ProfileUpdate(avatar_color=16777216)  # Too large
    
    def test_empty_update(self):
        """Test completely empty update objects"""
        # Should be valid - no fields to validate
        empty_user_update = UserUpdate()
        assert empty_user_update.given_name is None
        assert empty_user_update.family_name is None
        
        empty_account_update = AccountUpdate()
        assert empty_account_update.provider is None
        assert empty_account_update.type is None