import json
import os
from pydantic import BaseModel, Field
import yaml
from typing import Annotated, Optional, List, Dict, Any
from uuid import UUID
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from ctutor_backend.api.auth import get_current_permissions
from ctutor_backend.permissions.core import check_course_permissions
from ctutor_backend.permissions.principal import Principal

from ctutor_backend.api.exceptions import BadRequestException, NotFoundException
from ctutor_backend.api.filesystem import get_path_course_content, mirror_entity_to_filesystem
from ctutor_backend.database import get_db
from ctutor_backend.interface.course_contents import CourseContentGet, CourseContentInterface
from ctutor_backend.api.api_builder import CrudRouter
from ctutor_backend.model.course import CourseContent, Course
from ctutor_backend.model.example import Example, ExampleVersion, ExampleDependency
from ctutor_backend.redis_cache import get_redis_client
from aiocache import BaseCache

course_content_router = CrudRouter(CourseContentInterface)

class CourseContentFileQuery(BaseModel):
    filename: Optional[str] = None

@course_content_router.router.get("/files/{course_content_id}", response_model=dict)
async def get_course_content_meta(permissions: Annotated[Principal, Depends(get_current_permissions)], course_content_id: UUID | str, file_query: CourseContentFileQuery = Depends(), db: Session = Depends(get_db)):

    if check_course_permissions(permissions,CourseContent,"_tutor",db).filter(CourseContent.id == course_content_id).first() == None:
        raise NotFoundException()

    course_content_dir = await get_path_course_content(course_content_id,db)

    if file_query.filename == None:
        raise BadRequestException()

    with open(os.path.join(course_content_dir,file_query.filename),'r') as file:
        content = file.read()

        if file_query.filename.endswith(".yaml") or file_query.filename.endswith(".yml"):
            try:
                data = yaml.safe_load(content)
                if isinstance(data, dict):
                    return data
            except Exception:
                raise BadRequestException()

        elif file_query.filename.endswith(".json"):
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    return data
            except Exception:
                raise BadRequestException()
        else:
            return {"content": content}

async def event_wrapper(entity: CourseContentGet, db: Session, permissions: Principal):
    try:
        await mirror_entity_to_filesystem(str(entity.id),CourseContentInterface,db)
    except Exception as e:
        print(e)

course_content_router.on_created.append(event_wrapper)
course_content_router.on_updated.append(event_wrapper)

# Note: We don't need to track CourseContent deletion in ExampleDeployment
# The deployment tracks what's actually in the student-template repository,
# not what CourseContent intends to deploy

# DTOs for Example Assignment

class AssignExampleRequest(BaseModel):
    """Request to assign an example to course content."""
    example_id: str = Field(description="UUID of the Example to assign")
    example_version: str = Field(default="latest", description="Version to assign (default: latest)")

class CourseContentExampleResponse(BaseModel):
    """Response for course content with example information."""
    id: str
    path: str
    title: str
    example: Optional[Dict[str, Any]] = None
    deployment_status: str = Field(description="pending_release, released, modified")

# Example Assignment Endpoints

@course_content_router.router.post(
    "/{content_id}/assign-example",
    response_model=CourseContentExampleResponse
)
async def assign_example_to_content(
    content_id: str,
    request: AssignExampleRequest,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
    cache: Annotated[BaseCache, Depends(get_redis_client)] = None
):
    """
    Assign an example to course content (database only).
    
    This is step 1 of the two-step process. It only updates the database
    to link the example to the course content. No Git operations occur.
    The actual deployment happens when generating the student template.
    """
    # Get course content
    content = db.query(CourseContent).filter(CourseContent.id == content_id).first()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CourseContent {content_id} not found"
        )
    
    # Check permissions on the course
    if check_course_permissions(permissions, Course, "_maintainer", db).filter(Course.id == content.course_id).first() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this course content"
        )
    
    # Validate example exists
    example = db.query(Example).filter(Example.id == request.example_id).first()
    if not example:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Example {request.example_id} not found"
        )
    
    # Get the requested version
    if request.example_version == "latest":
        version = db.query(ExampleVersion).filter(
            ExampleVersion.example_id == request.example_id
        ).order_by(ExampleVersion.version_number.desc()).first()
        
        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No versions found for example {request.example_id}"
            )
        version_tag = version.version_tag
    else:
        version = db.query(ExampleVersion).filter(
            and_(
                ExampleVersion.example_id == request.example_id,
                ExampleVersion.version_tag == request.example_version
            )
        ).first()
        
        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {request.example_version} not found for example"
            )
        version_tag = request.example_version
    
    # Note: ExampleDeployment tracking happens during student-template generation,
    # not during assignment. This just updates the CourseContent's intent.
    
    # Update course content
    content.example_id = request.example_id
    content.example_version = version_tag
    content.deployment_status = "pending_release"
    
    db.commit()
    db.refresh(content)
    
    # Clear cache
    if cache:
        await cache.delete(f"course:{content.course_id}:contents")
    
    # Return updated content with example info
    return CourseContentExampleResponse(
        id=str(content.id),
        path=str(content.path),
        title=content.title,
        example={
            "id": str(example.id),
            "name": example.title,
            "version": version_tag,
            "latest_version": version.version_tag if version else version_tag,
            "has_update": False
        },
        deployment_status=content.deployment_status
    )

