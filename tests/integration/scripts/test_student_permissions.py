#!/usr/bin/env python3
"""
Student Permission Tests

Tests that students can only:
- View their own submissions
- Submit assignments for courses they're enrolled in
- View course content they have access to
- NOT view other students' submissions
- NOT modify course content
- NOT access admin endpoints
"""

import asyncio
from pathlib import Path
from test_helpers import TEST_USERS, PermissionTestRunner


async def main():
    """Run student permission tests"""

    runner = PermissionTestRunner()
    student = TEST_USERS["student"]

    # Define test cases for student role
    test_cases = [
        # ====================================================================
        # ALLOWED: Students can view their own user profile
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/user",
            "expected_status": 200,
            "description": "View own user profile"
        },

        # ====================================================================
        # ALLOWED: Students can list organizations (read-only)
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/organizations",
            "expected_status": 200,
            "description": "List organizations"
        },

        # ====================================================================
        # DENIED: Students cannot create organizations
        # ====================================================================
        {
            "method": "POST",
            "endpoint": "/organizations",
            "json_data": {
                "slug": "student-org",
                "title": "Student Created Org",
                "description": "Should fail"
            },
            "expected_status": 403,
            "description": "Create organization (should fail)"
        },

        # ====================================================================
        # ALLOWED: Students can list courses they're enrolled in
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/courses",
            "expected_status": 200,
            "description": "List courses"
        },

        # ====================================================================
        # DENIED: Students cannot create courses
        # ====================================================================
        {
            "method": "POST",
            "endpoint": "/courses",
            "json_data": {
                "slug": "student-course",
                "title": "Student Created Course",
                "description": "Should fail",
                "course_family_id": "dummy-id"
            },
            "expected_status": 403,
            "description": "Create course (should fail)"
        },

        # ====================================================================
        # DENIED: Students cannot update courses
        # ====================================================================
        {
            "method": "PUT",
            "endpoint": "/courses/programming-101",
            "json_data": {
                "title": "Modified by Student"
            },
            "expected_status": 403,
            "description": "Update course (should fail)"
        },

        # ====================================================================
        # DENIED: Students cannot delete courses
        # ====================================================================
        {
            "method": "DELETE",
            "endpoint": "/courses/programming-101",
            "expected_status": 403,
            "description": "Delete course (should fail)"
        },

        # ====================================================================
        # ALLOWED: Students can view course content
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/course-contents",
            "params": {"course_id": "programming-101"},
            "expected_status": 200,
            "description": "List course contents"
        },

        # ====================================================================
        # DENIED: Students cannot create course content
        # ====================================================================
        {
            "method": "POST",
            "endpoint": "/course-contents",
            "json_data": {
                "title": "Student Created Content",
                "content_type": "lecture",
                "course_id": "programming-101"
            },
            "expected_status": 403,
            "description": "Create course content (should fail)"
        },

        # ====================================================================
        # ALLOWED: Students can view their own submissions
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/submissions",
            "params": {"user_id": "me"},
            "expected_status": 200,
            "description": "List own submissions"
        },

        # ====================================================================
        # DENIED: Students cannot view all submissions (without filtering)
        # This tests that students can't see other students' work
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/submissions",
            "expected_status": 403,
            "description": "List all submissions (should fail)"
        },

        # ====================================================================
        # ALLOWED: Students can create submissions for their courses
        # ====================================================================
        {
            "method": "POST",
            "endpoint": "/submissions",
            "json_data": {
                "assignment_id": "homework-1",
                "content": "My submission"
            },
            "expected_status": 201,
            "description": "Create submission"
        },

        # ====================================================================
        # DENIED: Students cannot access user management
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/users",
            "expected_status": 403,
            "description": "List all users (should fail)"
        },

        # ====================================================================
        # DENIED: Students cannot create users
        # ====================================================================
        {
            "method": "POST",
            "endpoint": "/users",
            "json_data": {
                "username": "newstudent",
                "email": "new@test.edu",
                "name": "New Student",
                "password": "pass123"
            },
            "expected_status": 403,
            "description": "Create user (should fail)"
        },

        # ====================================================================
        # DENIED: Students cannot modify other users
        # ====================================================================
        {
            "method": "PUT",
            "endpoint": "/users/student2",
            "json_data": {
                "name": "Modified Name"
            },
            "expected_status": 403,
            "description": "Update other user (should fail)"
        },

        # ====================================================================
        # DENIED: Students cannot access admin endpoints
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/admin/stats",
            "expected_status": 403,
            "description": "Access admin stats (should fail)"
        },

        # ====================================================================
        # DENIED: Students cannot manage course members
        # ====================================================================
        {
            "method": "POST",
            "endpoint": "/course-members",
            "json_data": {
                "course_id": "programming-101",
                "user_id": "student2",
                "role": "_student"
            },
            "expected_status": 403,
            "description": "Add course member (should fail)"
        },

        # ====================================================================
        # DENIED: Students cannot delete course members
        # ====================================================================
        {
            "method": "DELETE",
            "endpoint": "/course-members/programming-101/student2",
            "expected_status": 403,
            "description": "Remove course member (should fail)"
        },

        # ====================================================================
        # DENIED: Students cannot access execution backends
        # ====================================================================
        {
            "method": "POST",
            "endpoint": "/execution-backends",
            "json_data": {
                "slug": "student-backend",
                "type": "temporal:python"
            },
            "expected_status": 403,
            "description": "Create execution backend (should fail)"
        },
    ]

    # Run the tests
    passed, failed = await runner.run_test_suite(student, test_cases)

    # Print summary
    runner.print_summary()

    # Save results
    results_file = Path(__file__).parent.parent / "data" / "student_test_results.json"
    runner.save_results(results_file)

    # Exit with proper code
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
