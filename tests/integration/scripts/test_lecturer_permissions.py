#!/usr/bin/env python3
"""
Lecturer Permission Tests

Tests that lecturers can:
- Full control over their courses
- Create and modify course content
- Manage course members (add/remove students and tutors)
- View and grade all submissions
- Configure course settings
- NOT access admin-only endpoints (system-wide operations)
- NOT create/delete organizations
- NOT manage users outside their courses
"""

import asyncio
from pathlib import Path
from test_helpers import TEST_USERS, PermissionTestRunner


async def main():
    """Run lecturer permission tests"""

    runner = PermissionTestRunner()
    lecturer = TEST_USERS["lecturer"]

    # Define test cases for lecturer role
    test_cases = [
        # ====================================================================
        # ALLOWED: Lecturers can view their own user profile
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/user",
            "expected_status": 200,
            "description": "View own user profile"
        },

        # ====================================================================
        # ALLOWED: Lecturers can list organizations
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/organizations",
            "expected_status": 200,
            "description": "List organizations"
        },

        # ====================================================================
        # DENIED: Lecturers cannot create organizations (admin only)
        # ====================================================================
        {
            "method": "POST",
            "endpoint": "/organizations",
            "json_data": {
                "slug": "lecturer-org",
                "title": "Lecturer Created Org",
                "description": "Should fail"
            },
            "expected_status": 403,
            "description": "Create organization (should fail)"
        },

        # ====================================================================
        # ALLOWED: Lecturers can list courses
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/courses",
            "expected_status": 200,
            "description": "List courses"
        },

        # ====================================================================
        # ALLOWED: Lecturers can view specific course details
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/courses/programming-101",
            "expected_status": 200,
            "description": "View course details"
        },

        # ====================================================================
        # ALLOWED: Lecturers can update their own courses
        # ====================================================================
        {
            "method": "PUT",
            "endpoint": "/courses/programming-101",
            "json_data": {
                "title": "Programming 101 - Updated",
                "description": "Updated by lecturer"
            },
            "expected_status": 200,
            "description": "Update own course"
        },

        # ====================================================================
        # ALLOWED: Lecturers can view and modify course content
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/course-contents",
            "params": {"course_id": "programming-101"},
            "expected_status": 200,
            "description": "List course contents"
        },

        # ====================================================================
        # ALLOWED: Lecturers can create course content
        # ====================================================================
        {
            "method": "POST",
            "endpoint": "/course-contents",
            "json_data": {
                "title": "Week 1 Lecture",
                "content_type": "lecture",
                "course_id": "programming-101",
                "description": "Introduction to programming"
            },
            "expected_status": 201,
            "description": "Create course content"
        },

        # ====================================================================
        # ALLOWED: Lecturers can update course content
        # ====================================================================
        {
            "method": "PUT",
            "endpoint": "/course-contents/content-123",
            "json_data": {
                "title": "Week 1 Lecture - Updated"
            },
            "expected_status": 200,
            "description": "Update course content (may 404 if not exists)"
        },

        # ====================================================================
        # ALLOWED: Lecturers can delete course content
        # ====================================================================
        {
            "method": "DELETE",
            "endpoint": "/course-contents/content-123",
            "expected_status": 200,
            "description": "Delete course content (may 404 if not exists)"
        },

        # ====================================================================
        # ALLOWED: Lecturers can view all submissions for their courses
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/submissions",
            "params": {"course_id": "programming-101"},
            "expected_status": 200,
            "description": "List all course submissions"
        },

        # ====================================================================
        # ALLOWED: Lecturers can view specific student submissions
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/submissions",
            "params": {"user_id": "student1", "course_id": "programming-101"},
            "expected_status": 200,
            "description": "View student submissions"
        },

        # ====================================================================
        # ALLOWED: Lecturers can grade submissions
        # ====================================================================
        {
            "method": "POST",
            "endpoint": "/submissions/submission-123/grade",
            "json_data": {
                "score": 95,
                "feedback": "Excellent work!",
                "graded_by": "lecturer1"
            },
            "expected_status": 200,
            "description": "Grade submission (may 404 if not exists)"
        },

        # ====================================================================
        # ALLOWED: Lecturers can view course members
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/course-members",
            "params": {"course_id": "programming-101"},
            "expected_status": 200,
            "description": "List course members"
        },

        # ====================================================================
        # ALLOWED: Lecturers can add course members
        # ====================================================================
        {
            "method": "POST",
            "endpoint": "/course-members",
            "json_data": {
                "course_id": "programming-101",
                "user_id": "student3",
                "role": "_student"
            },
            "expected_status": 201,
            "description": "Add course member"
        },

        # ====================================================================
        # ALLOWED: Lecturers can update course member roles
        # ====================================================================
        {
            "method": "PUT",
            "endpoint": "/course-members/programming-101/student3",
            "json_data": {
                "role": "_tutor"
            },
            "expected_status": 200,
            "description": "Update course member role"
        },

        # ====================================================================
        # ALLOWED: Lecturers can remove course members
        # ====================================================================
        {
            "method": "DELETE",
            "endpoint": "/course-members/programming-101/student3",
            "expected_status": 200,
            "description": "Remove course member"
        },

        # ====================================================================
        # ALLOWED: Lecturers can view submission artifacts
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/submissions/submission-123/artifacts",
            "expected_status": 200,
            "description": "View submission artifacts (may 404 if not exists)"
        },

        # ====================================================================
        # ALLOWED: Lecturers can view submission results
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/submissions/submission-123/results",
            "expected_status": 200,
            "description": "View submission results (may 404 if not exists)"
        },

        # ====================================================================
        # ALLOWED: Lecturers can trigger submission re-evaluation
        # ====================================================================
        {
            "method": "POST",
            "endpoint": "/submissions/submission-123/rerun",
            "expected_status": 200,
            "description": "Re-run submission tests (may 404 if not exists)"
        },

        # ====================================================================
        # DENIED: Lecturers cannot list all users (admin only)
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/users",
            "expected_status": 403,
            "description": "List all users (should fail)"
        },

        # ====================================================================
        # DENIED: Lecturers cannot create users (admin only)
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
        # DENIED: Lecturers cannot modify users outside their courses
        # ====================================================================
        {
            "method": "PUT",
            "endpoint": "/users/admin",
            "json_data": {
                "name": "Modified Admin"
            },
            "expected_status": 403,
            "description": "Update other user (should fail)"
        },

        # ====================================================================
        # DENIED: Lecturers cannot delete users
        # ====================================================================
        {
            "method": "DELETE",
            "endpoint": "/users/student1",
            "expected_status": 403,
            "description": "Delete user (should fail)"
        },

        # ====================================================================
        # DENIED: Lecturers cannot access admin endpoints
        # ====================================================================
        {
            "method": "GET",
            "endpoint": "/admin/stats",
            "expected_status": 403,
            "description": "Access admin stats (should fail)"
        },

        # ====================================================================
        # DENIED: Lecturers cannot create execution backends (admin only)
        # ====================================================================
        {
            "method": "POST",
            "endpoint": "/execution-backends",
            "json_data": {
                "slug": "lecturer-backend",
                "type": "temporal:python"
            },
            "expected_status": 403,
            "description": "Create execution backend (should fail)"
        },

        # ====================================================================
        # DENIED: Lecturers cannot delete organizations
        # ====================================================================
        {
            "method": "DELETE",
            "endpoint": "/organizations/test-university",
            "expected_status": 403,
            "description": "Delete organization (should fail)"
        },

        # ====================================================================
        # DENIED: Lecturers cannot delete course families
        # ====================================================================
        {
            "method": "DELETE",
            "endpoint": "/course-families/computer-science",
            "expected_status": 403,
            "description": "Delete course family (should fail)"
        },
    ]

    # Run the tests
    passed, failed = await runner.run_test_suite(lecturer, test_cases)

    # Print summary
    runner.print_summary()

    # Save results
    results_file = Path(__file__).parent.parent / "data" / "lecturer_test_results.json"
    runner.save_results(results_file)

    # Exit with proper code
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
