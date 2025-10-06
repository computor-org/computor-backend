#!/usr/bin/env python3
"""
Test version constraint resolution logic.

This test simulates the version constraint resolution where:
- Constraints are specified using version_tags (strings like "v1.0", "spring-2024")
- Resolution uses version_numbers (integers) for ordering
- Different operators (>=, <=, >, <, ==) work on the version_numbers
"""

from typing import List, Optional, NamedTuple
from dataclasses import dataclass


class Version(NamedTuple):
    """Simulates an ExampleVersion record."""
    version_tag: str
    version_number: int


@dataclass
class ConstraintTestCase:
    """Test case for version constraint resolution."""
    name: str
    constraint: str
    versions: List[Version]
    expected_tag: Optional[str]
    expected_reason: str


def parse_constraint(constraint: str) -> tuple[str, str]:
    """Parse a constraint string into operator and version_tag."""
    operators = [">=", "<=", "==", ">", "<"]
    
    for op in operators:
        if constraint.startswith(op):
            return op, constraint[len(op):].strip()
    
    # No operator means exact match
    return "==", constraint.strip()


def resolve_constraint(constraint: str, versions: List[Version]) -> Optional[Version]:
    """
    Resolve a version constraint to a specific version.
    
    Logic:
    1. Parse constraint to get operator and target version_tag
    2. Find the target version by tag to get its version_number
    3. Apply operator using version_numbers for comparison
    4. Return the appropriate version based on the operator
    """
    if not constraint or constraint == "*" or constraint == "latest":
        # No constraint means latest version
        return max(versions, key=lambda v: v.version_number) if versions else None
    
    operator, target_tag = parse_constraint(constraint)
    
    # Find target version by tag
    target_version = None
    for v in versions:
        if v.version_tag == target_tag:
            target_version = v
            break
    
    if not target_version:
        return None  # Target version not found
    
    target_number = target_version.version_number
    
    # Filter versions based on operator
    if operator == ">=":
        # Return oldest version >= target
        candidates = [v for v in versions if v.version_number >= target_number]
        return min(candidates, key=lambda v: v.version_number) if candidates else None
    
    elif operator == "<=":
        # Return newest version <= target
        candidates = [v for v in versions if v.version_number <= target_number]
        return max(candidates, key=lambda v: v.version_number) if candidates else None
    
    elif operator == ">":
        # Return oldest version > target
        candidates = [v for v in versions if v.version_number > target_number]
        return min(candidates, key=lambda v: v.version_number) if candidates else None
    
    elif operator == "<":
        # Return newest version < target
        candidates = [v for v in versions if v.version_number < target_number]
        return max(candidates, key=lambda v: v.version_number) if candidates else None
    
    elif operator == "==":
        # Return exact match
        return target_version
    
    return None


