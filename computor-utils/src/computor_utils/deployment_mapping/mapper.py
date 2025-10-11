"""
Core deployment mapper implementation.

Converts CSV/table data into deployment configurations using configurable mappings.
"""

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import ValidationError

from computor_types.deployments_refactored import (
    UserDeployment,
    AccountDeployment,
    CourseMemberDeployment,
    UserAccountDeployment,
    UsersDeploymentConfig,
)

from .config import (
    DeploymentMappingConfig,
    FieldMappingConfig,
    UserFieldsConfig,
    AccountFieldsConfig,
    CourseMemberFieldsConfig,
)
from .transformers import FieldTransformer


class MappingError(Exception):
    """Error during deployment mapping."""
    pass


class DeploymentMapper:
    """
    Maps table data to deployment configurations.

    Converts CSV/table rows into UserDeployment, AccountDeployment, and
    CourseMemberDeployment objects using a configurable JSON mapping.
    """

    def __init__(self, mapping_config: Union[str, Path, Dict, DeploymentMappingConfig]):
        """
        Initialize mapper with configuration.

        Args:
            mapping_config: Path to JSON config file, dict, or DeploymentMappingConfig instance
        """
        if isinstance(mapping_config, DeploymentMappingConfig):
            self.config = mapping_config
        elif isinstance(mapping_config, dict):
            self.config = DeploymentMappingConfig(**mapping_config)
        else:
            self.config = self._load_config_from_file(mapping_config)

        self.transformer = FieldTransformer()

    def _load_config_from_file(self, config_path: Union[str, Path]) -> DeploymentMappingConfig:
        """
        Load mapping configuration from JSON file.

        Args:
            config_path: Path to JSON configuration file

        Returns:
            DeploymentMappingConfig instance

        Raises:
            MappingError: If file cannot be read or parsed
        """
        path = Path(config_path)
        if not path.exists():
            raise MappingError(f"Config file not found: {config_path}")

        try:
            with path.open("r", encoding="utf-8") as f:
                config_data = json.load(f)
            return DeploymentMappingConfig(**config_data)
        except json.JSONDecodeError as e:
            raise MappingError(f"Invalid JSON in config file: {e}")
        except ValidationError as e:
            raise MappingError(f"Invalid config schema: {e}")

    def map_csv_to_deployments(
        self,
        csv_path: Union[str, Path],
        encoding: str = "utf-8",
        delimiter: str = ",",
    ) -> UsersDeploymentConfig:
        """
        Convert CSV file to deployment configuration.

        Args:
            csv_path: Path to CSV file
            encoding: File encoding (default: utf-8)
            delimiter: CSV delimiter (default: comma)

        Returns:
            UsersDeploymentConfig with all mapped users

        Raises:
            MappingError: If CSV cannot be read or mapped
        """
        path = Path(csv_path)
        if not path.exists():
            raise MappingError(f"CSV file not found: {csv_path}")

        try:
            with path.open("r", encoding=encoding, newline="") as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                rows = list(reader)
        except Exception as e:
            raise MappingError(f"Error reading CSV file: {e}")

        return self.map_table_data_to_deployments(rows)

    def map_table_data_to_deployments(
        self,
        rows: List[Dict[str, Any]]
    ) -> UsersDeploymentConfig:
        """
        Convert table rows to deployment configuration.

        Args:
            rows: List of row dictionaries (column_name -> value)

        Returns:
            UsersDeploymentConfig with all mapped users

        Raises:
            MappingError: If mapping fails
        """
        users = []
        errors = []

        for idx, row in enumerate(rows, start=1):
            try:
                user_account = self._map_row_to_user_account(row)
                users.append(user_account)
            except Exception as e:
                errors.append(f"Row {idx}: {str(e)}")

        if errors:
            error_msg = "Mapping errors:\n" + "\n".join(errors)
            raise MappingError(error_msg)

        return UsersDeploymentConfig(users=users)

    def _map_row_to_user_account(self, row: Dict[str, Any]) -> UserAccountDeployment:
        """
        Map a single row to UserAccountDeployment.

        Args:
            row: Row dictionary

        Returns:
            UserAccountDeployment instance
        """
        # Build initial context for template substitution
        context = self._build_context(row)

        # Map user fields first
        user = self._map_user_fields(row, context)

        # Rebuild context with user data so account/course fields can reference user fields
        user_data = user.model_dump(exclude_none=True)
        context = self._build_context(row, user_data)

        # Map account fields (optional)
        accounts = []
        if self.config.account_fields:
            account = self._map_account_fields(row, context)
            if account:
                accounts.append(account)

        # Map course member fields (optional)
        course_members = []
        if self.config.course_member_fields:
            course_members = self._map_course_member_fields(row, context)

        return UserAccountDeployment(
            user=user,
            accounts=accounts,
            course_members=course_members
        )

    def _build_context(self, row: Dict[str, Any], user_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Build context dictionary for template substitution.

        Context includes all row values plus any computed values.

        Args:
            row: Row dictionary
            user_data: Already computed user data fields (for referencing in accounts/course members)

        Returns:
            Context dictionary
        """
        # Start with all row values
        context = dict(row)

        # Add user data if provided (so we can reference user fields like {email} from user data)
        if user_data:
            context.update(user_data)

        # Add default values from transformations config
        if self.config.transformations and self.config.transformations.default_values:
            for key, value in self.config.transformations.default_values.items():
                if key not in context or self._is_null(context[key]):
                    context[key] = value

        return context

    def _map_user_fields(self, row: Dict[str, Any], context: Dict[str, Any]) -> UserDeployment:
        """
        Map row to UserDeployment.

        Args:
            row: Row dictionary
            context: Context for template substitution

        Returns:
            UserDeployment instance
        """
        user_data = {}
        user_config = self.config.user_fields

        # Map fields in order, updating context as we go so later fields can reference earlier ones
        for field_name in UserDeployment.model_fields.keys():
            field_config = getattr(user_config, field_name, None)
            if field_config is None:
                continue

            value = self._extract_field_value(field_config, row, context, field_name)
            if value is not None:
                user_data[field_name] = value
                # Add to context so subsequent fields can reference this one
                context[field_name] = value

        return UserDeployment(**user_data)

    def _map_account_fields(self, row: Dict[str, Any], context: Dict[str, Any]) -> Optional[AccountDeployment]:
        """
        Map row to AccountDeployment.

        Args:
            row: Row dictionary
            context: Context for template substitution

        Returns:
            AccountDeployment instance or None if not enough data
        """
        account_data = {}
        account_config = self.config.account_fields

        for field_name in AccountDeployment.model_fields.keys():
            field_config = getattr(account_config, field_name, None)
            if field_config is None:
                continue

            value = self._extract_field_value(field_config, row, context, field_name)
            if value is not None:
                account_data[field_name] = value

        # Only create account if we have required fields (provider and type)
        # Note: provider and type have defaults, so check if we got any data at all
        if not account_data:
            return None

        # Ensure we have at least provider and type
        if "provider" not in account_data or "type" not in account_data:
            return None

        return AccountDeployment(**account_data)

    def _map_course_member_fields(
        self,
        row: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[CourseMemberDeployment]:
        """
        Map row to CourseMemberDeployment list.

        Supports single or multiple course memberships per row.

        Args:
            row: Row dictionary
            context: Context for template substitution

        Returns:
            List of CourseMemberDeployment instances
        """
        course_members = []

        # Handle single or list of course member configs
        cm_configs = self.config.course_member_fields
        if not isinstance(cm_configs, list):
            cm_configs = [cm_configs]

        for cm_config in cm_configs:
            # Check condition if specified
            if cm_config.condition:
                if not self._evaluate_condition(cm_config.condition, context):
                    continue

            member_data = {}
            for field_name in CourseMemberDeployment.model_fields.keys():
                if field_name == "condition":  # Skip internal field
                    continue

                field_config = getattr(cm_config, field_name, None)
                if field_config is None:
                    continue

                value = self._extract_field_value(field_config, row, context, field_name)
                if value is not None:
                    member_data[field_name] = value

            # Only create course member if we have either ID or path-based identification
            has_id = member_data.get("id") is not None
            has_path = (
                member_data.get("organization") is not None
                and member_data.get("course_family") is not None
                and member_data.get("course") is not None
            )

            if has_id or has_path:
                course_members.append(CourseMemberDeployment(**member_data))

        return course_members

    def _extract_field_value(
        self,
        field_config: Union[str, FieldMappingConfig, Any],
        row: Dict[str, Any],
        context: Dict[str, Any],
        field_name: str
    ) -> Any:
        """
        Extract field value from row using field configuration.

        Args:
            field_config: Field configuration (string column name or FieldMappingConfig)
            row: Row dictionary
            context: Context for substitution
            field_name: Target field name

        Returns:
            Extracted and transformed value
        """
        # Handle simple string mapping (column name OR literal value)
        if isinstance(field_config, str):
            # First try as column name
            if field_config in row:
                value = self._get_row_value(row, field_config)
                # If column value is None/empty and we have a context default for this field, use it
                if value is None and field_name in context:
                    return context[field_name]
                return value
            # Otherwise treat as literal value
            return field_config

        # Handle literal values (non-mapping config objects)
        # Important: Check for bool/int/etc first before dict check
        if isinstance(field_config, (bool, int, float)):
            return field_config

        if not isinstance(field_config, (dict, FieldMappingConfig)):
            return field_config

        # Convert dict to FieldMappingConfig if needed
        if isinstance(field_config, dict):
            # Handle simple dict with literal/template/ref
            if "literal" in field_config:
                return field_config["literal"]
            if "ref" in field_config:
                ref_field = field_config["ref"]
                return context.get(ref_field)
            if "template" in field_config:
                template = field_config["template"]
                value = self.transformer.substitute_template(template, context)
                # Apply transformation if specified
                if "transform" in field_config:
                    value = self.transformer.apply_transformation(value, field_config["transform"], context)
                return value

            # Try to create FieldMappingConfig
            try:
                field_config = FieldMappingConfig(**field_config)
            except:
                # If it fails, treat as literal value
                return field_config

        # Handle FieldMappingConfig
        if isinstance(field_config, FieldMappingConfig):
            source = field_config.source

            # Handle different source types
            if isinstance(source, str):
                # Simple column reference
                value = self._get_row_value(row, source)
            elif isinstance(source, dict):
                if "literal" in source:
                    value = source["literal"]
                elif "ref" in source:
                    value = context.get(source["ref"])
                elif "template" in source:
                    value = self.transformer.substitute_template(source["template"], context)
                else:
                    value = None
            else:
                value = source  # Literal value

            # Apply transformation if specified
            if field_config.transform and value is not None:
                value = self.transformer.apply_transformation(value, field_config.transform, context)

            # Use default if value is null
            if self._is_null(value) and field_config.default is not None:
                value = field_config.default

            # Check required constraint
            if field_config.required and self._is_null(value):
                raise MappingError(f"Required field '{field_name}' is missing or empty")

            return value

        return None

    def _get_row_value(self, row: Dict[str, Any], column_name: str) -> Any:
        """
        Get value from row by column name.

        Args:
            row: Row dictionary
            column_name: Column name

        Returns:
            Column value or None if not found
        """
        value = row.get(column_name)
        if self._is_null(value):
            return None
        return value

    def _is_null(self, value: Any) -> bool:
        """
        Check if value should be treated as null.

        Args:
            value: Value to check

        Returns:
            True if value is null/empty
        """
        # Special handling for booleans and numbers - they are never null even if False or 0
        if isinstance(value, (bool, int, float)):
            return False

        null_values = (
            self.config.transformations.null_values
            if self.config.transformations
            else None
        )
        return self.transformer.is_null_value(value, null_values)

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """
        Evaluate a simple condition expression.

        Supports basic comparisons like:
        - {field} != ""
        - {field} == "value"

        Args:
            condition: Condition expression
            context: Context for variable substitution

        Returns:
            True if condition evaluates to true
        """
        # Substitute variables
        evaluated = self.transformer.substitute_template(condition, context)

        # Handle common patterns
        if " != " in evaluated:
            left, right = evaluated.split(" != ", 1)
            return left.strip().strip('"').strip("'") != right.strip().strip('"').strip("'")

        if " == " in evaluated:
            left, right = evaluated.split(" == ", 1)
            return left.strip().strip('"').strip("'") == right.strip().strip('"').strip("'")

        # Default: non-empty string is true
        return bool(evaluated.strip())
