#!/usr/bin/env python3
"""
Fake data seeder for the ComputingTutor database.
Generates realistic test data for development and testing.
"""

import os
import sys
import random
import argparse
from datetime import datetime, timedelta
from uuid import uuid4
from pathlib import Path
from dotenv import load_dotenv

# Add parent directories to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # computor_backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))  # src

# Load environment variables
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)

from database import get_db
from model.auth import User, Account, StudentProfile
from model.organization import Organization
from model.course import Course, CourseFamily, CourseGroup, CourseMember, CourseRole, CourseContent, CourseContentType, CourseContentKind, SubmissionGroup, SubmissionGroupMember
from model.role import Role, UserRole
from model.artifact import SubmissionArtifact
from model.message import Message
from custom_types import Ltree
from sqlalchemy.orm import Session
import requests
import time

# Fake data generators
from faker import Faker
fake = Faker()

# Import Temporal client for GitLab operations
try:
    from tasks.temporal_client import get_temporal_client
except ImportError:
    print("⚠️  Temporal client not available - GitLab operations will be skipped")
    get_temporal_client = None

# Course content kinds and roles are created by system initialization
# No need to recreate them here

def create_users(session, count=50):
    """Create fake users."""
    users = []

    for i in range(count):
        user = User(
            given_name=fake.first_name(),
            family_name=fake.last_name(),
            email=fake.unique.email(),
            username=fake.unique.user_name(),
        )
        session.add(user)
        users.append(user)

    session.flush()  # Get IDs
    print(f"✅ Created {count} users")
    return users

def create_organizations(session, users):
    """Create organizations with GitLab integration."""
    organizations = []
    
    # GitLab configuration from environment
    gitlab_url = os.environ.get('TEST_GITLAB_URL', 'http://localhost:8084')
    gitlab_token = os.environ.get('TEST_GITLAB_TOKEN')
    gitlab_parent_id = os.environ.get('TEST_GITLAB_GROUP_ID')
    
    if not gitlab_token:
        print("⚠️  TEST_GITLAB_TOKEN not set - GitLab integration will be skipped")
    
    # Check if main university already exists
    existing_main = session.query(Organization).filter(Organization.path == Ltree('university')).first()
    if existing_main:
        print("ℹ️  University organization already exists, using existing one")
        organizations.append(existing_main)
    else:
        # Create a main university organization with GitLab integration
        properties = {
            'gitlab': {
                'url': gitlab_url,
                'token': gitlab_token,
                'parent': int(gitlab_parent_id) if gitlab_parent_id else None
            }
        } if gitlab_token else {}
        
        main_org = Organization(
            title="Example University",
            description="A leading institution for computing education",
            organization_type='organization',
            path=Ltree('university'),
            email='admin@university.edu',
            telephone='+1-555-123-4567',
            url='https://university.edu',
            locality='Example City',
            region='Example State',
            country='Example Country',
            properties=properties,
            created_by=random.choice(users).id
        )
        session.add(main_org)
        session.flush()
        organizations.append(main_org)
        
        # Create GitLab group via Temporal if configured
        if gitlab_token and get_temporal_client:
            try:
                print("🔄 Creating GitLab group for university organization...")
                temporal_client = get_temporal_client()
                result = temporal_client.execute_workflow(
                    'create_organization',
                    {
                        'organization_id': str(main_org.id),
                        'organization_name': main_org.title,
                        'organization_path': str(main_org.path),
                        'gitlab_config': properties['gitlab']
                    },
                    id=f"create_org_{main_org.id}",
                    task_queue='computor-tasks'
                )
                print(f"✅ GitLab organization creation task started: {result.id}")
            except Exception as e:
                print(f"⚠️  GitLab organization creation failed: {e}")
        
        print("✅ Created main university organization")
    
    # Create departments if they don't exist
    departments = ['Computer Science', 'Information Systems', 'Software Engineering']
    for dept_name in departments:
        dept_path = Ltree(f"university.{dept_name.lower().replace(' ', '_')}")
        existing_dept = session.query(Organization).filter(Organization.path == dept_path).first()
        
        if existing_dept:
            print(f"ℹ️  Department '{dept_name}' already exists")
            organizations.append(existing_dept)
        else:
            dept = Organization(
                title=f"Department of {dept_name}",
                description=f"The {dept_name} department",
                organization_type='organization',
                path=dept_path,
                email=f'{dept_name.lower().replace(" ", ".")}@university.edu',
                created_by=random.choice(users).id
            )
            session.add(dept)
            session.flush()
            organizations.append(dept)
            print(f"✅ Created department: {dept_name}")
    
    print(f"✅ Using {len(organizations)} organizations")
    return organizations

