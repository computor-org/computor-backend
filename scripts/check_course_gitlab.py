#!/usr/bin/env python3
"""
Quick script to check GitLab configuration for a course.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sqlalchemy.orm import Session
from computor_backend.database import get_db
from computor_backend.model.course import Course, CourseFamily
import json


def check_course_gitlab(course_id: str):
    """Check GitLab configuration for a course."""
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # Get course
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            print(f"Course {course_id} not found")
            return
            
        print(f"\nCourse: {course.title} ({course.path})")
        print(f"ID: {course.id}")
        
        # Check properties
        if not course.properties:
            print("\n❌ No properties found on course")
            return
            
        print("\nCourse properties:")
        print(json.dumps(course.properties, indent=2))
        
        # Check GitLab config
        if "gitlab" not in course.properties:
            print("\n❌ No GitLab configuration found")
            
            # Check course family
            if course.course_family_id:
                family = db.query(CourseFamily).filter(CourseFamily.id == course.course_family_id).first()
                if family:
                    print(f"\nCourse Family: {family.title}")
                    if family.properties and "gitlab" in family.properties:
                        print("✅ Course family has GitLab config:")
                        print(json.dumps(family.properties["gitlab"], indent=2))
                    else:
                        print("❌ Course family also missing GitLab config")
        else:
            gitlab_config = course.properties["gitlab"]
            print("\n✅ GitLab configuration found:")
            print(json.dumps(gitlab_config, indent=2))
            
            # Check specific fields
            print("\nChecking required fields:")
            if "group_id" in gitlab_config:
                print(f"✅ group_id: {gitlab_config['group_id']}")
            else:
                print("❌ Missing group_id")
                
            if "student_template_url" in gitlab_config:
                print(f"✅ student_template_url: {gitlab_config['student_template_url']}")
            else:
                print("❌ Missing student_template_url")
                
            if "projects" in gitlab_config:
                print("✅ projects:")
                print(json.dumps(gitlab_config["projects"], indent=2))
            else:
                print("❌ Missing projects info")
                
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_course_gitlab.py <course_id>")
        sys.exit(1)
        
    course_id = sys.argv[1]
    check_course_gitlab(course_id)