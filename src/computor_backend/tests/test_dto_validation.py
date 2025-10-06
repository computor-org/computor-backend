"""
Comprehensive tests for DTO validation in refactored interfaces.
"""

import pytest
from pydantic import ValidationError
from datetime import datetime

# Import all our refactored DTOs
from computor_types.users import UserCreate, UserGet, UserUpdate, UserList
from computor_types.organizations import OrganizationCreate, OrganizationGet, OrganizationType
from computor_types.accounts import AccountCreate, AccountGet
from computor_types.roles import RoleGet, RoleList
from computor_types.groups import GroupCreate, GroupGet, GroupType
from computor_types.group_claims import GroupClaimCreate, GroupClaimGet
from computor_types.user_groups import UserGroupCreate, UserGroupGet
from computor_types.profiles import ProfileCreate, ProfileGet, ProfileUpdate
from computor_types.sessions import SessionCreate, SessionGet


class TestUserValidation:
    """Test User DTO validation"""
    
    def test_user_create_valid_data(self):
        """Test UserCreate with valid data"""
        user = UserCreate(
            given_name="John",
            family_name="Doe",
            email="john.doe@example.com",
            username="johndoe123",
            number="12345"
        )
        assert user.given_name == "John"
        assert user.family_name == "Doe"
        assert user.email == "john.doe@example.com"
        assert user.username == "johndoe123"
    
    def test_user_create_invalid_email(self):
        """Test UserCreate with invalid email"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                given_name="John",
                email="invalid-email"
            )
        assert "Email must contain @ symbol" in str(exc_info.value)
    
    def test_user_create_invalid_username(self):
        """Test UserCreate with invalid username (special characters)"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="user@name!"
            )
        assert "Username can only contain alphanumeric characters" in str(exc_info.value)
    
    def test_user_create_short_username(self):
        """Test UserCreate with too short username"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(username="ab")
        assert "at least 3 characters" in str(exc_info.value)
    
    def test_user_create_empty_name_validation(self):
        """Test UserCreate with empty names"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(given_name="   ")
        assert "Name cannot be empty or only whitespace" in str(exc_info.value)
    
    def test_user_get_computed_properties(self):
        """Test UserGet computed properties"""
        user = UserGet(
            id="123",
            given_name="John",
            family_name="Doe",
            email="john@example.com"
        )
        assert user.full_name == "John Doe"
        assert user.display_name == "John Doe"
        
        # Test with only given name
        user_partial = UserGet(id="123", given_name="John")
        assert user_partial.full_name == "John"
        assert user_partial.display_name == "John"
        
        # Test with neither name
        user_minimal = UserGet(id="123", username="johndoe")
        assert user_minimal.full_name == ""
        assert user_minimal.display_name == "johndoe"


class TestOrganizationValidation:
    """Test Organization DTO validation"""
    
    def test_organization_create_valid_user_type(self):
        """Test OrganizationCreate with user type"""
        org = OrganizationCreate(
            path="user.johndoe",
            organization_type=OrganizationType.user,
            user_id="user-123"
        )
        assert org.organization_type == OrganizationType.user
        assert org.user_id == "user-123"
        assert org.title is None
    
    def test_organization_create_valid_org_type(self):
        """Test OrganizationCreate with organization type"""
        org = OrganizationCreate(
            path="acme.corp",
            organization_type=OrganizationType.organization,
            title="ACME Corporation",
            email="contact@acme.com"
        )
        assert org.organization_type == OrganizationType.organization
        assert org.title == "ACME Corporation"
        assert org.user_id is None
    
    def test_organization_create_user_type_with_title_fails(self):
        """Test OrganizationCreate user type with title should fail"""
        with pytest.raises(ValidationError) as exc_info:
            OrganizationCreate(
                path="user.johndoe",
                organization_type=OrganizationType.user,
                title="Should not have title",
                user_id="user-123"
            )
        assert "User organizations cannot have a title" in str(exc_info.value)
    
    def test_organization_create_org_type_without_title_fails(self):
        """Test OrganizationCreate organization type without title should fail"""
        with pytest.raises(ValidationError) as exc_info:
            OrganizationCreate(
                path="acme.corp",
                organization_type=OrganizationType.organization
            )
        assert "Non-user organizations must have a title" in str(exc_info.value)
    
    def test_organization_create_invalid_path(self):
        """Test OrganizationCreate with invalid ltree path"""
        with pytest.raises(ValidationError) as exc_info:
            OrganizationCreate(
                path="invalid.path.with.spaces and symbols!",
                organization_type=OrganizationType.organization,
                title="Test Org"
            )
        assert "Path must be valid ltree format" in str(exc_info.value)
    
    def test_organization_create_invalid_url(self):
        """Test OrganizationCreate with invalid URL"""
        with pytest.raises(ValidationError) as exc_info:
            OrganizationCreate(
                path="test.org",
                organization_type=OrganizationType.organization,
                title="Test Org",
                url="not-a-valid-url"
            )
        assert "URL must start with http:// or https://" in str(exc_info.value)
    
    def test_organization_get_computed_properties(self):
        """Test OrganizationGet computed properties"""
        org = OrganizationGet(
            id="123",
            path="acme.corp.division",
            title="ACME Division",
            organization_type=OrganizationType.organization
        )
        assert org.display_name == "ACME Division"
        assert org.path_components == ["acme", "corp", "division"]
        assert org.parent_path == "acme.corp"
        
        # Test user organization
        user_org = OrganizationGet(
            id="456",
            path="user.johndoe",
            organization_type=OrganizationType.user,
            user_id="user-123"
        )
        assert user_org.display_name == "User Organization (user.johndoe)"


