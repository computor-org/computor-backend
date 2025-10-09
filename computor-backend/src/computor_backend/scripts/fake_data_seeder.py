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
from model.course import Course, CourseFamily, CourseGroup, CourseMember, CourseRole, CourseExecutionBackend, CourseContent, CourseContentType, CourseContentKind
from model.execution import ExecutionBackend
from model.role import Role, UserRole
from ..custom_types import Ltree
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
            user_type='user',
            fs_number=1000 + i
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
    """Create execution backends."""
    backends_data = [
        {'type': 'python', 'slug': 'python-3-11'},
        {'type': 'java', 'slug': 'java-17'},
        {'type': 'cpp', 'slug': 'gcc-11'},
        {'type': 'matlab', 'slug': 'matlab-2023a'}
    ]
    
    execution_backends = []
    for backend_data in backends_data:
        # Check if backend already exists
        existing_backend = session.query(ExecutionBackend).filter(
            ExecutionBackend.slug == backend_data['slug']
        ).first()
        
        if existing_backend:
            print(f"ℹ️  Execution backend '{backend_data['slug']}' already exists")
            execution_backends.append(existing_backend)
        else:
            backend = ExecutionBackend(
                type=backend_data['type'],
                slug=backend_data['slug'],
                created_by=random.choice(users).id
            )
            session.add(backend)
            session.flush()
            execution_backends.append(backend)
            print(f"✅ Created execution backend: {backend_data['slug']}")
    
    print(f"✅ Using {len(execution_backends)} execution backends")
    return execution_backends

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
            
            # Add execution backends to course
            for backend in random.sample(execution_backends, random.randint(1, 2)):
                course_backend = CourseExecutionBackend(
                    course_id=course.id,
                    execution_backend_id=backend.id
                )
                session.add(course_backend)
    
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

def clear_fake_data(session):
    """Clear existing fake data (but keep system data)."""
    print("🧹 Clearing existing fake data...")
    
    # Delete in reverse dependency order
    session.query(CourseMember).delete(synchronize_session=False)
    session.query(CourseExecutionBackend).delete(synchronize_session=False)
    session.query(CourseGroup).delete(synchronize_session=False)
    session.query(Course).delete(synchronize_session=False)
    session.query(CourseFamily).delete(synchronize_session=False)
    
    # Delete execution backends except system ones
    session.query(ExecutionBackend).filter(ExecutionBackend.slug != 'temporal.builtin').delete(synchronize_session=False)
    
    # Delete all organizations - we'll recreate them
    session.query(Organization).delete(synchronize_session=False)
    
    # Delete users except admin
    admin_username = os.environ.get('EXECUTION_BACKEND_API_USER', 'admin')
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
            
            session.commit()
            
            print("🎉 Fake data seeding completed successfully!")
            print(f"Created:")
            print(f"  - {len(users)} users")
            print(f"  - {len(organizations)} organizations") 
            print(f"  - {len(execution_backends)} execution backends")
            print(f"  - {len(course_families)} course families")
            print(f"  - {len(courses)} courses")
            print(f"  - {len(course_groups)} course groups")
            print(f"  - {len(course_members)} course members")
            print(f"  - {len(course_content_types)} course content types (weekly, mandatory)")
            print(f"  - {len(course_contents)} course contents (units with assignments)")
            
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