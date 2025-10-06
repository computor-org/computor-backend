"""
Test runner configuration for comprehensive DTO testing.
"""

import pytest
import sys
import os

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


def run_validation_tests():
    """Run only DTO validation tests"""
    return pytest.main([
        "src/computor_backend/tests/test_dto_validation.py",
        "-v",
        "--tb=short"
    ])


def run_property_tests():
    """Run computed property tests"""
    return pytest.main([
        "src/computor_backend/tests/test_dto_properties.py", 
        "-v",
        "--tb=short"
    ])


def run_caching_tests():
    """Run Redis caching tests (disabled - caching removed)"""
    print("Redis caching tests have been removed")
    return 0


def run_edge_case_tests():
    """Run edge case and error handling tests"""
    return pytest.main([
        "src/computor_backend/tests/test_dto_edge_cases.py",
        "-v",
        "--tb=short"
    ])


def run_all_dto_tests():
    """Run all DTO-related tests"""
    test_files = [
        "src/computor_backend/tests/test_dto_validation.py",
        "src/computor_backend/tests/test_dto_properties.py", 
        "src/computor_backend/tests/test_dto_edge_cases.py"
    ]
    
    return pytest.main([
        *test_files,
        "-v",
        "--tb=short",
        "--maxfail=10",  # Stop after 10 failures
        "--durations=10"  # Show 10 slowest tests
    ])


def run_specific_dto_tests(dto_name):
    """Run tests for a specific DTO (e.g., 'user', 'organization')"""
    return pytest.main([
        "src/computor_backend/tests/",
        "-k", dto_name.lower(),
        "-v",
        "--tb=short"
    ])


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run DTO tests")
    parser.add_argument(
        "--type", 
        choices=["validation", "properties", "caching", "edge_cases", "all"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--dto",
        help="Run tests for specific DTO (e.g., user, organization)"
    )
    
    args = parser.parse_args()
    
    if args.dto:
        exit_code = run_specific_dto_tests(args.dto)
    elif args.type == "validation":
        exit_code = run_validation_tests()
    elif args.type == "properties":
        exit_code = run_property_tests()
    elif args.type == "caching":
        exit_code = run_caching_tests()
    elif args.type == "edge_cases":
        exit_code = run_edge_case_tests()
    else:
        exit_code = run_all_dto_tests()
    
    sys.exit(exit_code)