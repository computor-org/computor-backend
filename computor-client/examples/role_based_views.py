"""
Example usage of role-based view clients.

This demonstrates how students, tutors, and lecturers interact with the API
through their respective role-based view clients.
"""

import asyncio
from computor_client import ComputorClient


async def student_workflow():
    """Example workflow for a student user."""

    async with ComputorClient(base_url="http://localhost:8000") as client:
        # Authenticate as student
        await client.authenticate(username="student@example.com", password="password")

        print("=== Student View ===\n")

        # Get my courses as a student
        my_courses = await client.student_view.get_my_courses()
        print(f"📚 I'm enrolled in {len(my_courses)} courses")

        for course in my_courses:
            print(f"   - {course.get('name', 'Unknown Course')}")

        # Get course contents for a specific course
        if my_courses:
            course_id = my_courses[0]['id']
            course_contents = await client.student_view.get_my_course_contents(
                course_id=course_id
            )
            print(f"\n📝 Course contents available: {len(course_contents)}")

            # Get detailed view of first content
            if course_contents:
                content_id = course_contents[0]['id']
                content_detail = await client.student_view.get_course_content_detail(
                    content_id
                )
                print(f"\n📄 Content: {content_detail.get('title', 'Untitled')}")
                print(f"   Type: {content_detail.get('content_type', 'Unknown')}")
                print(f"   Status: {content_detail.get('status', 'Unknown')}")


async def tutor_workflow():
    """Example workflow for a tutor user."""

    async with ComputorClient(base_url="http://localhost:8000") as client:
        # Authenticate as tutor
        await client.authenticate(username="tutor@example.com", password="password")

        print("\n=== Tutor View ===\n")

        # Get courses I'm tutoring
        my_courses = await client.tutor_view.get_my_courses()
        print(f"👨‍🏫 I'm tutoring {len(my_courses)} courses")

        # Get students I'm responsible for
        course_members = await client.tutor_view.get_course_members()
        print(f"👥 I'm tutoring {len(course_members)} students")

        for member in course_members[:5]:  # Show first 5
            print(f"   - {member.get('user', {}).get('name', 'Unknown')}")

        # View a specific student's progress
        if course_members:
            student_id = course_members[0]['id']
            student_contents = await client.tutor_view.get_student_course_contents(
                student_id
            )
            print(f"\n📊 Student has {len(student_contents)} course contents")

            # Update grades for a student
            if student_contents:
                content_id = student_contents[0]['id']
                updated = await client.tutor_view.update_student_grades(
                    course_member_id=student_id,
                    course_content_id=content_id,
                    grades_data={
                        "grade": 85,
                        "feedback": "Good work! Consider improving X and Y."
                    }
                )
                print(f"✅ Updated grade for student")


async def lecturer_workflow():
    """Example workflow for a lecturer user."""

    async with ComputorClient(base_url="http://localhost:8000") as client:
        # Authenticate as lecturer
        await client.authenticate(username="lecturer@example.com", password="password")

        print("\n=== Lecturer View ===\n")

        # Get courses I'm teaching
        my_courses = await client.lecturer_view.get_my_courses()
        print(f"🎓 I'm teaching {len(my_courses)} courses")

        for course in my_courses:
            print(f"   - {course.get('name', 'Unknown')}")

        # Get course contents I've created
        if my_courses:
            course_id = my_courses[0]['id']
            course_contents = await client.lecturer_view.get_my_course_contents(
                course_id=course_id
            )
            print(f"\n📚 Course has {len(course_contents)} contents")

            # Create new course content
            new_content = await client.lecturer_view.create_course_content(
                course_id=course_id,
                content_data={
                    "title": "Week 5: Advanced Topics",
                    "content_type": "assignment",
                    "description": "Complete the advanced exercise",
                    "due_date": "2025-11-01T23:59:59Z"
                }
            )
            print(f"\n✅ Created new course content: {new_content.get('title')}")

            # Update course content
            if course_contents:
                content_id = course_contents[0]['id']
                updated = await client.lecturer_view.update_course_content(
                    content_id,
                    content_data={
                        "description": "Updated description with more details"
                    }
                )
                print(f"✅ Updated course content")


async def main():
    """Run all workflow examples."""

    print("=" * 60)
    print("Role-Based View Client Examples")
    print("=" * 60)

    try:
        await student_workflow()
    except Exception as e:
        print(f"❌ Student workflow error: {e}")

    try:
        await tutor_workflow()
    except Exception as e:
        print(f"❌ Tutor workflow error: {e}")

    try:
        await lecturer_workflow()
    except Exception as e:
        print(f"❌ Lecturer workflow error: {e}")

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