def create_execution_backends(session, users):
    """
    DEPRECATED: ExecutionBackend model has been replaced by ServiceType.
    This function is kept for backward compatibility but does nothing.
    To create testing services, use ServiceType and Service models instead.
    """
    print("ℹ️  ExecutionBackend creation skipped (deprecated - use ServiceType instead)")
    return []

def create_course_families(session, organizations, users):
    """Create course families."""
    course_families = []
    
    cs_org = next(org for org in organizations if 'Computer Science' in org.title)
    
    families_data = [
        {'title': 'Programming Fundamentals', 'path': 'cs.programming'},
        {'title': 'Data Structures & Algorithms', 'path': 'cs.algorithms'},
        {'title': 'Software Engineering', 'path': 'cs.software_eng'},
        {'title': 'Machine Learning', 'path': 'cs.ml'}
    ]
    
    for family_data in families_data:
        family = CourseFamily(
            title=family_data['title'],
            description=f"Course family for {family_data['title']}",
            path=Ltree(family_data['path']),
            organization_id=cs_org.id,
            created_by=random.choice(users).id
        )
        session.add(family)
        course_families.append(family)
    
    session.flush()
    print(f"✅ Created {len(course_families)} course families")
    return course_families

def create_courses(session, course_families, organizations, users, execution_backends):
    """Create courses."""
    courses = []
    
    cs_org = next(org for org in organizations if 'Computer Science' in org.title)
    
    for family in course_families:
        # Create 2-3 courses per family
        for i in range(random.randint(2, 3)):
            year = random.choice(['2023', '2024', '2025'])
            semester = random.choice(['fall', 'spring', 'summer'])
            # Add random suffix to make paths unique
            random_suffix = random.randint(1000, 9999)
            
            course = Course(
                title=f"{family.title} {year}",
                description=f"{family.title} course for {semester} {year}",
                path=Ltree(f"{family.path}.{year}_{semester}_{random_suffix}"),
                course_family_id=family.id,
                organization_id=cs_org.id,
                version_identifier=f"v{year}.{i+1}",
                created_by=random.choice(users).id
            )
            session.add(course)
            session.flush()  # Flush to get course ID
            courses.append(course)

            # NOTE: Execution backend assignment removed - use ServiceType/Service instead

    session.flush()
    print(f"✅ Created {len(courses)} courses")
    return courses

def create_course_groups(session, courses, users):
    """Create course groups."""
    course_groups = []
    
    for course in courses:
        # Create 3-5 groups per course
        for i in range(random.randint(3, 5)):
            group = CourseGroup(
                title=f"Group {i+1}",
                description=f"Study group {i+1} for {course.title}",
                course_id=course.id,
                created_by=random.choice(users).id
            )
            session.add(group)
            course_groups.append(group)
    
    session.flush()
    print(f"✅ Created {len(course_groups)} course groups")
    return course_groups

