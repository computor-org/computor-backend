"""
Pydantic configuration models for deployment mapping.

Defines the JSON schema for mapping arbitrary table fields to deployment configurations.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class FieldMappingConfig(BaseModel):
    """
    Configuration for mapping a single field.

    Supports:
    - Direct column mapping: "source_column_name"
    - Literal values: {"literal": "value"}
    - Template substitution: {"template": "{field1}_{field2}"}
    - Field reference: {"ref": "field_name"}
    """

    source: Union[str, Dict[str, Any]] = Field(
        description="Source column name, literal value, or template configuration"
    )
    default: Optional[Any] = Field(
        default=None,
        description="Default value if source is missing or empty"
    )
    required: bool = Field(
        default=False,
        description="Whether this field is required (will raise error if missing)"
    )
    transform: Optional[str] = Field(
        default=None,
        description="Transformation function name (e.g., 'to_bool', 'to_lower', 'extract_username')"
    )


class UserFieldsConfig(BaseModel):
    """
    Mapping configuration for UserDeployment fields.

    All fields are optional and map to UserDeployment attributes.
    """

    given_name: Optional[Union[str, FieldMappingConfig, Dict]] = None
    family_name: Optional[Union[str, FieldMappingConfig, Dict]] = None
    email: Optional[Union[str, FieldMappingConfig, Dict]] = None
    number: Optional[Union[str, FieldMappingConfig, Dict]] = None
    username: Optional[Union[str, FieldMappingConfig, Dict]] = None
    user_type: Optional[Union[str, FieldMappingConfig, Dict]] = Field(
        default="user",
        description="User type (defaults to 'user')"
    )
    password: Optional[Union[str, FieldMappingConfig, Dict]] = None
    roles: Optional[Union[str, FieldMappingConfig, Dict, List]] = None
    gitlab_username: Optional[Union[str, FieldMappingConfig, Dict]] = None
    gitlab_email: Optional[Union[str, FieldMappingConfig, Dict]] = None
    properties: Optional[Union[str, FieldMappingConfig, Dict]] = None

    class Config:
        extra = "allow"  # Allow additional properties


class AccountFieldsConfig(BaseModel):
    """
    Mapping configuration for AccountDeployment fields.

    If not specified, no accounts will be created.
    """

    provider: Union[str, FieldMappingConfig, Dict] = Field(
        default="gitlab",
        description="Account provider (e.g., 'gitlab', 'github')"
    )
    type: Union[str, FieldMappingConfig, Dict] = Field(
        default="oauth",
        description="Account type (e.g., 'oauth', 'api_token')"
    )
    provider_account_id: Optional[Union[str, FieldMappingConfig, Dict]] = None
    access_token: Optional[Union[str, FieldMappingConfig, Dict]] = None
    refresh_token: Optional[Union[str, FieldMappingConfig, Dict]] = None
    gitlab_username: Optional[Union[str, FieldMappingConfig, Dict]] = None
    gitlab_email: Optional[Union[str, FieldMappingConfig, Dict]] = None
    gitlab_user_id: Optional[Union[str, FieldMappingConfig, Dict, int]] = None
    is_admin: Optional[Union[str, FieldMappingConfig, Dict, bool]] = Field(
        default=False,
        description="Whether user has admin privileges"
    )
    can_create_group: Optional[Union[str, FieldMappingConfig, Dict, bool]] = Field(
        default=True,
        description="Whether user can create groups"
    )
    properties: Optional[Union[str, FieldMappingConfig, Dict]] = None

    class Config:
        extra = "allow"


class CourseMemberFieldsConfig(BaseModel):
    """
    Mapping configuration for CourseMemberDeployment fields.

    Supports both path-based and ID-based course identification.
    Can specify multiple course memberships per row using list syntax.
    """

    # ID-based identification
    id: Optional[Union[str, FieldMappingConfig, Dict]] = None

    # Path-based identification
    organization: Optional[Union[str, FieldMappingConfig, Dict]] = None
    course_family: Optional[Union[str, FieldMappingConfig, Dict]] = None
    course: Optional[Union[str, FieldMappingConfig, Dict]] = None

    # Membership details
    role: Union[str, FieldMappingConfig, Dict] = Field(
        default="_student",
        description="Course role (defaults to '_student')"
    )
    group: Optional[Union[str, FieldMappingConfig, Dict]] = None

    # Condition for creating this membership
    condition: Optional[str] = Field(
        default=None,
        description="Condition expression - only create if evaluates to true"
    )

    class Config:
        extra = "allow"


class TransformationsConfig(BaseModel):
    """
    Global transformation rules applied during mapping.
    """

    boolean_values: Optional[Dict[str, Dict[str, List[str]]]] = Field(
        default=None,
        description="Boolean interpretation rules per field"
    )

    template_functions: Optional[Dict[str, str]] = Field(
        default=None,
        description="Custom template function definitions"
    )

    default_values: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Global default values for fields"
    )

    null_values: List[str] = Field(
        default=["", "null", "NULL", "None", "N/A", "-"],
        description="Values to treat as null/empty"
    )


class DeploymentMappingConfig(BaseModel):
    """
    Root configuration for mapping table data to deployment configurations.

    This defines how CSV/table columns map to UserDeployment, AccountDeployment,
    and CourseMemberDeployment fields.
    """

    version: str = Field(
        default="1.0",
        description="Mapping configuration version"
    )

    description: Optional[str] = Field(
        default=None,
        description="Human-readable description of this mapping"
    )

    # Field mappings
    user_fields: UserFieldsConfig = Field(
        description="Mapping for UserDeployment fields"
    )

    account_fields: Optional[AccountFieldsConfig] = Field(
        default=None,
        description="Mapping for AccountDeployment fields (optional)"
    )

    course_member_fields: Optional[Union[CourseMemberFieldsConfig, List[CourseMemberFieldsConfig]]] = Field(
        default=None,
        description="Mapping for CourseMemberDeployment fields (supports single or multiple)"
    )

    # Global transformations
    transformations: Optional[TransformationsConfig] = Field(
        default=None,
        description="Global transformation rules"
    )

    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata about this mapping"
    )

    class Config:
        extra = "allow"
        json_schema_extra = {
            "examples": [
                {
                    "version": "1.0",
                    "description": "Student import mapping",
                    "user_fields": {
                        "given_name": "First Name",
                        "family_name": "Last Name",
                        "email": "Email",
                        "username": {"template": "{email}", "transform": "extract_username"},
                        "number": "Student ID"
                    },
                    "account_fields": {
                        "provider": "gitlab",
                        "type": "oauth",
                        "provider_account_id": {"ref": "username"},
                        "gitlab_email": {"ref": "email"}
                    },
                    "course_member_fields": {
                        "organization": "kit",
                        "course_family": "prog",
                        "course": "prog1",
                        "role": "_student",
                        "group": "Group"
                    }
                }
            ]
        }
