"""Tests for team management endpoints."""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from computor_backend.model.course import (
    Course,
    CourseContent,
    CourseMember,
    CourseContentKind,
    SubmissionGroup,
    SubmissionGroupMember,
)
from computor_backend.model.auth import User
from computor_backend.business_logic.team_formation import get_team_formation_rules


class TestTeamManagement:
    """Test suite for team management endpoints."""

    def test_create_team_success(self, db: Session, test_client: TestClient):
        """Test creating a team successfully."""
        # Setup: Create course with team assignment
        course = Course(
            id=uuid4(),
            title="Test Course",
            properties={
                "team_formation": {
                    "mode": "self_organized",
                    "allow_student_group_creation": True,
                }
            }
        )
        db.add(course)

        # Create submittable kind
        kind = CourseContentKind(
            id="assignment",
            title="Assignment",
            submittable=True,
            has_ascendants=False,
            has_descendants=False,
        )
        db.add(kind)

        # Create team assignment
        course_content = CourseContent(
            id=uuid4(),
            title="Team Project",
            course_id=course.id,
            max_group_size=4,
            course_content_kind_id=kind.id,
            properties={}
        )
        db.add(course_content)

        # Create user and course member
        user = User(id=uuid4(), username="student1", email="student1@test.com")
        db.add(user)

        course_member = CourseMember(
            id=uuid4(),
            user_id=user.id,
            course_id=course.id,
            course_role_id="_student"
        )
        db.add(course_member)
        db.commit()

        # Test: Create team
        response = test_client.post(
            f"/course-contents/{course_content.id}/submission-groups/my-team",
            json={"team_name": "Awesome Team"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["max_group_size"] == 4
        assert data["status"] == "forming"
        assert data["created_by"] == "student"
        assert data["member_count"] == 1
        assert data["can_join"] is True
        assert "join_code" in data

    def test_create_team_not_team_assignment(self, db: Session, test_client: TestClient):
        """Test creating team for individual assignment fails."""
        # Setup: Individual assignment (max_group_size=1)
        course = Course(id=uuid4(), title="Test Course")
        db.add(course)

        kind = CourseContentKind(
            id="assignment",
            submittable=True,
            has_ascendants=False,
            has_descendants=False,
        )
        db.add(kind)

        course_content = CourseContent(
            id=uuid4(),
            course_id=course.id,
            max_group_size=1,  # Individual
            course_content_kind_id=kind.id,
        )
        db.add(course_content)

        user = User(id=uuid4(), username="student1")
        db.add(user)

        course_member = CourseMember(
            id=uuid4(),
            user_id=user.id,
            course_id=course.id,
            course_role_id="_student"
        )
        db.add(course_member)
        db.commit()

        # Test: Try to create team
        response = test_client.post(
            f"/course-contents/{course_content.id}/submission-groups/my-team",
            json={}
        )

        assert response.status_code == 400
        assert "not a team assignment" in response.json()["detail"]

    def test_get_my_team(self, db: Session, test_client: TestClient):
        """Test getting current user's team."""
        # Setup: Create team with user
        course = Course(id=uuid4(), title="Test Course")
        db.add(course)

        kind = CourseContentKind(id="assignment", submittable=True, has_ascendants=False, has_descendants=False)
        db.add(kind)

        course_content = CourseContent(
            id=uuid4(),
            course_id=course.id,
            max_group_size=3,
            course_content_kind_id=kind.id,
        )
        db.add(course_content)

        user = User(id=uuid4(), username="student1")
        db.add(user)

        course_member = CourseMember(
            id=uuid4(),
            user_id=user.id,
            course_id=course.id,
            course_role_id="_student"
        )
        db.add(course_member)

        # Create team
        team = SubmissionGroup(
            id=uuid4(),
            course_content_id=course_content.id,
            course_id=course.id,
            max_group_size=3,
            properties={"team_formation": {"status": "forming"}}
        )
        db.add(team)

        member = SubmissionGroupMember(
            submission_group_id=team.id,
            course_member_id=course_member.id,
            course_id=course.id
        )
        db.add(member)
        db.commit()

        # Test: Get my team
        response = test_client.get(
            f"/course-contents/{course_content.id}/submission-groups/my-team"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(team.id)
        assert data["member_count"] == 1

    def test_join_team(self, db: Session, test_client: TestClient):
        """Test joining an existing team."""
        # Setup
        course = Course(id=uuid4(), title="Test Course")
        db.add(course)

        kind = CourseContentKind(id="assignment", submittable=True, has_ascendants=False, has_descendants=False)
        db.add(kind)

        course_content = CourseContent(
            id=uuid4(),
            course_id=course.id,
            max_group_size=4,
            course_content_kind_id=kind.id,
            properties={"team_formation": {"allow_student_join_groups": True}}
        )
        db.add(course_content)

        # User 1 creates team
        user1 = User(id=uuid4(), username="student1")
        db.add(user1)
        member1 = CourseMember(id=uuid4(), user_id=user1.id, course_id=course.id, course_role_id="_student")
        db.add(member1)

        team = SubmissionGroup(
            id=uuid4(),
            course_content_id=course_content.id,
            course_id=course.id,
            max_group_size=4,
            properties={"team_formation": {"status": "forming", "join_code": "ABC123"}}
        )
        db.add(team)

        sgm1 = SubmissionGroupMember(
            submission_group_id=team.id,
            course_member_id=member1.id,
            course_id=course.id
        )
        db.add(sgm1)

        # User 2 wants to join
        user2 = User(id=uuid4(), username="student2")
        db.add(user2)
        member2 = CourseMember(id=uuid4(), user_id=user2.id, course_id=course.id, course_role_id="_student")
        db.add(member2)
        db.commit()

        # Test: User 2 joins team
        response = test_client.post(
            f"/submission-groups/{team.id}/join",
            json={}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "joined"
        assert "2/4" in data["message"]

    def test_leave_team(self, db: Session, test_client: TestClient):
        """Test leaving a team."""
        # Setup
        course = Course(id=uuid4(), title="Test Course")
        db.add(course)

        kind = CourseContentKind(id="assignment", submittable=True, has_ascendants=False, has_descendants=False)
        db.add(kind)

        course_content = CourseContent(
            id=uuid4(),
            course_id=course.id,
            max_group_size=3,
            course_content_kind_id=kind.id,
            properties={"team_formation": {"allow_student_leave_groups": True}}
        )
        db.add(course_content)

        user = User(id=uuid4(), username="student1")
        db.add(user)

        course_member = CourseMember(
            id=uuid4(),
            user_id=user.id,
            course_id=course.id,
            course_role_id="_student"
        )
        db.add(course_member)

        team = SubmissionGroup(
            id=uuid4(),
            course_content_id=course_content.id,
            course_id=course.id,
            max_group_size=3,
            properties={"team_formation": {"status": "forming"}}
        )
        db.add(team)

        member = SubmissionGroupMember(
            submission_group_id=team.id,
            course_member_id=course_member.id,
            course_id=course.id
        )
        db.add(member)
        db.commit()

        # Test: Leave team
        response = test_client.delete(
            f"/course-contents/{course_content.id}/submission-groups/my-team"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "deleted" in data["message"]  # Team deleted because last member left

    def test_get_team_formation_rules_inheritance(self, db: Session):
        """Test that team formation rules inherit from course to course_content."""
        from computor_backend.business_logic.team_formation import get_team_formation_rules

        # Setup: Course with defaults
        course = Course(
            id=uuid4(),
            title="Test Course",
            properties={
                "team_formation": {
                    "mode": "hybrid",
                    "max_group_size": 3,
                    "allow_student_group_creation": True,
                }
            }
        )
        db.add(course)

        kind = CourseContentKind(id="assignment", submittable=True, has_ascendants=False, has_descendants=False)
        db.add(kind)

        # Assignment overrides max_group_size
        course_content = CourseContent(
            id=uuid4(),
            course_id=course.id,
            max_group_size=5,
            course_content_kind_id=kind.id,
            properties={
                "team_formation": {
                    "max_group_size": 5,  # Override
                    "formation_deadline": "2025-12-01T23:59:59Z"  # Add new field
                }
            }
        )
        db.add(course_content)
        db.commit()

        # Test: Get resolved rules
        rules = get_team_formation_rules(course_content, course, db)

        assert rules["mode"] == "hybrid"  # Inherited from course
        assert rules["max_group_size"] == 5  # Overridden in course_content
        assert rules["allow_student_group_creation"] is True  # Inherited
        assert rules["formation_deadline"] == "2025-12-01T23:59:59Z"  # Added in course_content