def create_course_members(session, courses, course_groups, users):
    """Create course members and assign them to groups."""
    course_members = []
    
    # Get course roles
    student_role = session.query(CourseRole).filter(CourseRole.id == '_student').first()
    tutor_role = session.query(CourseRole).filter(CourseRole.id == '_tutor').first()
    lecturer_role = session.query(CourseRole).filter(CourseRole.id == '_lecturer').first()
    
    if not all([student_role, tutor_role, lecturer_role]):
        print("❌ Missing course roles! Run system initialization first.")
        return course_members
    
    for course in courses:
        course_course_groups = [g for g in course_groups if g.course_id == course.id]
        used_users = set()  # Track users already in this course
        
        # Add 1 lecturer per course
        lecturer_user = random.choice(users)
        used_users.add(lecturer_user.id)
        lecturer = CourseMember(
            user_id=lecturer_user.id,
            course_id=course.id,
            course_group_id=random.choice(course_course_groups).id if course_course_groups else None,
            course_role_id=lecturer_role.id,
            created_by=random.choice(users).id
        )
        session.add(lecturer)
        course_members.append(lecturer)
        
        # Add 1-2 tutors per course
        for _ in range(random.randint(1, 2)):
            available_users = [u for u in users if u.id not in used_users]
            if not available_users:
                break
            tutor_user = random.choice(available_users)
            used_users.add(tutor_user.id)
            tutor = CourseMember(
                user_id=tutor_user.id,
                course_id=course.id,
                course_group_id=random.choice(course_course_groups).id if course_course_groups else None,
                course_role_id=tutor_role.id,
                created_by=random.choice(users).id
            )
            session.add(tutor)
            course_members.append(tutor)
        
        # Add students per course (up to available users)
        max_students = min(15, len(users) - len(used_users))
        num_students = random.randint(5, max_students) if max_students >= 5 else max_students
        
        for _ in range(num_students):
            available_users = [u for u in users if u.id not in used_users]
            if not available_users:
                break
            student_user = random.choice(available_users)
            used_users.add(student_user.id)
            student = CourseMember(
                user_id=student_user.id,
                course_id=course.id,
                course_group_id=random.choice(course_course_groups).id if course_course_groups else None,
                course_role_id=student_role.id,
                created_by=random.choice(users).id
            )
            session.add(student)
            course_members.append(student)
    
    session.flush()
    print(f"✅ Created {len(course_members)} course members")
    return course_members

def create_course_content_types(session, courses, users):
    """Create course content types for each course."""
    course_content_types = []
    
    # Get required CourseContentKinds
    unit_kind = session.query(CourseContentKind).filter(CourseContentKind.id == 'unit').first()
    assignment_kind = session.query(CourseContentKind).filter(CourseContentKind.id == 'assignment').first()
    
    if not all([unit_kind, assignment_kind]):
        print("❌ Missing CourseContentKind entries! Run migration first.")
        return course_content_types
    
    for course in courses:
        # Create 'weekly' content type for units
        weekly_type = CourseContentType(
            title="Weekly Unit",
            description="Weekly organizational unit",
            slug="weekly",
            color="#4CAF50",  # Green
            course_content_kind_id=unit_kind.id,
            course_id=course.id,
            created_by=random.choice(users).id
        )
        session.add(weekly_type)
        course_content_types.append(weekly_type)
        
        # Create 'mandatory' content type for assignments
        mandatory_type = CourseContentType(
            title="Mandatory Assignment",
            description="Mandatory programming assignment",
            slug="mandatory",
            color="#2196F3",  # Blue
            course_content_kind_id=assignment_kind.id,
            course_id=course.id,
            created_by=random.choice(users).id
        )
        session.add(mandatory_type)
        course_content_types.append(mandatory_type)
    
    session.flush()
    print(f"✅ Created {len(course_content_types)} course content types")
    return course_content_types