class TestAccountValidation:
    """Test Account DTO validation"""
    
    def test_account_create_valid_data(self):
        """Test AccountCreate with valid data"""
        account = AccountCreate(
            provider="google",
            type="oauth",
            provider_account_id="google123456",
            user_id="user-123"
        )
        assert account.provider == "google"
        assert account.type == "oauth"
        assert account.provider_account_id == "google123456"
    
    def test_account_create_empty_provider(self):
        """Test AccountCreate with empty provider"""
        with pytest.raises(ValidationError) as exc_info:
            AccountCreate(
                provider="   ",
                type="oauth",
                provider_account_id="123",
                user_id="user-123"
            )
        assert "Provider cannot be empty" in str(exc_info.value)
    
    def test_account_create_provider_normalization(self):
        """Test AccountCreate provider normalization"""
        account = AccountCreate(
            provider="  GOOGLE  ",
            type="oauth",
            provider_account_id="123",
            user_id="user-123"
        )
        assert account.provider == "google"


class TestProfileValidation:
    """Test Profile DTO validation"""
    
    def test_profile_create_valid_data(self):
        """Test ProfileCreate with valid data"""
        profile = ProfileCreate(
            user_id="user-123",
            nickname="johndoe",
            bio="Software developer",
            avatar_color=16711680,  # Red in RGB
            url="https://johndoe.com"
        )
        assert profile.nickname == "johndoe"
        assert profile.avatar_color == 16711680
        assert profile.url == "https://johndoe.com"
    
    def test_profile_create_invalid_avatar_color(self):
        """Test ProfileCreate with invalid avatar color"""
        with pytest.raises(ValidationError) as exc_info:
            ProfileCreate(
                user_id="user-123",
                avatar_color=16777216  # > 16777215 (max RGB)
            )
        assert "less than or equal to 16777215" in str(exc_info.value)
    
    def test_profile_create_invalid_nickname(self):
        """Test ProfileCreate with invalid nickname"""
        with pytest.raises(ValidationError) as exc_info:
            ProfileCreate(
                user_id="user-123",
                nickname="user@name!"
            )
        assert "Nickname can only contain alphanumeric characters" in str(exc_info.value)
    
    def test_profile_create_invalid_url(self):
        """Test ProfileCreate with invalid URL"""
        with pytest.raises(ValidationError) as exc_info:
            ProfileCreate(
                user_id="user-123",
                url="not-a-url"
            )
        assert "URL must start with http:// or https://" in str(exc_info.value)
    
    def test_profile_get_computed_properties(self):
        """Test ProfileGet computed properties"""
        profile = ProfileGet(
            id="123",
            user_id="user-123",
            nickname="johndoe",
            avatar_color=16711680,
            avatar_image="https://example.com/avatar.jpg"
        )
        assert profile.display_name == "johndoe"
        assert profile.avatar_color_hex == "#ff0000"
        assert profile.has_custom_avatar is True
        
        # Test without custom avatar
        profile_no_avatar = ProfileGet(
            id="123",
            user_id="user-123",
            nickname="johndoe"
        )
        assert profile_no_avatar.has_custom_avatar is False


