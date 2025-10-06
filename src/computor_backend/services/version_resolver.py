"""
Version constraint resolution service.

Handles semantic version constraint resolution for example dependencies.
"""

import re
from typing import List, Optional
from sqlalchemy.orm import Session

from ..model.example import Example, ExampleVersion


class VersionResolver:
    """Resolves version constraints to specific example versions."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def resolve_constraint(self, example_slug: str, constraint: Optional[str]) -> Optional[ExampleVersion]:
        """
        Resolve version constraint to a specific ExampleVersion.
        
        Args:
            example_slug: The hierarchical slug/identifier of the example
            constraint: Version constraint string (e.g., '>=1.2.0', '^2.1.0', '1.0.0')
                       If None, returns latest version
        
        Returns:
            ExampleVersion that satisfies the constraint, or None if not found
        """
        # Find the example by identifier
        example = self.db.query(Example).filter(
            Example.identifier == example_slug
        ).first()
        
        if not example:
            return None
        
        # Get all versions for this example
        all_versions = self.db.query(ExampleVersion).filter(
            ExampleVersion.example_id == example.id
        ).order_by(ExampleVersion.version_number.desc()).all()
        
        if not all_versions:
            return None
        
        # If no constraint specified, return latest version
        if not constraint:
            return all_versions[0]
        
        # Parse and resolve constraint
        return self._resolve_constraint_against_versions(constraint, all_versions)
    
    def _resolve_constraint_against_versions(self, constraint: str, versions: List[ExampleVersion]) -> Optional[ExampleVersion]:
        """
        Resolve version constraint against a list of available versions using database-level ordering.
        
        Uses version_number for proper ordering and version_tag for matching.
        This approach works with arbitrary version tag strings.
        
        Args:
            constraint: Version constraint string
            versions: List of ExampleVersion objects (should be sorted by version_number desc)  
        
        Returns:
            First version that satisfies constraint, or None
        """
        
        # Handle different constraint operators
        if constraint.startswith('>='):
            target_tag = constraint[2:]
            return self._find_version_with_number_constraint(target_tag, versions, '>=')
            
        elif constraint.startswith('<='):
            target_tag = constraint[2:]
            return self._find_version_with_number_constraint(target_tag, versions, '<=')
            
        elif constraint.startswith('>'):
            target_tag = constraint[1:]
            return self._find_version_with_number_constraint(target_tag, versions, '>')
            
        elif constraint.startswith('<'):
            target_tag = constraint[1:]
            return self._find_version_with_number_constraint(target_tag, versions, '<')
            
        elif constraint.startswith('^'):
            # Compatible version range - use semantic versioning concept but with version_number
            target_tag = constraint[1:]
            return self._find_compatible_version(target_tag, versions)
            
        elif constraint.startswith('~'):
            # Patch-level compatibility - similar to ^ but more restrictive
            target_tag = constraint[1:]
            return self._find_patch_compatible_version(target_tag, versions)
            
        elif constraint.startswith('=='):
            # Exact version match
            target_tag = constraint[2:]
            return self._find_exact_version(target_tag, versions)
            
        else:
            # No operator prefix - treat as exact match
            return self._find_exact_version(constraint, versions)
    
    def _find_version_with_number_constraint(self, target_tag: str, versions: List[ExampleVersion], operator: str) -> Optional[ExampleVersion]:
        """Find version using version_number for ordering."""
        # First, find the target version to get its version_number
        target_version = self._find_exact_version(target_tag, versions)
        if not target_version:
            return None
        
        target_number = target_version.version_number
        
        # Apply the constraint using version_number
        if operator == '>=':
            # Find the oldest version that satisfies >= constraint
            candidates = [v for v in versions if v.version_number >= target_number]
            return min(candidates, key=lambda v: v.version_number) if candidates else None
            
        elif operator == '<=':
            # Find the newest version that satisfies <= constraint
            candidates = [v for v in versions if v.version_number <= target_number]
            return max(candidates, key=lambda v: v.version_number) if candidates else None
            
        elif operator == '>':
            # Find the oldest version that satisfies > constraint
            candidates = [v for v in versions if v.version_number > target_number]
            return min(candidates, key=lambda v: v.version_number) if candidates else None
            
        elif operator == '<':
            # Find the newest version that satisfies < constraint
            candidates = [v for v in versions if v.version_number < target_number]
            return max(candidates, key=lambda v: v.version_number) if candidates else None
        
        return None
    
    def _find_exact_version(self, target_tag: str, versions: List[ExampleVersion]) -> Optional[ExampleVersion]:
        """Find exact version by version_tag."""
        for v in versions:
            if v.version_tag == target_tag:
                return v
        return None
    
    def _find_compatible_version(self, target_tag: str, versions: List[ExampleVersion]) -> Optional[ExampleVersion]:
        """
        Find compatible version (^ operator).
        
        For database-level ordering, we interpret ^ as "same major version or higher"
        based on version_number, falling back to newest available if semantic parsing fails.
        """
        target_version = self._find_exact_version(target_tag, versions)
        if not target_version:
            return None
        
        try:
            # Try semantic version parsing for major version extraction
            from packaging import version
            target_parsed = version.parse(target_tag)
            target_major = target_parsed.major
            
            # Find versions with same major version and >= version_number
            compatible = []
            for v in versions:
                if v.version_number >= target_version.version_number:
                    try:
                        v_parsed = version.parse(v.version_tag)
                        if v_parsed.major == target_major:
                            compatible.append(v)
                    except:
                        # If parsing fails, include version if it's >= target number
                        compatible.append(v)
            
            return min(compatible, key=lambda v: v.version_number) if compatible else None
            
        except:
            # Fallback: just use >= constraint
            return self._find_version_with_number_constraint(target_tag, versions, '>=')
    
    def _find_patch_compatible_version(self, target_tag: str, versions: List[ExampleVersion]) -> Optional[ExampleVersion]:
        """
        Find patch-compatible version (~ operator).
        
        For database-level ordering, we interpret ~ as "same major.minor version or higher patch"
        based on version_number, falling back to >= constraint if semantic parsing fails.
        """
        target_version = self._find_exact_version(target_tag, versions)
        if not target_version:
            return None
        
        try:
            # Try semantic version parsing for major.minor version extraction
            from packaging import version
            target_parsed = version.parse(target_tag)
            target_major = target_parsed.major
            target_minor = target_parsed.minor
            
            # Find versions with same major.minor version and >= version_number
            compatible = []
            for v in versions:
                if v.version_number >= target_version.version_number:
                    try:
                        v_parsed = version.parse(v.version_tag)
                        if v_parsed.major == target_major and v_parsed.minor == target_minor:
                            compatible.append(v)
                    except:
                        # If parsing fails, include version if it's >= target number
                        compatible.append(v)
            
            return min(compatible, key=lambda v: v.version_number) if compatible else None
            
        except:
            # Fallback: just use >= constraint
            return self._find_version_with_number_constraint(target_tag, versions, '>=')
    
    def resolve_multiple_constraints(self, constraints: List[tuple]) -> List[ExampleVersion]:
        """
        Resolve multiple version constraints.
        
        Args:
            constraints: List of (example_slug, version_constraint) tuples
            
        Returns:
            List of resolved ExampleVersion objects
        """
        resolved = []
        for slug, constraint in constraints:
            version_obj = self.resolve_constraint(slug, constraint)
            if version_obj:
                resolved.append(version_obj)
        
        return resolved