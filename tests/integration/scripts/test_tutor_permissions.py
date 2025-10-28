#!/usr/bin/env python3
"""
Tutor Permission Tests

Tests that tutors can:
- View and grade submissions for their courses
- View course content
- View student lists for their courses
- NOT modify course structure
- NOT manage course members
- NOT access admin endpoints
- Have more permissions than students but less than lecturers
"""

import asyncio
from pathlib import Path
from test_helpers import TEST_USERS, PermissionTestRunner


async def main():
    """Run tutor permission tests"""

    runner = PermissionTestRunner()
    tutor = TEST_USERS["tutor"]

    # Define test cases for tutor role
    test_cases = [
        # ====================================================================
        # ALLOWED: Tutors can view their own user profile
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/user",
            "expected_status": 200,
            "description": "View own user profile"
        },

        # ====================================================================
        # ALLOWED: Tutors can list organizations
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/organizations",
            "expected_status": 200,
            "description": "List organizations"
        },

        # ====================================================================
        # DENIED: Tutors cannot create organizations
        # ====================================================================
        {
            "method": "POST",
            "endpoint": "/organizations",
            "json_data": {
                "slug": "tutor-org",
                "title": "Tutor Created Org",
                "description": "Should fail"
            },
            "expected_status": 403,
            "description": "Create organization (should fail)"
        },

        # ====================================================================
        # ALLOWED: Tutors can list courses
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/courses",
            "expected_status": 200,
            "description": "List courses"
        },

        # ====================================================================
        # DENIED: Tutors cannot create courses
        # ====================================================================
        {
            "method": "POST",
            "endpoint": "/courses",
            "json_data": {
                "slug": "tutor-course",
                "title": "Tutor Created Course",
                "description": "Should fail",
                "course_family_id": "dummy-id"
            },
            "expected_status": 403,
            "description": "Create course (should fail)"
        },

        # ====================================================================
        # DENIED: Tutors cannot update course structure
        # ====================================================================
        {
            "method": "PUT",
            "endpoint": "/courses/programming-101",
            "json_data": {
                "title": "Modified by Tutor"
            },
            "expected_status": 403,
            "description": "Update course (should fail)"
        },

        # ====================================================================
        # DENIED: Tutors cannot delete courses
        # ====================================================================
        {
            "method": "DELETE",
            "endpoint": "/courses/programming-101",
            "expected_status": 403,
            "description": "Delete course (should fail)"
        },

        # ====================================================================
        # ALLOWED: Tutors can view course content
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/course-contents",
            "params": {"course_id": "programming-101"},
            "expected_status": 200,
            "description": "List course contents"
        },

        # ====================================================================
        # DENIED: Tutors cannot create course content
        # Only lecturers can modify course structure
        # ====================================================================
        {
            "method": "POST",
            "endpoint": "/course-contents",
            "json_data": {
                "title": "Tutor Created Content",
                "content_type": "lecture",
                "course_id": "programming-101"
            },
            "expected_status": 403,
            "description": "Create course content (should fail)"
        },

        # ====================================================================
        # ALLOWED: Tutors can view all submissions for their courses
        # This is a key difference from students
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/submissions",
            "params": {"course_id": "programming-101"},
            "expected_status": 200,
            "description": "List all course submissions"
        },

        # ====================================================================
        # ALLOWED: Tutors can view specific student submissions
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/submissions",
            "params": {"user_id": "student1", "course_id": "programming-101"},
            "expected_status": 200,
            "description": "View student submissions"
        },

        # ====================================================================
        # ALLOWED: Tutors can grade submissions
        # ====================================================================
        {
            "method": "POST",
            "endpoint": "/submissions/submission-123/grade",
            "json_data": {
                "score": 85,
                "feedback": "Good work!",
                "graded_by": "tutor1"
            },
            "expected_status": 200,
            "description": "Grade submission (may fail if submission doesn't exist, but should not be 403)"
        },

        # ====================================================================
        # ALLOWED: Tutors can view course members (students in their course)
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/course-members",
            "params": {"course_id": "programming-101"},
            "expected_status": 200,
            "description": "List course members"
        },

        # ====================================================================
        # DENIED: Tutors cannot add course members
        # Only lecturers can manage enrollment
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
        # DENIED: Tutors cannot remove course members
        # ====================================================================
        {
            "method": "DELETE",
            "endpoint": "/course-members/programming-101/student2",
            "expected_status": 403,
            "description": "Remove course member (should fail)"
        },

        # ====================================================================
        # DENIED: Tutors cannot list all users
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/users",
            "expected_status": 403,
            "description": "List all users (should fail)"
        },

        # ====================================================================
        # DENIED: Tutors cannot create users
        # ====================================================================
        {
            "method": "POST",
            "endpoint": "/users",
            "json_data": {
                "username": "newuser",
                "email": "new@test.edu",
                "name": "New User",
                "password": "pass123"
            },
            "expected_status": 403,
            "description": "Create user (should fail)"
        },

        # ====================================================================
        # DENIED: Tutors cannot modify other users
        # ====================================================================
        {
            "method": "PUT",
            "endpoint": "/users/student1",
            "json_data": {
                "name": "Modified Name"
            },
            "expected_status": 403,
            "description": "Update other user (should fail)"
        },

        # ====================================================================
        # DENIED: Tutors cannot access admin endpoints
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/admin/stats",
            "expected_status": 403,
            "description": "Access admin stats (should fail)"
        },

        # ====================================================================
        # DENIED: Tutors cannot manage execution backends
        # ====================================================================
        {
            "method": "POST",
            "endpoint": "/execution-backends",
            "json_data": {
                "slug": "tutor-backend",
                "type": "temporal:python"
            },
            "expected_status": 403,
            "description": "Create execution backend (should fail)"
        },

        # ====================================================================
        # ALLOWED: Tutors can download submission artifacts
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/submissions/submission-123/artifacts",
            "expected_status": 200,
            "description": "View submission artifacts (may 404 if not exists, but not 403)"
        },

        # ====================================================================
        # ALLOWED: Tutors can view submission results
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/submissions/submission-123/results",
            "expected_status": 200,
            "description": "View submission results (may 404 if not exists, but not 403)"
        },
    ]

    # Run the tests
    passed, failed = await runner.run_test_suite(tutor, test_cases)

    # Print summary
    runner.print_summary()

    # Save results
    results_file = Path(__file__).parent.parent / "data" / "tutor_test_results.json"
    runner.save_results(results_file)

    # Exit with proper code
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
