"""Tests for exception classes."""

import pytest

from computor_client.exceptions import (
    ComputorClientError,
    AuthenticationError,
    TokenExpiredError,
    InvalidCredentialsError,
    AuthorizationError,
    AdminRequiredError,
    CourseAccessDeniedError,
    ValidationError,
    MissingFieldError,
    InvalidFieldFormatError,
    NotFoundError,
    UserNotFoundError,
    CourseNotFoundError,
    ConflictError,
    ResourceExistsError,
    RateLimitError,
    ServerError,
    ServiceUnavailableError,
    NetworkError,
    TimeoutError,
    ConnectionError,
    exception_from_response,
)


class TestComputorClientError:
    """Tests for the base ComputorClientError class."""

    def test_basic_creation(self):
        """Test creating a basic exception."""
        error = ComputorClientError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.status_code is None
        assert error.error_code is None
        assert error.details == {}

    def test_with_status_code(self):
        """Test exception with status code."""
        error = ComputorClientError("Error", status_code=500)
        assert error.status_code == 500
        assert "(HTTP 500)" in str(error)

    def test_with_error_code(self):
        """Test exception with error code."""
        error = ComputorClientError("Error", error_code="ERR_001")
        assert error.error_code == "ERR_001"
        assert "[ERR_001]" in str(error)

    def test_with_details(self):
        """Test exception with details."""
        details = {"field": "username", "reason": "too short"}
        error = ComputorClientError("Validation failed", details=details)
        assert error.details == details

    def test_repr(self):
        """Test exception repr."""
        error = ComputorClientError(
            "Error",
            status_code=400,
            error_code="VAL_001",
        )
        repr_str = repr(error)
        assert "ComputorClientError" in repr_str
        assert "Error" in repr_str
        assert "400" in repr_str
        assert "VAL_001" in repr_str


class TestAuthenticationErrors:
    """Tests for authentication-related exceptions."""

    def test_authentication_error(self):
        """Test basic authentication error."""
        error = AuthenticationError()
        assert error.status_code == 401
        assert "Authentication required" in error.message

    def test_token_expired_error(self):
        """Test token expired error."""
        error = TokenExpiredError()
        assert error.status_code == 401
        assert error.error_code == "AUTH_003"
        assert "expired" in error.message.lower()

    def test_invalid_credentials_error(self):
        """Test invalid credentials error."""
        error = InvalidCredentialsError()
        assert error.status_code == 401
        assert error.error_code == "AUTH_002"
        assert "invalid" in error.message.lower()


class TestAuthorizationErrors:
    """Tests for authorization-related exceptions."""

    def test_authorization_error(self):
        """Test basic authorization error."""
        error = AuthorizationError()
        assert error.status_code == 403
        assert "denied" in error.message.lower()

    def test_admin_required_error(self):
        """Test admin required error."""
        error = AdminRequiredError()
        assert error.status_code == 403
        assert error.error_code == "AUTHZ_002"
        assert "admin" in error.message.lower()

    def test_course_access_denied_error(self):
        """Test course access denied error."""
        error = CourseAccessDeniedError(course_id="course-123")
        assert error.status_code == 403
        assert error.error_code == "AUTHZ_003"
        assert error.details.get("course_id") == "course-123"


class TestValidationErrors:
    """Tests for validation-related exceptions."""

    def test_validation_error(self):
        """Test basic validation error."""
        error = ValidationError()
        assert error.status_code == 400

    def test_validation_error_with_field_errors(self):
        """Test validation error with field errors."""
        field_errors = {"email": "Invalid email format"}
        error = ValidationError(field_errors=field_errors)
        assert error.field_errors == field_errors
        assert error.details.get("field_errors") == field_errors

    def test_missing_field_error(self):
        """Test missing field error."""
        error = MissingFieldError("username")
        assert error.status_code == 400
        assert error.error_code == "VAL_002"
        assert error.field_name == "username"
        assert "username" in error.message

    def test_invalid_field_format_error(self):
        """Test invalid field format error."""
        error = InvalidFieldFormatError("email", "valid email address")
        assert error.status_code == 400
        assert error.error_code == "VAL_003"
        assert error.field_name == "email"
        assert error.expected_format == "valid email address"


