"""
Integration Test Helpers

Provides utilities for testing API permissions with different user roles.
"""

import os
import sys
import json
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dotenv import load_dotenv
import httpx
from dataclasses import dataclass

# Load environment variables from config/.env
config_dir = Path(__file__).parent.parent / "config"
env_file = config_dir / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    print(f"Warning: .env file not found at {env_file}")
    print("Using environment variables or defaults")


@dataclass
class TestUser:
    """Represents a test user with credentials"""
    username: str
    password: str
    role: str
    email: str
    name: str


@dataclass
class TestResult:
    """Represents the result of a single API test"""
    endpoint: str
    method: str
    user_role: str
    expected_status: int
    actual_status: int
    passed: bool
    error_message: Optional[str] = None
    response_data: Optional[Dict] = None


class APITestClient:
    """HTTP client for testing API endpoints with authentication"""

    def __init__(self, base_url: str = None, timeout: int = 30):
        self.base_url = base_url or os.getenv("API_BASE_URL", "http://localhost:8000")
        self.timeout = timeout
        self.token: Optional[str] = None
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)

    async def login(self, username: str, password: str) -> bool:
        """
        Authenticate with the API and store the token

        Returns:
            True if authentication succeeded, False otherwise
        """
        try:
            response = await self.client.post(
                "/auth/login",
                json={"username": username, "password": password}
            )

            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                return True
            else:
                print(f"Login failed for {username}: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"Login error for {username}: {e}")
            return False

    async def request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        expected_status: int = 200
    ) -> TestResult:
        """
        Make an authenticated API request and return the result

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint path
            json_data: JSON body for POST/PUT requests
            params: Query parameters
            expected_status: Expected HTTP status code

        Returns:
            TestResult object with the outcome
        """
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            response = await self.client.request(
                method=method,
                url=endpoint,
                json=json_data,
                params=params,
                headers=headers
            )

            # Try to parse response as JSON
            try:
                response_data = response.json()
            except:
                response_data = {"raw": response.text}

            passed = response.status_code == expected_status

            return TestResult(
                endpoint=endpoint,
                method=method,
                user_role="authenticated" if self.token else "anonymous",
                expected_status=expected_status,
                actual_status=response.status_code,
                passed=passed,
                response_data=response_data if passed else None,
                error_message=None if passed else f"Expected {expected_status}, got {response.status_code}"
            )

        except Exception as e:
            return TestResult(
                endpoint=endpoint,
                method=method,
                user_role="authenticated" if self.token else "anonymous",
                expected_status=expected_status,
                actual_status=0,
                passed=False,
                error_message=str(e)
            )

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


class PermissionTestRunner:
    """Runs permission tests for different user roles"""

    def __init__(self):
        self.results: List[TestResult] = []
        self.base_url = os.getenv("API_BASE_URL", "http://localhost:8000")

    async def run_test_suite(
        self,
        user: TestUser,
        test_cases: List[Dict[str, Any]]
    ) -> Tuple[int, int]:
        """
        Run a suite of tests for a specific user

        Args:
            user: TestUser to authenticate as
            test_cases: List of test case dictionaries with:
                - method: HTTP method
                - endpoint: API endpoint
                - expected_status: Expected HTTP status code
                - json_data: Optional JSON body
                - params: Optional query parameters
                - description: Test case description

        Returns:
            Tuple of (passed_count, failed_count)
        """
        client = APITestClient(self.base_url)

        # Authenticate
        print(f"\n{'='*80}")
        print(f"Testing as: {user.name} ({user.role})")
        print(f"{'='*80}")

        auth_success = await client.login(user.username, user.password)
        if not auth_success:
            print(f"❌ Authentication failed for {user.username}")
            await client.close()
            return 0, len(test_cases)

        print(f"✓ Authenticated successfully\n")

        passed = 0
        failed = 0

        # Run each test case
        for i, test_case in enumerate(test_cases, 1):
            description = test_case.get("description", f"Test {i}")

            result = await client.request(
                method=test_case["method"],
                endpoint=test_case["endpoint"],
                json_data=test_case.get("json_data"),
                params=test_case.get("params"),
                expected_status=test_case["expected_status"]
            )

            result.user_role = user.role
            self.results.append(result)

            if result.passed:
                passed += 1
                status_icon = "✓"
            else:
                failed += 1
                status_icon = "✗"

            print(f"{status_icon} {description}")
            print(f"  {result.method} {result.endpoint}")
            print(f"  Expected: {result.expected_status}, Got: {result.actual_status}")

            if not result.passed and result.error_message:
                print(f"  Error: {result.error_message}")

            print()

        await client.close()
        return passed, failed

    def print_summary(self):
        """Print a summary of all test results"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed

        print(f"\n{'='*80}")
        print("TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Total Tests: {total}")
        print(f"Passed: {passed} ({100*passed/total if total > 0 else 0:.1f}%)")
        print(f"Failed: {failed} ({100*failed/total if total > 0 else 0:.1f}%)")
        print(f"{'='*80}\n")

        if failed > 0:
            print("Failed Tests:")
            for result in self.results:
                if not result.passed:
                    print(f"  - [{result.user_role}] {result.method} {result.endpoint}")
                    print(f"    Expected {result.expected_status}, got {result.actual_status}")
                    if result.error_message:
                        print(f"    {result.error_message}")
            print()

    def save_results(self, output_file: Path):
        """Save test results to a JSON file"""
        results_data = {
            "total": len(self.results),
            "passed": sum(1 for r in self.results if r.passed),
            "failed": sum(1 for r in self.results if not r.passed),
            "results": [
                {
                    "endpoint": r.endpoint,
                    "method": r.method,
                    "user_role": r.user_role,
                    "expected_status": r.expected_status,
                    "actual_status": r.actual_status,
                    "passed": r.passed,
                    "error_message": r.error_message
                }
                for r in self.results
            ]
        }

        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(results_data, f, indent=2)

        print(f"Results saved to: {output_file}")


# Test user definitions based on deployment.yaml
TEST_USERS = {
    "admin": TestUser(
        username="admin",
        password=os.getenv("ADMIN_PASSWORD", "admin123"),
        role="admin",
        email="admin@test.edu",
        name="Admin User"
    ),
    "lecturer": TestUser(
        username="lecturer1",
        password=os.getenv("LECTURER_PASSWORD", "lecturer123"),
        role="lecturer",
        email="lecturer1@test.edu",
        name="Professor Smith"
    ),
    "tutor": TestUser(
        username="tutor1",
        password=os.getenv("TUTOR_PASSWORD", "tutor123"),
        role="tutor",
        email="tutor1@test.edu",
        name="Teaching Assistant One"
    ),
    "student": TestUser(
        username="student1",
        password=os.getenv("STUDENT_PASSWORD", "student123"),
        role="student",
        email="student1@test.edu",
        name="Alice Student"
    ),
}