def create_course_contents(session, courses, course_content_types, users):
    """Create hierarchical course content with units and assignments."""
    course_contents = []
    
    for course in courses:
        # Get content types for this course
        weekly_type = next((ct for ct in course_content_types 
                           if ct.course_id == course.id and ct.slug == 'weekly'), None)
        mandatory_type = next((ct for ct in course_content_types 
                              if ct.course_id == course.id and ct.slug == 'mandatory'), None)
        
        if not all([weekly_type, mandatory_type]):
            print(f"❌ Missing content types for course {course.title}")
            continue
        
        # Create 4-6 weekly units
        num_weeks = random.randint(4, 6)
        for week_num in range(1, num_weeks + 1):
            # Create unit (parent)
            unit_title = f"Week {week_num}"
            unit_path = Ltree(f"week_{week_num}")
            
            unit = CourseContent(
                title=unit_title,
                description=f"Learning unit for week {week_num}",
                path=unit_path,
                course_id=course.id,
                course_content_type_id=weekly_type.id,
                version_identifier=f"week_{week_num}_v1",
                position=float(week_num * 10),  # 10, 20, 30, etc.
                max_group_size=1,
                # Units don't have examples (example_id=None)
                created_by=random.choice(users).id
            )
            session.add(unit)
            course_contents.append(unit)
            
            # Create 2-6 assignments under this unit
            num_assignments = random.randint(2, 6)
            for assignment_num in range(1, num_assignments + 1):
                assignment_topics = [
                    "Hello World", "Variables", "Functions", "Loops", "Arrays", 
                    "Classes", "File I/O", "Exceptions", "Algorithms", "Data Structures"
                ]
                topic = random.choice(assignment_topics)
                
                assignment_title = f"{topic} Assignment"
                # Path: week_1.assignment_1, week_1.assignment_2, etc.
                assignment_path = Ltree(f"week_{week_num}.assignment_{assignment_num}")
                
                assignment = CourseContent(
                    title=assignment_title,
                    description=f"Programming assignment on {topic.lower()}",
                    path=assignment_path,
                    course_id=course.id,
                    course_content_type_id=mandatory_type.id,
                    version_identifier=f"week_{week_num}_assignment_{assignment_num}_v1",
                    position=float(assignment_num * 10),  # 10, 20, 30, etc. within the week
                    max_group_size=random.randint(1, 3),
                    max_test_runs=random.randint(5, 20),
                    max_submissions=random.randint(10, 50),
                    # Assignments could have examples, but we'll leave them NULL for now
                    # since we don't have actual examples yet
                    # example_id=None,
                    # example_version=None,
                    created_by=random.choice(users).id
                )
                session.add(assignment)
                course_contents.append(assignment)
    
    session.flush()
    print(f"✅ Created {len(course_contents)} course contents")
    return course_contents


