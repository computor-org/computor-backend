"""Tests for course member import functionality."""
import pytest
from uuid import uuid4
from sqlalchemy.orm import Session

from computor_backend.model.auth import User, StudentProfile
from computor_backend.model.course import Course, CourseFamily, CourseMember, CourseGroup
from computor_backend.model.organization import Organization
from computor_backend.business_logic.course_member_import import import_course_members
from computor_backend.permissions.principal import Principal
from computor_types.course_member_import import CourseMemberImportRow, ImportStatus


# Sample XML content for testing
SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<?mso-application progid="Excel.Sheet"?>
<ss:Workbook xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet" xmlns:wb="urn:schemas-microsoft-com:office:excel">
  <ss:Worksheet ss:Name="Members">
    <ss:Table>
      <ss:Row>
        <ss:Cell><ss:Data ss:Type="String">E-Mail</ss:Data></ss:Cell>
        <ss:Cell><ss:Data ss:Type="String">Vorname</ss:Data></ss:Cell>
        <ss:Cell><ss:Data ss:Type="String">Familienname</ss:Data></ss:Cell>
        <ss:Cell><ss:Data ss:Type="String">Matrikelnummer</ss:Data></ss:Cell>
        <ss:Cell><ss:Data ss:Type="String">Gruppe</ss:Data></ss:Cell>
      </ss:Row>
      <ss:Row>
        <ss:Cell><ss:Data ss:Type="String">john.doe@example.com</ss:Data></ss:Cell>
        <ss:Cell><ss:Data ss:Type="String">John</ss:Data></ss:Cell>
        <ss:Cell><ss:Data ss:Type="String">Doe</ss:Data></ss:Cell>
        <ss:Cell><ss:Data ss:Type="String">12345</ss:Data></ss:Cell>
        <ss:Cell><ss:Data ss:Type="String">Group A</ss:Data></ss:Cell>
      </ss:Row>
      <ss:Row>
        <ss:Cell><ss:Data ss:Type="String">jane.smith@example.com</ss:Data></ss:Cell>
        <ss:Cell><ss:Data ss:Type="String">Jane</ss:Data></ss:Cell>
        <ss:Cell><ss:Data ss:Type="String">Smith</ss:Data></ss:Cell>
        <ss:Cell><ss:Data ss:Type="String">67890</ss:Data></ss:Cell>
        <ss:Cell><ss:Data ss:Type="String">Group B</ss:Data></ss:Cell>
      </ss:Row>
    </ss:Table>
  </ss:Worksheet>
