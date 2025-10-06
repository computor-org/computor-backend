"""
Dependency synchronization service.

Handles syncing testDependencies from meta.yaml to database ExampleDependency records.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from ..model.example import Example, ExampleDependency
from ..custom_types import Ltree
from ..api.exceptions import BadRequestException

logger = logging.getLogger(__name__)


class DependencySyncService:
    """Service for syncing testDependencies from meta.yaml to database."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def sync_dependencies_from_meta(
        self, 
        example: Example, 
        test_dependencies: List[Any],
        repository_id: str
    ) -> None:
        """
        Sync testDependencies from meta.yaml to ExampleDependency database records.
        
        Args:
            example: The Example object to create dependencies for
            test_dependencies: List from meta.yaml testDependencies field
            repository_id: Repository ID to validate dependencies exist in same repo
            
        Raises:
            BadRequestException: If any dependencies are missing
        """
        if not test_dependencies:
            logger.info(f"No test dependencies found for example {example.identifier}")
            return
        
        logger.info(f"Processing {len(test_dependencies)} test dependencies for example {example.identifier}")
        
        # First, remove existing dependencies for this example (in case they changed)
        self.db.query(ExampleDependency).filter(
            ExampleDependency.example_id == example.id
        ).delete()
        
        # Parse and validate dependencies
        parsed_dependencies = self._parse_test_dependencies(test_dependencies)
        missing_dependencies = []
        found_dependencies = []
        
        for dep_identifier, version_constraint in parsed_dependencies:
            # Find the dependency example by identifier
            dep_example = self.db.query(Example).filter(
                Example.identifier == Ltree(dep_identifier),
                Example.example_repository_id == repository_id  # Dependencies must be in same repository
            ).first()
            
            if dep_example:
                found_dependencies.append((dep_identifier, dep_example, version_constraint))
            else:
                missing_dependencies.append(dep_identifier)
        
        # If any dependencies are missing, return 400 error
        if missing_dependencies:
            missing_list = ", ".join(missing_dependencies)
            raise BadRequestException(
                f"Cannot upload example '{example.identifier}'. "
                f"Missing dependencies: {missing_list}. "
                f"Please upload the dependency examples first."
            )
        
        # All dependencies found, add them with version constraints
        for dep_identifier, dep_example, version_constraint in found_dependencies:
            dependency = ExampleDependency(
                example_id=example.id,
                depends_id=dep_example.id,
                version_constraint=version_constraint
            )
            self.db.add(dependency)
            constraint_info = f" (constraint: {version_constraint})" if version_constraint else " (latest)"
            logger.info(f"Added dependency: {example.identifier} -> {dep_identifier}{constraint_info}")
        
        self.db.commit()
    
    def _parse_test_dependencies(self, test_dependencies: List[Any]) -> List[Tuple[str, Optional[str]]]:
        """
        Parse testDependencies list supporting both string and structured formats.
        
        Args:
            test_dependencies: Raw testDependencies list from meta.yaml
            
        Returns:
            List of (identifier, version_constraint) tuples
        """
        parsed = []
        
        for dep_item in test_dependencies:
            # Handle both string format and structured format
            if isinstance(dep_item, str):
                # Old string format: just the slug/identifier, no version constraint
                dep_identifier = dep_item
                version_constraint = None
                parsed.append((dep_identifier, version_constraint))
                
            elif isinstance(dep_item, dict):
                # New structured format: has slug and version fields
                dep_identifier = dep_item.get('slug')
                version_constraint = dep_item.get('version')
                
                if not dep_identifier:
                    logger.warning(f"Skipping dependency with missing slug: {dep_item}")
                    continue
                
                # Basic validation of version constraint format
                if version_constraint and not self._is_valid_version_constraint(version_constraint):
                    logger.warning(f"Invalid version constraint '{version_constraint}' for dependency {dep_identifier}")
                    # Don't fail upload, just log warning and continue
                
                parsed.append((dep_identifier, version_constraint))
                
            else:
                logger.warning(f"Skipping invalid dependency format: {dep_item}")
                continue
        
        return parsed
    
    def _is_valid_version_constraint(self, constraint: str) -> bool:
        """
        Basic validation of version constraint format.
        
        Args:
            constraint: Version constraint string
            
        Returns:
            True if constraint appears valid
        """
        if not constraint or not isinstance(constraint, str):
            return False
        
        # Check for valid prefixes
        valid_prefixes = ['>=', '<=', '>', '<', '^', '~', '==']
        has_valid_prefix = any(constraint.startswith(prefix) for prefix in valid_prefixes)
        
        # Remove prefix to check version part
        version_part = constraint
        for prefix in sorted(valid_prefixes, key=len, reverse=True):
            if constraint.startswith(prefix):
                version_part = constraint[len(prefix):]
                break
        
        # Basic check: should contain mostly alphanumeric characters, dots, dashes, plus
        if version_part:
            clean_version = version_part.replace('.', '').replace('-', '').replace('+', '')
            return clean_version.isalnum()
        
        return has_valid_prefix  # Has prefix but no version part - might be valid
    
    def get_dependencies_with_constraints(self, example_id: str) -> List[Tuple[str, Optional[str]]]:
        """
        Get all dependencies for an example with their version constraints.
        
        Args:
            example_id: Example UUID
            
        Returns:
            List of (dependency_identifier, version_constraint) tuples
        """
        dependencies = self.db.query(ExampleDependency).filter(
            ExampleDependency.example_id == example_id
        ).all()
        
        result = []
        for dep in dependencies:
            dep_example = self.db.query(Example).filter(
                Example.id == dep.depends_id
            ).first()
            if dep_example:
                result.append((str(dep_example.identifier), dep.version_constraint))
        
        return result