def create_submission_groups(session, courses, course_contents, course_members):
    """Create submission groups for assignments (course content with 'assignment' in path)."""
    submission_groups = []

    for course in courses:
        # Get assignments (course content) for this course
        course_assignments = [cc for cc in course_contents
                            if cc.course_id == course.id and '.' in str(cc.path)]  # assignments have dot in path

        # Get student members for this course
        student_role = session.query(CourseRole).filter(CourseRole.id == '_student').first()
        course_student_members = [cm for cm in course_members
                                  if cm.course_id == course.id and cm.course_role_id == student_role.id]

        if not course_student_members:
            continue

        # Create submission groups for each assignment with random students
        for assignment in course_assignments:
            # Randomly select some students (30-70% of students) to have submission groups
            selected_students = random.sample(
                course_student_members,
                k=random.randint(
                    max(1, len(course_student_members) // 3),
                    max(1, len(course_student_members) * 2 // 3)
                )
            )

            for student_member in selected_students:
                # Create submission group
                submission_group = SubmissionGroup(
                    display_name=None,  # Will be computed from member name
                    max_group_size=assignment.max_group_size or 1,
                    max_test_runs=assignment.max_test_runs,
                    max_submissions=assignment.max_submissions,
                    course_id=course.id,
                    course_content_id=assignment.id,
                    created_by=student_member.user_id
                )
                session.add(submission_group)
                session.flush()  # Get the submission group ID

                # Create submission group member
                submission_group_member = SubmissionGroupMember(
                    course_id=course.id,
                    submission_group_id=submission_group.id,
                    course_member_id=student_member.id,
                    created_by=student_member.user_id
                )
                session.add(submission_group_member)
                submission_groups.append(submission_group)

    session.flush()
    print(f"✅ Created {len(submission_groups)} submission groups")
    return submission_groups


def create_submission_artifacts(session, submission_groups, course_members):
    """Create submission artifacts with submit=True for some submission groups."""
    submission_artifacts = []

    for submission_group in submission_groups:
        # Randomly decide if this group has a submission (60% chance)
        if random.random() < 0.6:
            # Get the uploader (first member of the group)
            group_member = session.query(SubmissionGroupMember).filter(
                SubmissionGroupMember.submission_group_id == submission_group.id
            ).first()

            if not group_member:
                continue

            # Create a submission artifact with submit=True
            artifact = SubmissionArtifact(
                submission_group_id=submission_group.id,
                uploaded_by_course_member_id=group_member.course_member_id,
                content_type='application/zip',
                file_size=random.randint(1000, 100000),  # Random file size
                bucket_name='submissions',
                object_key=f'{submission_group.id}/v1/submission.zip',
                version_identifier='v1',
                submit=True,  # This is an official submission
                properties={
                    'original_filename': 'submission.zip',
                    'seeded': True
                }
            )
            session.add(artifact)
            submission_artifacts.append(artifact)

    session.flush()
    print(f"✅ Created {len(submission_artifacts)} submission artifacts (with submit=True)")
    return submission_artifacts


def create_messages_for_submissions(session, submission_artifacts, submission_groups):
    """Create help request messages for submission artifacts with submit=True."""
    messages = []

    help_requests = [
        "I'm stuck on this assignment. Can you help me understand the requirements?",
        "My code compiles but I'm getting wrong results. Please help me debug!",
        "I don't understand why my tests are failing. Could someone explain?",
        "Need help with the algorithm implementation. What approach should I use?",
        "Getting a runtime error that I can't figure out. Please assist!",
        "The instructions are unclear to me. Can you clarify what's expected?",
        "My solution works locally but fails the tests. What am I missing?",
        "I'm having trouble with edge cases. Any hints would be appreciated!",
    ]

    for artifact in submission_artifacts:
        # Randomly decide if this submission has a help message (40% chance)
        if random.random() < 0.4:
            # Get the submission group
            submission_group = next(
                (sg for sg in submission_groups if sg.id == artifact.submission_group_id),
                None
            )

            if not submission_group:
                continue

            # Get the uploader's course member to find the author
            group_member = session.query(SubmissionGroupMember).filter(
                SubmissionGroupMember.submission_group_id == submission_group.id
            ).first()

            if not group_member or not group_member.course_member:
                continue

            author_id = group_member.course_member.user_id

            # Create a help request message
            message = Message(
                author_id=author_id,
                parent_id=None,
                level=0,  # Top-level message
                title="#ai::help",
                content=random.choice(help_requests),
                # Target the message to the submission group
                submission_group_id=submission_group.id,
                course_id=submission_group.course_id,
                course_content_id=submission_group.course_content_id,
                created_by=author_id
            )
            session.add(message)
            messages.append(message)

    session.flush()
    print(f"✅ Created {len(messages)} messages with subject '#ai::help'")
    return messages


def clear_fake_data(session):
    """Clear existing fake data (but keep system data)."""
    print("🧹 Clearing existing fake data...")

    # Delete in reverse dependency order
    # First delete messages (they reference submission groups)
    session.query(Message).delete(synchronize_session=False)
    # Delete submission artifacts (they reference submission groups)
    session.query(SubmissionArtifact).delete(synchronize_session=False)
    # Delete submission group members (they reference submission groups and course members)
    session.query(SubmissionGroupMember).delete(synchronize_session=False)
    # Delete submission groups (they reference course content)
    session.query(SubmissionGroup).delete(synchronize_session=False)

    session.query(CourseMember).delete(synchronize_session=False)
    # NOTE: CourseExecutionBackend table removed - use CourseService instead
    session.query(CourseGroup).delete(synchronize_session=False)
    session.query(Course).delete(synchronize_session=False)
    session.query(CourseFamily).delete(synchronize_session=False)

    # NOTE: ExecutionBackend table removed - use ServiceType/Service instead

    # Delete all organizations - we'll recreate them
    session.query(Organization).delete(synchronize_session=False)

    # Delete users except admin
    admin_username = os.environ.get('API_ADMIN_USER', 'admin')
    session.query(User).filter(User.username != admin_username).delete(synchronize_session=False)

    session.commit()
    print("✅ Cleared existing fake data")

def main():
    """Main seeder function."""
    parser = argparse.ArgumentParser(description='Seed the database with fake data')
    parser.add_argument('--clear', action='store_true', help='Clear existing fake data first')
    parser.add_argument('--count', type=int, default=50, help='Number of users to create')
    args = parser.parse_args()
    
    with next(get_db()) as session:
        try:
            if args.clear:
                clear_fake_data(session)
            
            print("🌱 Starting fake data seeding...")
            print("ℹ️  Note: System roles and content kinds should already exist from system initialization")
            
            # Create users and organizations
            users = create_users(session, args.count)
            organizations = create_organizations(session, users)
            execution_backends = create_execution_backends(session, users)
            session.commit()
            
            # Create course structure
            course_families = create_course_families(session, organizations, users)
            courses = create_courses(session, course_families, organizations, users, execution_backends)
            course_groups = create_course_groups(session, courses, users)
            course_members = create_course_members(session, courses, course_groups, users)
            
            # Create course content hierarchy
            course_content_types = create_course_content_types(session, courses, users)
            course_contents = create_course_contents(session, courses, course_content_types, users)

            # Create submission groups, artifacts, and messages
            submission_groups = create_submission_groups(session, courses, course_contents, course_members)
            submission_artifacts = create_submission_artifacts(session, submission_groups, course_members)
            messages = create_messages_for_submissions(session, submission_artifacts, submission_groups)

            session.commit()

            print("🎉 Fake data seeding completed successfully!")
            print(f"Created:")
            print(f"  - {len(users)} users")
            print(f"  - {len(organizations)} organizations")
            print(f"  - {len(course_families)} course families")
            print(f"  - {len(courses)} courses")
            print(f"  - {len(course_groups)} course groups")
            print(f"  - {len(course_members)} course members")
            print(f"  - {len(course_content_types)} course content types (weekly, mandatory)")
            print(f"  - {len(course_contents)} course contents (units with assignments)")
            print(f"  - {len(submission_groups)} submission groups")
            print(f"  - {len(submission_artifacts)} submission artifacts (with submit=True)")
            print(f"  - {len(messages)} messages with subject '#ai::help'")
            
            # Show some example structure
            if course_contents:
                print("\n📋 Sample course content structure:")
                sample_course = courses[0] if courses else None
                if sample_course:
                    sample_contents = [cc for cc in course_contents if cc.course_id == sample_course.id][:10]  # First 10
                    for content in sample_contents:
                        indent = "  " * (len(str(content.path).split('.')))
                        content_type = "📁" if "week_" in str(content.path) and "." not in str(content.path) else "📝"
                        print(f"    {indent}{content_type} {content.path} - {content.title}")
            
            # Show GitLab integration status
            gitlab_token = os.environ.get('TEST_GITLAB_TOKEN')
            if gitlab_token and get_temporal_client:
                print("\n🦊 GitLab Integration:")
                print(f"  - GitLab URL: {os.environ.get('TEST_GITLAB_URL', 'http://localhost:8084')}")
                print(f"  - Parent Group ID: {os.environ.get('TEST_GITLAB_GROUP_ID', 'not set')}")
                print(f"  - Temporal tasks created for organization, course families, and courses")
                print(f"  - Check Temporal UI at http://localhost:8088 to monitor GitLab creation progress")
            else:
                print("\n⚠️  GitLab Integration: Disabled (missing TEST_GITLAB_TOKEN or Temporal client)")
            
        except Exception as e:
            print(f"❌ Error seeding data: {e}")
            session.rollback()
            raise

if __name__ == '__main__':
    main()