</ss:Workbook>"""


@pytest.fixture
def test_organization(db: Session) -> Organization:
    """Create a test organization."""
    org = Organization(
        id=uuid4(),
        title="Test Organization",
        path="test_org"
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@pytest.fixture
def test_course(db: Session, test_organization: Organization) -> Course:
    """Create a test course."""
    course_family = CourseFamily(
        id=uuid4(),
        title="Test Course Family",
        path="test_family",
        organization_id=test_organization.id
    )
    db.add(course_family)
    db.commit()

    course = Course(
        id=uuid4(),
        title="Test Course",
        path="test_course",
        course_family_id=course_family.id,
        organization_id=test_organization.id
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@pytest.fixture
def admin_principal() -> Principal:
    """Create an admin principal for testing."""
    principal = Principal(user_id=str(uuid4()))
    # Mock permission check
    principal.permitted = lambda resource, action: True
    return principal


def test_import_single_member(db: Session, test_course: Course, admin_principal: Principal):
    """Test importing a single course member."""
    members = [
        CourseMemberImportRow(
            email="test.user@example.com",
            given_name="Test",
            family_name="User",
            student_id="11111",
            course_role_id="_student"
        )
    ]

    result = import_course_members(
        course_id=test_course.id,
        members=members,
        default_course_role_id="_student",
        update_existing=False,
        create_missing_groups=True,
        organization_id=test_course.organization_id,
        permissions=admin_principal,
        db=db
    )

    assert result.total == 1
    assert result.success == 1
    assert result.errors == 0

    # Verify user was created
    user = db.query(User).filter(User.email == "test.user@example.com").first()
    assert user is not None
    assert user.given_name == "Test"
    assert user.family_name == "User"

    # Verify course member was created
    course_member = db.query(CourseMember).filter(
        CourseMember.user_id == user.id,
        CourseMember.course_id == test_course.id
    ).first()
    assert course_member is not None
    assert course_member.course_role_id == "_student"


def test_import_duplicate_member(db: Session, test_course: Course, admin_principal: Principal):
    """Test importing a member that already exists."""
    # Create existing user and course member
    user = User(
        id=uuid4(),
        email="existing@example.com",
        username="existing",
        given_name="Existing",
        family_name="User"
    )
    db.add(user)
    db.commit()

    course_member = CourseMember(
        id=uuid4(),
        user_id=user.id,
        course_id=test_course.id,
        course_role_id="_student"
    )
    db.add(course_member)
    db.commit()

    # Try to import the same user
    members = [
        CourseMemberImportRow(
            email="existing@example.com",
            given_name="Updated",
            family_name="Name",
            course_role_id="_student"
        )
    ]

    result = import_course_members(
        course_id=test_course.id,
        members=members,
        default_course_role_id="_student",
        update_existing=False,
        create_missing_groups=True,
        organization_id=test_course.organization_id,
        permissions=admin_principal,
        db=db
    )

    assert result.total == 1
    assert result.skipped == 1
    assert result.success == 0


def test_import_with_group_creation(db: Session, test_course: Course, admin_principal: Principal):
    """Test importing members with auto-group creation."""
    members = [
        CourseMemberImportRow(
            email="student1@example.com",
            given_name="Student",
            family_name="One",
            course_group_title="Auto Group",
            course_role_id="_student"
        )
    ]

    result = import_course_members(
        course_id=test_course.id,
        members=members,
        default_course_role_id="_student",
        update_existing=False,
        create_missing_groups=True,
        organization_id=test_course.organization_id,
        permissions=admin_principal,
        db=db
    )

    assert result.total == 1
    assert result.success == 1
    assert "Auto Group" in result.missing_groups

    # Verify group was created
    group = db.query(CourseGroup).filter(
        CourseGroup.course_id == test_course.id,
        CourseGroup.title == "Auto Group"
    ).first()
    assert group is not None

    # Verify member was assigned to group
    user = db.query(User).filter(User.email == "student1@example.com").first()
    course_member = db.query(CourseMember).filter(
        CourseMember.user_id == user.id,
        CourseMember.course_id == test_course.id
    ).first()
    assert course_member.course_group_id == group.id


def test_import_invalid_email(db: Session, test_course: Course, admin_principal: Principal):
    """Test importing with missing email."""
    members = [
        CourseMemberImportRow(
            email="",
            given_name="No",
            family_name="Email",
            course_role_id="_student"
        )
    ]

    result = import_course_members(
        course_id=test_course.id,
        members=members,
        default_course_role_id="_student",
        update_existing=False,
        create_missing_groups=True,
        organization_id=test_course.organization_id,
        permissions=admin_principal,
        db=db
    )

    assert result.total == 1
    assert result.errors == 1
    assert result.success == 0


def test_xml_parser():
    """Test XML parser with sample data."""
    from computor_backend.utils.excel_xml_parser import parse_course_member_xml

    parsed = parse_course_member_xml(SAMPLE_XML)

    assert len(parsed) == 2
    assert parsed[0]['email'] == 'john.doe@example.com'
    assert parsed[0]['given_name'] == 'John'
    assert parsed[0]['family_name'] == 'Doe'
    assert parsed[0]['student_id'] == '12345'
    assert parsed[0]['course_group_title'] == 'Group A'

    assert parsed[1]['email'] == 'jane.smith@example.com'
    assert parsed[1]['given_name'] == 'Jane'