@course_content_router.router.delete("/{content_id}/example")
async def remove_example_assignment(
    content_id: str,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
    cache: Annotated[BaseCache, Depends(get_redis_client)] = None
):
    """
    Remove example assignment from course content.
    
    This only clears the database assignment. The content will be
    removed from the student template on the next generation.
    """
    # Get course content
    content = db.query(CourseContent).filter(CourseContent.id == content_id).first()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CourseContent {content_id} not found"
        )
    
    # Check permissions
    if check_course_permissions(permissions, Course, "_maintainer", db).filter(Course.id == content.course_id).first() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this course content"
        )
    
    # Note: ExampleDeployment removal happens during next student-template generation,
    # not during unassignment. This just updates the CourseContent's intent.
    
    # Clear example assignment
    content.example_id = None
    content.example_version = None
    content.deployment_status = "unassigned"
    
    db.commit()
    
    # Clear cache
    if cache:
        await cache.delete(f"course:{content.course_id}:contents")
    
    return {"status": "removed"}

@course_content_router.router.get(
    "/courses/{course_id}/contents-with-examples",
    response_model=Dict[str, Any]
)
async def get_course_contents_with_examples(
    course_id: str,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
    cache: Annotated[BaseCache, Depends(get_redis_client)] = None
):
    """
    Get all course contents with their example assignment status.
    
    Shows which contents have examples assigned and their deployment status.
    """
    # Check permissions
    if check_course_permissions(permissions, Course, "_maintainer", db).filter(Course.id == course_id).first() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this course"
        )
    
    # Check cache first
    cache_key = f"course:{course_id}:contents-with-examples"
    if cache:
        cached = await cache.get(cache_key)
        if cached:
            return cached
    
    # Get all course contents
    contents = db.query(CourseContent).filter(
        CourseContent.course_id == course_id
    ).order_by(CourseContent.path).all()
    
    contents_list = []
    for content in contents:
        content_data = {
            "id": str(content.id),
            "path": str(content.path),
            "title": content.title,
            "example": None
        }
        
        if content.example_id:
            # Get example details
            example = db.query(Example).filter(
                Example.id == content.example_id
            ).first()
            
            if example:
                # Check for updates
                latest_version = None
                has_update = False
                
                if content.example_version != "latest":
                    latest = db.query(ExampleVersion).filter(
                        ExampleVersion.example_id == content.example_id
                    ).order_by(ExampleVersion.version_number.desc()).first()
                    
                    if latest:
                        latest_version = latest.version_tag
                        has_update = latest.version_tag != content.example_version
                
                content_data["example"] = {
                    "id": str(example.id),
                    "name": example.title,
                    "version": content.example_version,
                    "latest_version": latest_version,
                    "has_update": has_update,
                    "release_status": content.deployment_status
                }
        
        contents_list.append(content_data)
    
    result = {"contents": contents_list}
    
    # Cache the result
    if cache:
        await cache.set(cache_key, result, ttl=300)  # Cache for 5 minutes
    
    return result

