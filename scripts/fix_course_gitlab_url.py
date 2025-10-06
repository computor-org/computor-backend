#!/usr/bin/env python3
"""
Fix missing student_template_url in course properties.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from computor_backend.database import get_db
from computor_backend.model.course import Course
import json


def fix_course_gitlab_url(course_id: str, student_template_url: str):
    """Add missing student_template_url to course properties."""
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # Get course
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            print(f"❌ Course {course_id} not found")
            return
            
        print(f"\n✅ Found course: {course.title} ({course.path})")
        
        # Initialize properties if needed
        if not course.properties:
            course.properties = {}
            print("📝 Initialized empty properties")
            
        if "gitlab" not in course.properties:
            course.properties["gitlab"] = {}
            print("📝 Initialized gitlab section")
            
        # Show current GitLab config
        print("\nCurrent GitLab config:")
        print(json.dumps(course.properties.get("gitlab", {}), indent=2))
        
        # Add the student_template_url
        course.properties["gitlab"]["student_template_url"] = student_template_url
        print(f"\n✅ Added student_template_url: {student_template_url}")
        
        # Also add the projects section if missing
        if "projects" not in course.properties["gitlab"]:
            # Extract path from URL
            # http://localhost:8084/test/<...>/student-template
            path_parts = student_template_url.replace("http://", "").replace("https://", "").split("/")
            full_path = "/".join(path_parts[1:])  # Skip the domain
            
            course.properties["gitlab"]["projects"] = {
                "student_template": {
                    "path": "student-template",
                    "full_path": full_path,
                    "web_url": student_template_url,
                    "description": "Template repository for students"
                }
            }
            print("✅ Added projects section")
        
        # Mark the field as modified so SQLAlchemy knows to update it
        flag_modified(course, "properties")
        
        # Commit the changes
        db.commit()
        db.refresh(course)
        
        print("\n✅ Course properties updated successfully!")
        print("\nUpdated GitLab config:")
        print(json.dumps(course.properties["gitlab"], indent=2))
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python fix_course_gitlab_url.py <course_id> <student_template_url>")
        print("Example: python fix_course_gitlab_url.py abc-123 http://localhost:8084/test/course/student-template")
        sys.exit(1)
        
    course_id = sys.argv[1]
    student_template_url = sys.argv[2]
    fix_course_gitlab_url(course_id, student_template_url)