def run_test_cases():
    """Run all test cases and report results."""
    
    # Define a set of versions with non-sequential tags
    versions = [
        Version("alpha-1", 1),
        Version("beta-2", 2),
        Version("spring-2024", 3),
        Version("summer-2024", 4),
        Version("v1.0", 5),
        Version("v1.1", 6),
        Version("fall-2024", 7),
        Version("v2.0", 8),
        Version("winter-2025", 9),
        Version("v3.0-beta", 10),
    ]
    
    test_cases = [
        # Latest version tests
        ConstraintTestCase(
            name="No constraint returns latest",
            constraint="",
            versions=versions,
            expected_tag="v3.0-beta",
            expected_reason="Should return version with highest version_number (10)"
        ),
        ConstraintTestCase(
            name="Wildcard returns latest",
            constraint="*",
            versions=versions,
            expected_tag="v3.0-beta",
            expected_reason="Wildcard should return version with highest version_number"
        ),
        
        # >= operator tests
        ConstraintTestCase(
            name=">= with spring-2024",
            constraint=">=spring-2024",
            versions=versions,
            expected_tag="spring-2024",
            expected_reason=">= returns oldest version with number >= 3 (spring-2024 itself)"
        ),
        ConstraintTestCase(
            name=">= with v1.0",
            constraint=">=v1.0",
            versions=versions,
            expected_tag="v1.0",
            expected_reason=">= returns oldest version with number >= 5 (v1.0 itself)"
        ),
        
        # <= operator tests
        ConstraintTestCase(
            name="<= with v1.1",
            constraint="<=v1.1",
            versions=versions,
            expected_tag="v1.1",
            expected_reason="<= returns newest version with number <= 6 (v1.1 itself)"
        ),
        ConstraintTestCase(
            name="<= with summer-2024",
            constraint="<=summer-2024",
            versions=versions,
            expected_tag="summer-2024",
            expected_reason="<= returns newest version with number <= 4 (summer-2024 itself)"
        ),
        
        # > operator tests
        ConstraintTestCase(
            name="> with spring-2024",
            constraint=">spring-2024",
            versions=versions,
            expected_tag="summer-2024",
            expected_reason="> returns oldest version with number > 3 (summer-2024 with number 4)"
        ),
        ConstraintTestCase(
            name="> with v2.0",
            constraint=">v2.0",
            versions=versions,
            expected_tag="winter-2025",
            expected_reason="> returns oldest version with number > 8 (winter-2025 with number 9)"
        ),
        
        # < operator tests
        ConstraintTestCase(
            name="< with v1.0",
            constraint="<v1.0",
            versions=versions,
            expected_tag="summer-2024",
            expected_reason="< returns newest version with number < 5 (summer-2024 with number 4)"
        ),
        ConstraintTestCase(
            name="< with spring-2024",
            constraint="<spring-2024",
            versions=versions,
            expected_tag="beta-2",
            expected_reason="< returns newest version with number < 3 (beta-2 with number 2)"
        ),
        
        # == operator tests
        ConstraintTestCase(
            name="== with fall-2024",
            constraint="==fall-2024",
            versions=versions,
            expected_tag="fall-2024",
            expected_reason="== returns exact match for fall-2024"
        ),
        ConstraintTestCase(
            name="Implicit == with v2.0",
            constraint="v2.0",
            versions=versions,
            expected_tag="v2.0",
            expected_reason="No operator means exact match for v2.0"
        ),
        
        # Edge cases
        ConstraintTestCase(
            name="Non-existent version",
            constraint=">=v99.0",
            versions=versions,
            expected_tag=None,
            expected_reason="Version v99.0 doesn't exist, should return None"
        ),
        ConstraintTestCase(
            name="Empty version list",
            constraint=">=v1.0",
            versions=[],
            expected_tag=None,
            expected_reason="No versions available, should return None"
        ),
        ConstraintTestCase(
            name="> with highest version",
            constraint=">v3.0-beta",
            versions=versions,
            expected_tag=None,
            expected_reason="No version higher than v3.0-beta (number 10), should return None"
        ),
        ConstraintTestCase(
            name="< with lowest version",
            constraint="<alpha-1",
            versions=versions,
            expected_tag=None,
            expected_reason="No version lower than alpha-1 (number 1), should return None"
        ),
    ]
    
    print("=" * 80)
    print("VERSION CONSTRAINT RESOLUTION TESTS")
    print("=" * 80)
    print()
    print("Available versions:")
    for v in versions:
        print(f"  {v.version_tag:15} -> version_number: {v.version_number}")
    print()
    print("=" * 80)
    print()
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        result = resolve_constraint(test.constraint, test.versions)
        result_tag = result.version_tag if result else None
        
        if result_tag == test.expected_tag:
            passed += 1
            status = "✅ PASS"
        else:
            failed += 1
            status = "❌ FAIL"
        
        print(f"{status}: {test.name}")
        print(f"  Constraint: '{test.constraint}'")
        print(f"  Expected: {test.expected_tag}")
        print(f"  Got: {result_tag}")
        print(f"  Reason: {test.expected_reason}")
        if result_tag != test.expected_tag:
            print(f"  ERROR: Result doesn't match expected!")
        print()
    
    print("=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)
    
    return failed == 0


def test_complex_scenarios():
    """Test more complex real-world scenarios."""
    print("\n" + "=" * 80)
    print("COMPLEX SCENARIO TESTS")
    print("=" * 80)
    print()
    
    # Scenario 1: Semantic versioning-like tags
    print("Scenario 1: Semantic versioning tags")
    print("-" * 40)
    sem_versions = [
        Version("1.0.0", 1),
        Version("1.0.1", 2),
        Version("1.1.0", 3),
        Version("1.2.0", 4),
        Version("2.0.0", 5),
        Version("2.0.1", 6),
        Version("2.1.0", 7),
        Version("3.0.0-alpha", 8),
        Version("3.0.0-beta", 9),
        Version("3.0.0", 10),
    ]
    
    sem_tests = [
        (">=2.0.0", "2.0.0", "Get 2.0.0 or higher"),
        ("<3.0.0", "3.0.0-beta", "Get latest before 3.0.0 release"),
        (">1.1.0", "1.2.0", "Get next version after 1.1.0"),
        ("<=2.1.0", "2.1.0", "Get 2.1.0 or earlier"),
    ]
    
    for constraint, expected, description in sem_tests:
        result = resolve_constraint(constraint, sem_versions)
        result_tag = result.version_tag if result else None
        status = "✅" if result_tag == expected else "❌"
        print(f"  {status} {constraint:12} -> {result_tag:15} ({description})")
    
    # Scenario 2: Date-based tags
    print("\nScenario 2: Date-based version tags")
    print("-" * 40)
    date_versions = [
        Version("2024-01-15", 1),
        Version("2024-02-01", 2),
        Version("2024-03-15", 3),
        Version("2024-04-01", 4),
        Version("2024-05-15", 5),
        Version("2024-06-01", 6),
        Version("2024-07-15", 7),
        Version("2024-08-01", 8),
    ]
    
    date_tests = [
        (">=2024-04-01", "2024-04-01", "Get April release or later"),
        ("<2024-06-01", "2024-05-15", "Get latest before June"),
        (">2024-02-01", "2024-03-15", "Get next release after February"),
    ]
    
    for constraint, expected, description in date_tests:
        result = resolve_constraint(constraint, date_versions)
        result_tag = result.version_tag if result else None
        status = "✅" if result_tag == expected else "❌"
        print(f"  {status} {constraint:15} -> {result_tag:15} ({description})")
    
    # Scenario 3: Mixed naming schemes
    print("\nScenario 3: Mixed naming schemes (realistic scenario)")
    print("-" * 40)
    mixed_versions = [
        Version("initial", 1),
        Version("v0.1-draft", 2),
        Version("spring2024", 3),
        Version("v1.0", 4),
        Version("summer2024", 5),
        Version("v1.1-hotfix", 6),
        Version("fall2024", 7),
        Version("v2.0-rc1", 8),
        Version("v2.0", 9),
        Version("latest", 10),
    ]
    
    mixed_tests = [
        (">=v1.0", "v1.0", "Get v1.0 or later"),
        (">spring2024", "v1.0", "Get next after spring semester"),
        ("<=fall2024", "fall2024", "Get fall2024 or earlier"),
        ("latest", "latest", "Get the latest version"),
    ]
    
    for constraint, expected, description in mixed_tests:
        result = resolve_constraint(constraint, mixed_versions)
        result_tag = result.version_tag if result else None
        status = "✅" if result_tag == expected else "❌"
        print(f"  {status} {constraint:15} -> {result_tag:15} ({description})")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Run basic tests
    success = run_test_cases()
    
    # Run complex scenario tests
    test_complex_scenarios()
    
    if success:
        print("\n✅ All basic tests passed!")
    else:
        print("\n❌ Some tests failed!")
        exit(1)