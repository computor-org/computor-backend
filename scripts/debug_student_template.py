#!/usr/bin/env python3
"""
Debug script to test student template URL construction.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sqlalchemy.orm import Session
from computor_backend.database import get_db
from computor_backend.model.course import Course, CourseFamily
from computor_backend.model.organization import Organization
import json


def debug_course_student_template_url(course_id: str):
    """Debug student template URL construction for a course."""
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # Get course
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            print(f"❌ Course {course_id} not found")
            return
            
        print(f"\n✅ Found course: {course.title} ({course.path})")
        print(f"Course ID: {course.id}")
        
        # Check course properties
        print("\n📋 Course properties:")
        if course.properties:
            print(json.dumps(course.properties, indent=2))
        else:
            print("❌ No properties found")
            
        # Get student-template URL using the same logic as the API
        student_template_url = None
        
        # Check if course has GitLab properties
        if course.properties and "gitlab" in course.properties:
            course_gitlab = course.properties["gitlab"]
            
            # Option 1: Direct URL stored (backward compatibility)
            if "student_template_url" in course_gitlab:
                student_template_url = course_gitlab["student_template_url"]
                print(f"\n✅ Found direct URL: {student_template_url}")
            
            # Option 2: Construct from course's full_path
            elif "full_path" in course_gitlab:
                print(f"\n🔧 Course has full_path: {course_gitlab['full_path']}")
                
                # Get GitLab URL from organization
                if course.course_family_id:
                    family = db.query(CourseFamily).filter(CourseFamily.id == course.course_family_id).first()
                    if family and family.organization_id:
                        org = db.query(Organization).filter(Organization.id == family.organization_id).first()
                        if org and org.properties and "gitlab" in org.properties:
                            gitlab_url = org.properties["gitlab"].get("url")
                            if gitlab_url:
                                student_template_url = f"{gitlab_url}/{course_gitlab['full_path']}/student-template"
                                print(f"✅ Constructed URL: {student_template_url}")
                            else:
                                print("❌ No GitLab URL in organization")
                        else:
                            print("❌ Organization missing GitLab config")
                    else:
                        print("❌ Course family or organization not found")
                else:
                    print("❌ Course missing course family reference")
            else:
                print("❌ Course GitLab properties missing both 'student_template_url' and 'full_path'")
        else:
            print("❌ Course missing GitLab properties")
        
        if student_template_url:
            print(f"\n🎯 Final URL: {student_template_url}")
            
            # Transform for Docker
            if "localhost" in student_template_url:
                docker_url = student_template_url.replace("localhost", "172.17.0.1")
                print(f"🐳 Docker URL: {docker_url}")
        else:
            print("\n❌ Unable to determine student-template URL")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_student_template.py <course_id>")
        sys.exit(1)
        
    course_id = sys.argv[1]
    debug_course_student_template_url(course_id)