class TestNotFoundErrors:
    """Tests for not found exceptions."""

    def test_not_found_error(self):
        """Test basic not found error."""
        error = NotFoundError()
        assert error.status_code == 404

    def test_not_found_with_resource_info(self):
        """Test not found error with resource info."""
        error = NotFoundError(
            "User not found",
            resource_type="user",
            resource_id="user-123",
        )
        assert error.resource_type == "user"
        assert error.resource_id == "user-123"

    def test_user_not_found_error(self):
        """Test user not found error."""
        error = UserNotFoundError("user-123")
        assert error.status_code == 404
        assert error.error_code == "NF_002"
        assert error.resource_type == "user"
        assert error.resource_id == "user-123"

    def test_course_not_found_error(self):
        """Test course not found error."""
        error = CourseNotFoundError("course-123")
        assert error.status_code == 404
        assert error.error_code == "NF_003"
        assert error.resource_type == "course"


class TestConflictErrors:
    """Tests for conflict exceptions."""

    def test_conflict_error(self):
        """Test basic conflict error."""
        error = ConflictError()
        assert error.status_code == 409

    def test_resource_exists_error(self):
        """Test resource exists error."""
        error = ResourceExistsError("User", "admin@example.com")
        assert error.status_code == 409
        assert error.resource_type == "User"
        assert error.identifier == "admin@example.com"
        assert "already exists" in error.message.lower()


class TestRateLimitError:
    """Tests for rate limit exception."""

    def test_rate_limit_error(self):
        """Test rate limit error."""
        error = RateLimitError()
        assert error.status_code == 429

    def test_rate_limit_with_retry_after(self):
        """Test rate limit error with retry_after."""
        error = RateLimitError(retry_after=60)
        assert error.retry_after == 60


class TestServerErrors:
    """Tests for server-side exceptions."""

    def test_server_error(self):
        """Test basic server error."""
        error = ServerError()
        assert error.status_code == 500

    def test_service_unavailable_error(self):
        """Test service unavailable error."""
        error = ServiceUnavailableError()
        assert error.status_code == 503


class TestNetworkErrors:
    """Tests for network-level exceptions."""

    def test_network_error(self):
        """Test basic network error."""
        error = NetworkError("Connection refused")
        assert error.status_code is None
        assert error.error_code is None

    def test_timeout_error(self):
        """Test timeout error."""
        error = TimeoutError()
        assert "timed out" in error.message.lower()

    def test_connection_error(self):
        """Test connection error."""
        error = ConnectionError()
        assert "connect" in error.message.lower()


class TestExceptionFromResponse:
    """Tests for the exception_from_response utility."""

    @pytest.mark.parametrize(
        "status_code,expected_class",
        [
            (400, ValidationError),
            (401, AuthenticationError),
            (403, AuthorizationError),
            (404, NotFoundError),
            (409, ConflictError),
            (429, RateLimitError),
            (500, ServerError),
            (502, ServerError),
            (503, ServiceUnavailableError),
            (504, ServerError),
        ],
    )
    def test_exception_mapping(self, status_code, expected_class):
        """Test that status codes map to correct exception classes."""
        error = exception_from_response(status_code, "Test error")
        assert isinstance(error, expected_class)
        assert error.status_code == status_code

    def test_unknown_status_code(self):
        """Test handling of unknown status codes."""
        error = exception_from_response(418, "I'm a teapot")
        assert isinstance(error, ComputorClientError)
        assert error.status_code == 418

    def test_with_error_code_and_details(self):
        """Test creating exception with error code and details."""
        details = {"resource": "user"}
        error = exception_from_response(
            404,
            "User not found",
            error_code="NF_002",
            details=details,
        )
        assert error.error_code == "NF_002"
        assert error.details == details