class TestSessionValidation:
    """Test Session DTO validation"""
    
    def test_session_create_valid_ipv4(self):
        """Test SessionCreate with valid IPv4"""
        session = SessionCreate(
            user_id="user-123",
            session_id="session-abc123",
            ip_address="192.168.1.1"
        )
        assert session.ip_address == "192.168.1.1"
    
    def test_session_create_valid_ipv6(self):
        """Test SessionCreate with valid IPv6"""
        session = SessionCreate(
            user_id="user-123",
            session_id="session-abc123",
            ip_address="2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        )
        assert session.ip_address == "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
    
    def test_session_create_invalid_ip(self):
        """Test SessionCreate with invalid IP address"""
        with pytest.raises(ValidationError) as exc_info:
            SessionCreate(
                user_id="user-123",
                session_id="session-abc123",
                ip_address="not.an.ip.address"
            )
        assert "Invalid IP address format" in str(exc_info.value)
    
    def test_session_get_computed_properties(self):
        """Test SessionGet computed properties"""
        session = SessionGet(
            id="123",
            user_id="user-123",
            session_id="session-abc123456789",
            ip_address="192.168.1.1",
            created_at=datetime(2023, 1, 1, 10, 0, 0),
            logout_time=datetime(2023, 1, 1, 12, 0, 0)
        )
        assert session.is_active is False
        assert session.session_duration == 7200  # 2 hours in seconds
        assert "session-" in session.display_name
        assert "Logged out" in session.display_name
        
        # Test active session
        active_session = SessionGet(
            id="123",
            user_id="user-123",
            session_id="session-active",
            ip_address="192.168.1.1"
        )
        assert active_session.is_active is True
        assert "Active" in active_session.display_name


class TestGroupValidation:
    """Test Group DTO validation"""
    
    def test_group_create_valid_data(self):
        """Test GroupCreate with valid data"""
        group = GroupCreate(
            name="Developers",
            description="Software developers group",
            group_type=GroupType.fixed
        )
        assert group.name == "Developers"
        assert group.group_type == GroupType.fixed
    
    def test_group_create_empty_name(self):
        """Test GroupCreate with empty name"""
        with pytest.raises(ValidationError) as exc_info:
            GroupCreate(
                name="   ",
                group_type=GroupType.fixed
            )
        assert "Group name cannot be empty or only whitespace" in str(exc_info.value)


class TestGroupClaimValidation:
    """Test GroupClaim DTO validation"""
    
    def test_group_claim_create_valid_data(self):
        """Test GroupClaimCreate with valid data"""
        claim = GroupClaimCreate(
            group_id="group-123",
            claim_type="permissions",
            claim_value="read_documents"
        )
        assert claim.claim_type == "permissions"
        assert claim.claim_value == "read_documents"
    
    def test_group_claim_create_claim_type_normalization(self):
        """Test GroupClaimCreate claim type normalization"""
        claim = GroupClaimCreate(
            group_id="group-123",
            claim_type="  PERMISSION  ",
            claim_value="read_documents"
        )
        assert claim.claim_type == "permissions"


class TestUserGroupValidation:
    """Test UserGroup DTO validation"""
    
    def test_user_group_create_valid_data(self):
        """Test UserGroupCreate with valid data"""
        user_group = UserGroupCreate(
            user_id="user-123",
            group_id="group-456",
            transient=True
        )
        assert user_group.user_id == "user-123"
        assert user_group.group_id == "group-456"
        assert user_group.transient is True
    
    def test_user_group_get_computed_properties(self):
        """Test UserGroupGet computed properties"""
        user_group = UserGroupGet(
            user_id="user-123",
            group_id="group-456",
            transient=True
        )
        assert user_group.membership_type == "Transient"
        assert user_group.membership_identifier == "user-123:group-456"
        
        # Test permanent membership
        permanent_membership = UserGroupGet(
            user_id="user-123",
            group_id="group-456",
            transient=False
        )
        assert permanent_membership.membership_type == "Permanent"


class TestFieldConstraints:
    """Test various field constraints across DTOs"""
    
    def test_string_length_constraints(self):
        """Test string length constraints"""
        # Test max length
        with pytest.raises(ValidationError):
            UserCreate(given_name="a" * 256)  # Max 255
        
        # Test min length
        with pytest.raises(ValidationError):
            UserCreate(username="ab")  # Min 3
    
    def test_field_descriptions_present(self):
        """Test that Field descriptions are present"""
        user_create_fields = UserCreate.model_fields
        assert user_create_fields['given_name'].description is not None
        assert user_create_fields['email'].description is not None
        
        org_create_fields = OrganizationCreate.model_fields
        assert org_create_fields['path'].description is not None
        assert org_create_fields['organization_type'].description is not None
    
    def test_optional_vs_required_fields(self):
        """Test optional vs required field behavior"""
        # Test minimal valid UserCreate
        user = UserCreate()
        assert user.given_name is None
        assert user.email is None
        
        # Test required fields for OrganizationCreate
        with pytest.raises(ValidationError):
            OrganizationCreate()  # Missing required 'path' and 'organization_type'