@course_content_router.router.get(
    "/courses/{course_id}/available-examples",
    response_model=Dict[str, Any]
)
async def get_available_examples(
    course_id: str,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
    cache: Annotated[BaseCache, Depends(get_redis_client)] = None,
    search: Optional[str] = None,
    category: Optional[str] = None,
    language: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Get available examples from the Example Library for a course.
    
    Returns examples that can be deployed to course content,
    with filtering by search query, category, and language.
    """
    # Check permissions
    if check_course_permissions(permissions, Course, "_maintainer", db).filter(Course.id == course_id).first() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this course"
        )
    
    # Check cache first
    cache_key = f"course:{course_id}:available-examples:{search}:{category}:{language}:{limit}:{offset}"
    if cache:
        cached = await cache.get(cache_key)
        if cached:
            return cached
    
    # Build query for examples
    query = db.query(Example).filter(
        Example.archived_at.is_(None)
    )
    
    # Apply search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Example.title.ilike(search_pattern),
                Example.description.ilike(search_pattern),
                Example.properties['tags'].astext.ilike(search_pattern)
            )
        )
    
    # Apply category filter
    if category:
        query = query.filter(
            Example.properties['category'].astext == category
        )
    
    # Apply language filter  
    if language:
        query = query.filter(
            Example.properties['language'].astext == language
        )
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    examples = query.offset(offset).limit(limit).all()
    
    # Get unique categories and languages for filters
    all_examples = db.query(Example).filter(Example.archived_at.is_(None)).all()
    categories = set()
    languages = set()
    
    for ex in all_examples:
        if ex.properties:
            if 'category' in ex.properties:
                categories.add(ex.properties['category'])
            if 'language' in ex.properties:
                languages.add(ex.properties['language'])
    
    # Format response
    example_list = []
    for example in examples:
        # Get latest version
        latest_version = db.query(ExampleVersion).filter(
            ExampleVersion.example_id == example.id
        ).order_by(ExampleVersion.version_number.desc()).first()
        
        example_data = {
            "id": str(example.id),
            "title": example.title,
            "description": example.description,
            "repository_id": str(example.example_repository_id),
            "latest_version": latest_version.version_tag if latest_version else None
        }
        
        # Add properties if they exist
        if example.properties:
            if 'category' in example.properties:
                example_data['category'] = example.properties['category']
            if 'language' in example.properties:
                example_data['language'] = example.properties['language']
            if 'tags' in example.properties:
                example_data['tags'] = example.properties.get('tags', [])
        
        example_list.append(example_data)
    
    result = {
        "examples": example_list,
        "total": total,
        "filters": {
            "categories": sorted(list(categories)),
            "languages": sorted(list(languages))
        }
    }
    
    # Cache the result
    if cache:
        await cache.set(cache_key, result, ttl=300)  # Cache for 5 minutes
    
    return result

@course_content_router.router.get(
    "/courses/{course_id}/examples/{example_id}/deployment-preview",
    response_model=Dict[str, Any]
)
async def get_deployment_preview(
    course_id: str,
    example_id: str,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db),
    version: str = "latest",
    target_path: str = None
):
    """
    Get a preview of what will happen when deploying an example.
    
    Shows files, dependencies, and potential conflicts.
    """
    # Check permissions
    if check_course_permissions(permissions, Course, "_maintainer", db).filter(Course.id == course_id).first() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this course"
        )
    
    # Get example
    example = db.query(Example).filter(Example.id == example_id).first()
    if not example:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Example {example_id} not found"
        )
    
    # Get version
    if version == "latest":
        version_obj = db.query(ExampleVersion).filter(
            ExampleVersion.example_id == example_id
        ).order_by(ExampleVersion.version_number.desc()).first()
    else:
        version_obj = db.query(ExampleVersion).filter(
            and_(
                ExampleVersion.example_id == example_id,
                ExampleVersion.version_tag == version
            )
        ).first()
    
    if not version_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version} not found for example"
        )
    
    # Check for conflicts if target_path provided
    conflicts = []
    if target_path:
        # Check if content already has a different example
        existing_content = db.query(CourseContent).filter(
            and_(
                CourseContent.course_id == course_id,
                CourseContent.path == target_path
            )
        ).first()
        
        if existing_content and existing_content.example_id:
            if str(existing_content.example_id) != example_id:
                existing_example = db.query(Example).filter(
                    Example.id == existing_content.example_id
                ).first()
                conflicts.append({
                    "type": "existing_example",
                    "path": target_path,
                    "current_example_id": str(existing_content.example_id),
                    "current_example_title": existing_example.title if existing_example else "Unknown",
                    "current_example_version": existing_content.example_version
                })
    
    # Get dependencies
    dependencies = []
    deps = db.query(ExampleDependency).filter(
        ExampleDependency.example_id == example_id
    ).all()
    
    for dep in deps:
        dep_example = db.query(Example).filter(
            Example.id == dep.dependency_example_id
        ).first()
        if dep_example:
            dependencies.append({
                "example_id": str(dep.dependency_example_id),
                "title": dep_example.title,
                "required": dep.required
            })
    
    # Estimate file structure (in real implementation, would check MinIO)
    file_structure = {
        "files": [
            "meta.yaml",
            "README.md",
        ],
        "size_mb": 0.1  # Placeholder
    }
    
    # Add files based on properties
    if version_obj.properties:
        props = version_obj.properties.get('properties', {})
        if 'studentTemplates' in props:
            file_structure['files'].extend(props['studentTemplates'])
        if 'testFiles' in props:
            file_structure['files'].extend(props['testFiles'])
        if 'additionalFiles' in props:
            file_structure['files'].extend(props['additionalFiles'])
    
    return {
        "example": {
            "id": str(example.id),
            "title": example.title,
            "description": example.description,
            "category": example.properties.get('category') if example.properties else None,
            "language": example.properties.get('language') if example.properties else None
        },
        "version": {
            "id": str(version_obj.id),
            "version_tag": version_obj.version_tag,
            "created_at": version_obj.created_at.isoformat() if version_obj.created_at else None
        },
        "dependencies": dependencies,
        "conflicts": conflicts,
        "file_structure": file_structure
    }