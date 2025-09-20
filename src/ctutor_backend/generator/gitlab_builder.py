"""
New GitLab builder with integrated database operations and enhanced property storage.

This module provides a clean implementation of GitLab group creation with:
- Direct database access via repositories
- Enhanced GitLab property storage
- Proper error handling for both GitLab and database operations
- Validation and synchronization of GitLab metadata
"""

import logging
import tempfile
import os
import yaml
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
from gitlab import Gitlab
from gitlab.v4.objects import Group
from gitlab.exceptions import GitlabCreateError, GitlabGetError, GitlabDeleteError
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.attributes import flag_modified

from ctutor_backend.api.exceptions import NotImplementedException
from ctutor_backend.services.git_service import GitService

from ctutor_backend.interface.deployments import (
    ComputorDeploymentConfig,
    GitLabConfig
)
from ctutor_backend.interface.organizations import (
    OrganizationCreate,
    OrganizationProperties
)
from ctutor_backend.interface.course_families import (
    CourseFamilyCreate,
    CourseFamilyProperties
)
from ctutor_backend.interface.courses import (
    CourseCreate,
    CourseProperties
)
from ctutor_backend.model.organization import Organization
from ctutor_backend.model.course import CourseFamily, Course
from ctutor_backend.repositories.organization import OrganizationRepository
from ctutor_backend.services.git_service import GitService
from ..custom_types import Ltree


logger = logging.getLogger(__name__)


class EnhancedGitLabConfig(GitLabConfig):
    """Enhanced GitLab configuration with complete metadata."""
    group_id: Optional[int] = None
    namespace_id: Optional[int] = None
    namespace_path: Optional[str] = None
    # web_url is already defined in parent GitLabConfigGet
    visibility: Optional[str] = None
    last_synced_at: Optional[datetime] = None


class GitLabBuilder:
    """
    New GitLab builder with integrated database operations.
    
    This builder creates GitLab groups and corresponding database entries
    with enhanced property storage and proper error handling.
    """
    
    def __init__(
        self,
        db_session: Session,
        gitlab_url: str,
        gitlab_token: str,
        git_service: Optional[GitService] = None
    ):
        """
        Initialize the GitLab builder.
        
        Args:
            db_session: SQLAlchemy database session
            gitlab_url: GitLab instance URL
            gitlab_token: GitLab access token
            git_service: Optional GitService for repository operations
        """
        self.db = db_session
        self.gitlab_url = gitlab_url  # Store original URL for database
        self.gitlab_token = gitlab_token
        self.git_service = git_service
        
        # Transform URL for Docker environment if needed (API calls only)
        from ..utils.docker_utils import transform_localhost_url
        api_url = transform_localhost_url(gitlab_url)
        
        # Initialize GitLab connection with transformed URL
        self.gitlab = Gitlab(url=api_url, private_token=gitlab_token, keep_base_url=True)
        try:
            # For group tokens, gl.auth() doesn't work properly
            # Test with a simple API call instead
            self.gitlab.version()  # Test API access
            logger.info(f"Successfully authenticated with GitLab at {api_url}")
        except Exception as e:
            logger.error(f"Failed to authenticate with GitLab: {e}")
            raise
        
        # Initialize repositories
        self.org_repo = OrganizationRepository(db_session)
    
    def create_deployment_hierarchy(
        self,
        deployment: ComputorDeploymentConfig,
        created_by_user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create the complete deployment hierarchy with GitLab groups and database entries.
        
        Args:
            deployment: Deployment configuration
            created_by_user_id: ID of the user creating the deployment
            
        Returns:
            Dictionary with created entities and status
        """
        results = {
            "organization": None,
            "course_family": None,
            "course": None,
            "gitlab_groups_created": [],
            "database_entries_created": [],
            "errors": [],
            "success": False
        }
        
        try:
            # Start database transaction
            logger.info("Starting deployment hierarchy creation")
            
            # Phase 1: Create Organization
            org_result = self._create_organization(
                deployment,
                created_by_user_id
            )
            
            if not org_result["success"]:
                results["errors"].append(org_result["error"])
                self.db.rollback()
                return results
            
            results["organization"] = org_result["organization"]
            if org_result.get("gitlab_created"):
                results["gitlab_groups_created"].append(f"Organization: {org_result['gitlab_group'].full_path}")
            if org_result.get("db_created"):
                results["database_entries_created"].append(f"Organization: {org_result['organization'].path}")
            
            # Phase 2: Create CourseFamily
            family_result = self._create_course_family(
                deployment,
                results["organization"],
                created_by_user_id
            )
            
            if not family_result["success"]:
                results["errors"].append(family_result["error"])
                self.db.rollback()
                return results
            
            results["course_family"] = family_result["course_family"]
            if family_result.get("gitlab_created"):
                results["gitlab_groups_created"].append(f"CourseFamily: {family_result['gitlab_group'].full_path}")
            if family_result.get("db_created"):
                results["database_entries_created"].append(f"CourseFamily: {family_result['course_family'].path}")
            
            # Phase 3: Create Course
            course_result = self._create_course(
                deployment,
                results["organization"],
                results["course_family"],
                created_by_user_id
            )
            
            if not course_result["success"]:
                results["errors"].append(course_result["error"])
                self.db.rollback()
                return results
            
            results["course"] = course_result["course"]
            if course_result.get("gitlab_created"):
                results["gitlab_groups_created"].append(f"Course: {course_result['gitlab_group'].full_path}")
            if course_result.get("db_created"):
                results["database_entries_created"].append(f"Course: {course_result['course'].path}")
            
            # Commit all changes
            self.db.commit()
            results["success"] = True
            logger.info("Successfully created deployment hierarchy")
            
        except Exception as e:
            logger.error(f"Unexpected error creating deployment hierarchy: {e}")
            results["errors"].append(f"Unexpected error: {str(e)}")
            self.db.rollback()
        
        return results
    
    def _create_organization(
        self,
        deployment: ComputorDeploymentConfig,
        created_by_user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create organization with GitLab group and database entry."""
        result = {
            "success": False,
            "organization": None,
            "gitlab_group": None,
            "gitlab_created": False,
            "db_created": False,
            "error": None
        }
        
        try:
            logger.info(f"Creating organization with path: {deployment.organization.path}")
            # Check if organization already exists in database
            existing_org = self.org_repo.find_by_path(deployment.organization.path)
            
            if existing_org:
                logger.info(f"Organization already exists: {existing_org.path}")
                result["organization"] = existing_org
                
                # Validate GitLab group if properties exist
                if existing_org.properties and existing_org.properties.get("gitlab"):
                    gitlab_config = existing_org.properties["gitlab"]
                    if gitlab_config.get("group_id"):
                        # Validate the GitLab group still exists
                        is_valid = self._validate_gitlab_group(
                            gitlab_config["group_id"],
                            deployment.organization.path
                        )
                        if not is_valid:
                            # Need to recreate GitLab group
                            logger.warning(f"GitLab group for organization {existing_org.path} no longer exists")
                            gitlab_group, _ = self._create_gitlab_group(
                                deployment.organization.name,
                                deployment.organization.path,
                                deployment.organization.gitlab.parent,
                                deployment.organization.description or ""
                            )
                            result["gitlab_group"] = gitlab_group
                            result["gitlab_created"] = True
                            
                            # Create organization-specific config with encrypted token
                            gitlab_config = self._create_organization_gitlab_config(gitlab_group)
                            
                            # Update organization properties
                            self._update_organization_gitlab_properties(
                                existing_org,
                                gitlab_group,
                                gitlab_config
                            )
                        else:
                            result["gitlab_group"] = self.gitlab.groups.get(gitlab_config["group_id"])
                    else:
                        # No group_id stored, create GitLab group
                        gitlab_group, _ = self._create_gitlab_group(
                            deployment.organization.name,
                            deployment.organization.path,
                            deployment.organization.gitlab.parent,
                            deployment.organization.description or ""
                        )
                        result["gitlab_group"] = gitlab_group
                        result["gitlab_created"] = True
                        
                        # Create organization-specific config with encrypted token
                        gitlab_config = self._create_organization_gitlab_config(gitlab_group)
                        
                        # Update organization properties
                        self._update_organization_gitlab_properties(
                            existing_org,
                            gitlab_group,
                            gitlab_config
                        )
                else:
                    # No GitLab properties, create GitLab group
                    gitlab_group, _ = self._create_gitlab_group(
                        deployment.organization.name,
                        deployment.organization.path,
                        deployment.organization.gitlab.parent,
                        deployment.organization.description or ""
                    )
                    result["gitlab_group"] = gitlab_group
                    result["gitlab_created"] = True
                    
                    # Create organization-specific config with encrypted token
                    gitlab_config = self._create_organization_gitlab_config(gitlab_group)
                    
                    # Update organization properties
                    self._update_organization_gitlab_properties(
                        existing_org,
                        gitlab_group,
                        gitlab_config
                    )
                
                result["success"] = True
                return result
            
            # Create new organization
            # First create GitLab group
            logger.info(f"Creating new organization GitLab group with parent: {deployment.organization.gitlab.parent}")
            gitlab_group, _ = self._create_gitlab_group(
                deployment.organization.name,
                deployment.organization.path,
                deployment.organization.gitlab.parent,
                deployment.organization.description or ""
            )
            result["gitlab_group"] = gitlab_group
            result["gitlab_created"] = True
            
            # Create organization-specific config with encrypted token
            gitlab_config = self._create_organization_gitlab_config(gitlab_group)
            
            # Create organization in database
            logger.info(f"Creating organization with gitlab_config: {gitlab_config}")
            org_data = OrganizationCreate(
                title=deployment.organization.name,
                description=deployment.organization.description,
                path=deployment.organization.path,
                organization_type="organization",
                properties=OrganizationProperties(gitlab=gitlab_config)
            )
            
            new_org = Organization(
                title=org_data.title,
                description=org_data.description,
                path=Ltree(org_data.path),  # Convert to Ltree
                organization_type=org_data.organization_type,
                properties=org_data.properties.model_dump() if org_data.properties else {},
                created_by=created_by_user_id,
                updated_by=created_by_user_id
            )
            
            created_org = self.org_repo.create(new_org)
            result["organization"] = created_org
            result["db_created"] = True
            result["success"] = True
            
            logger.info(f"Created organization: {created_org.path} (ID: {created_org.id})")
            
        except GitlabCreateError as e:
            logger.error(f"GitLab error creating organization: {e}")
            result["error"] = f"GitLab error: {str(e)}"
        except IntegrityError as e:
            logger.error(f"Database integrity error creating organization: {e}")
            result["error"] = f"Database integrity error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error creating organization: {e}")
            result["error"] = f"Unexpected error: {str(e)}"
        
        return result
    
    def _create_course_family(
        self,
        deployment: ComputorDeploymentConfig,
        organization: Organization,
        created_by_user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create course family with GitLab group and database entry."""
        result = {
            "success": False,
            "course_family": None,
            "gitlab_group": None,
            "gitlab_created": False,
            "db_created": False,
            "error": None
        }
        
        try:
            # Check if course family already exists
            existing_family = self.db.query(CourseFamily).filter(
                CourseFamily.organization_id == organization.id,
                CourseFamily.path == Ltree(deployment.courseFamily.path)
            ).first()
            
            if existing_family:
                logger.info(f"CourseFamily already exists: {existing_family.path}")
                result["course_family"] = existing_family
                
                # Get parent GitLab group
                parent_gitlab_config = organization.properties.get("gitlab", {})
                parent_group_id = parent_gitlab_config.get("group_id")
                
                if not parent_group_id:
                    result["error"] = "Parent organization missing GitLab group_id"
                    return result
                
                try:
                    parent_group = self.gitlab.groups.get(parent_group_id)
                except GitlabGetError as e:
                    result["error"] = f"Failed to retrieve parent group {parent_group_id}: {str(e)}"
                    return result
                
                # Validate GitLab group if properties exist
                if existing_family.properties and existing_family.properties.get("gitlab"):
                    gitlab_config = existing_family.properties["gitlab"]
                    if gitlab_config.get("group_id"):
                        is_valid = self._validate_gitlab_group(
                            gitlab_config["group_id"],
                            f"{parent_group.full_path}/{deployment.courseFamily.path}"
                        )
                        if not is_valid:
                            # Recreate GitLab group
                            gitlab_group, _ = self._create_gitlab_group(
                                deployment.courseFamily.name,
                                deployment.courseFamily.path,
                                parent_group_id,
                                deployment.courseFamily.description or "",
                                parent_group
                            )
                            result["gitlab_group"] = gitlab_group
                            result["gitlab_created"] = True
                            
                            # Create child-specific config WITHOUT token
                            gitlab_config = self._create_child_gitlab_config(gitlab_group)
                            
                            # Update properties
                            self._update_course_family_gitlab_properties(
                                existing_family,
                                gitlab_group,
                                gitlab_config
                            )
                        else:
                            result["gitlab_group"] = self.gitlab.groups.get(gitlab_config["group_id"])
                    else:
                        # Create GitLab group
                        gitlab_group, _ = self._create_gitlab_group(
                            deployment.courseFamily.name,
                            deployment.courseFamily.path,
                            parent_group_id,
                            deployment.courseFamily.description or "",
                            parent_group
                        )
                        result["gitlab_group"] = gitlab_group
                        result["gitlab_created"] = True
                        
                        # Create child-specific config WITHOUT token
                        gitlab_config = self._create_child_gitlab_config(gitlab_group)
                        
                        # Update properties
                        self._update_course_family_gitlab_properties(
                            existing_family,
                            gitlab_group,
                            gitlab_config
                        )
                else:
                    # Create GitLab group
                    gitlab_group, _ = self._create_gitlab_group(
                        deployment.courseFamily.name,
                        deployment.courseFamily.path,
                        parent_group_id,
                        deployment.courseFamily.description or "",
                        parent_group
                    )
                    result["gitlab_group"] = gitlab_group
                    result["gitlab_created"] = True
                    
                    # Create child-specific config WITHOUT token
                    gitlab_config = self._create_child_gitlab_config(gitlab_group)
                    
                    # Update properties
                    self._update_course_family_gitlab_properties(
                        existing_family,
                        gitlab_group,
                        gitlab_config
                    )
                
                result["success"] = True
                return result
            
            # Create new course family
            # Get parent GitLab group
            parent_gitlab_config = organization.properties.get("gitlab", {})
            parent_group_id = parent_gitlab_config.get("group_id")
            
            if not parent_group_id:
                result["error"] = "Parent organization missing GitLab group_id"
                return result
            
            try:
                parent_group = self.gitlab.groups.get(parent_group_id)
            except GitlabGetError as e:
                result["error"] = f"Failed to retrieve parent group {parent_group_id}: {str(e)}"
                return result
            
            # Create GitLab group
            gitlab_group, _ = self._create_gitlab_group(
                deployment.courseFamily.name,
                deployment.courseFamily.path,
                parent_group_id,
                deployment.courseFamily.description or "",
                parent_group
            )
            result["gitlab_group"] = gitlab_group
            result["gitlab_created"] = True
            
            # Create child-specific config WITHOUT token
            gitlab_config = self._create_child_gitlab_config(gitlab_group)
            
            # Create course family in database
            family_data = CourseFamilyCreate(
                title=deployment.courseFamily.name,
                description=deployment.courseFamily.description or "",
                path=deployment.courseFamily.path,
                organization_id=str(organization.id),
                properties=CourseFamilyProperties(gitlab=gitlab_config)
            )
            
            new_family = CourseFamily(
                title=family_data.title,
                description=family_data.description,
                path=Ltree(family_data.path),  # Convert to Ltree
                organization_id=organization.id,
                properties=family_data.properties.model_dump() if family_data.properties else {},
                created_by=created_by_user_id,
                updated_by=created_by_user_id
            )
            
            self.db.add(new_family)
            self.db.flush()  # Get the ID
            
            result["course_family"] = new_family
            result["db_created"] = True
            result["success"] = True
            
            logger.info(f"Created course family: {new_family.path} (ID: {new_family.id})")
            
        except GitlabCreateError as e:
            logger.error(f"GitLab error creating course family: {e}")
            result["error"] = f"GitLab error: {str(e)}"
        except IntegrityError as e:
            logger.error(f"Database integrity error creating course family: {e}")
            result["error"] = f"Database integrity error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error creating course family: {e}")
            result["error"] = f"Unexpected error: {str(e)}"
        
        return result
    
    def _create_course(
        self,
        deployment: ComputorDeploymentConfig,
        organization: Organization,
        course_family: CourseFamily,
        created_by_user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create course with GitLab group and database entry."""
        result = {
            "success": False,
            "course": None,
            "gitlab_group": None,
            "gitlab_created": False,
            "db_created": False,
            "error": None
        }
        
        try:
            # Check if course already exists
            existing_course = self.db.query(Course).filter(
                Course.course_family_id == course_family.id,
                Course.path == Ltree(deployment.course.path)
            ).first()
            
            if existing_course:
                logger.info(f"Course already exists: {existing_course.path}")
                result["course"] = existing_course
                
                # Get parent GitLab group
                parent_gitlab_config = course_family.properties.get("gitlab", {})
                parent_group_id = parent_gitlab_config.get("group_id")
                
                if not parent_group_id:
                    result["error"] = "Parent course family missing GitLab group_id"
                    return result
                
                try:
                    parent_group = self.gitlab.groups.get(parent_group_id)
                except GitlabGetError as e:
                    result["error"] = f"Failed to retrieve parent group {parent_group_id}: {str(e)}"
                    return result
                
                # Validate GitLab group if properties exist
                if existing_course.properties and existing_course.properties.get("gitlab"):
                    gitlab_config = existing_course.properties["gitlab"]
                    if gitlab_config.get("group_id"):
                        is_valid = self._validate_gitlab_group(
                            gitlab_config["group_id"],
                            f"{parent_group.full_path}/{deployment.course.path}"
                        )
                        if not is_valid:
                            # Recreate GitLab group
                            gitlab_group, _ = self._create_gitlab_group(
                                deployment.course.name,
                                deployment.course.path,
                                parent_group_id,
                                deployment.course.description or "",
                                parent_group
                            )
                            result["gitlab_group"] = gitlab_group
                            result["gitlab_created"] = True
                            
                            # Create child-specific config WITHOUT token
                            gitlab_config = self._create_child_gitlab_config(gitlab_group)
                            
                            # Update properties
                            self._update_course_gitlab_properties(
                                existing_course,
                                gitlab_group,
                                gitlab_config
                            )
                        else:
                            result["gitlab_group"] = self.gitlab.groups.get(gitlab_config["group_id"])
                    else:
                        # Create GitLab group
                        gitlab_group, _ = self._create_gitlab_group(
                            deployment.course.name,
                            deployment.course.path,
                            parent_group_id,
                            deployment.course.description or "",
                            parent_group
                        )
                        result["gitlab_group"] = gitlab_group
                        result["gitlab_created"] = True
                        
                        # Create child-specific config WITHOUT token
                        gitlab_config = self._create_child_gitlab_config(gitlab_group)
                        
                        # Update properties
                        self._update_course_gitlab_properties(
                            existing_course,
                            gitlab_group,
                            gitlab_config
                        )
                else:
                    # Create GitLab group
                    gitlab_group, _ = self._create_gitlab_group(
                        deployment.course.name,
                        deployment.course.path,
                        parent_group_id,
                        deployment.course.description or "",
                        parent_group
                    )
                    result["gitlab_group"] = gitlab_group
                    result["gitlab_created"] = True
                    
                    # Create child-specific config WITHOUT token
                    gitlab_config = self._create_child_gitlab_config(gitlab_group)
                    
                    # Update properties
                    self._update_course_gitlab_properties(
                        existing_course,
                        gitlab_group,
                        gitlab_config
                    )
                
                # Ensure students group exists for existing course
                if result.get("gitlab_group"):
                    students_group_result = self._create_students_group(
                        course=existing_course,
                        parent_group=result["gitlab_group"],
                        deployment=deployment
                    )
                    
                    if not students_group_result["success"]:
                        logger.warning(f"Failed to create students group: {students_group_result['error']}")
                    else:
                        logger.info(f"Ensured students group exists: {students_group_result['gitlab_group'].full_path}")
                    
                    # Ensure tutors group exists for existing course
                    tutors_group_result = self._create_tutors_group(
                        course=existing_course,
                        parent_group=result["gitlab_group"],
                        deployment=deployment
                    )
                    
                    if not tutors_group_result["success"]:
                        logger.warning(f"Failed to create tutors group: {tutors_group_result['error']}")
                    else:
                        logger.info(f"Ensured tutors group exists: {tutors_group_result['gitlab_group'].full_path}")
                    
                    # Ensure course projects exist for existing course
                    projects_result = self._create_course_projects(
                        course=existing_course,
                        parent_group=result["gitlab_group"],
                        deployment=deployment
                    )
                    
                    if not projects_result["success"]:
                        logger.warning(f"Failed to create course projects: {projects_result['error']}")
                    else:
                        logger.info(f"Ensured course projects exist: {', '.join(projects_result['created_projects'])}")
                
                result["success"] = True
                return result
            
            # Create new course
            # Get parent GitLab group
            parent_gitlab_config = course_family.properties.get("gitlab", {})
            parent_group_id = parent_gitlab_config.get("group_id")
            
            if not parent_group_id:
                result["error"] = "Parent course family missing GitLab group_id"
                return result
            
            try:
                parent_group = self.gitlab.groups.get(parent_group_id)
            except GitlabGetError as e:
                result["error"] = f"Failed to retrieve parent group {parent_group_id}: {str(e)}"
                return result
            
            # Create GitLab group
            gitlab_group, _ = self._create_gitlab_group(
                deployment.course.name,
                deployment.course.path,
                parent_group_id,
                deployment.course.description or "",
                parent_group
            )
            result["gitlab_group"] = gitlab_group
            result["gitlab_created"] = True
            
            # Create child-specific config WITHOUT token
            gitlab_config = self._create_child_gitlab_config(gitlab_group)
            
            # Create course in database
            course_data = CourseCreate(
                title=deployment.course.name,
                description=deployment.course.description or "",
                path=deployment.course.path,
                course_family_id=str(course_family.id),
                properties=CourseProperties(gitlab=gitlab_config)
            )
            
            new_course = Course(
                title=course_data.title,
                description=course_data.description,
                path=Ltree(course_data.path),  # Convert to Ltree
                course_family_id=course_family.id,
                organization_id=organization.id,
                properties=course_data.properties.model_dump() if course_data.properties else {},
                created_by=created_by_user_id,
                updated_by=created_by_user_id
            )
            
            self.db.add(new_course)
            self.db.flush()  # Get the ID
            
            result["course"] = new_course
            result["db_created"] = True
            
            # Create students group under the course
            students_group_result = self._create_students_group(
                course=new_course,
                parent_group=gitlab_group,
                deployment=deployment
            )
            
            if not students_group_result["success"]:
                logger.warning(f"Failed to create students group: {students_group_result['error']}")
                # Don't fail the entire course creation, just log the warning
            else:
                logger.info(f"Created students group: {students_group_result['gitlab_group'].full_path}")
            
            # Create tutors group under the course
            tutors_group_result = self._create_tutors_group(
                course=new_course,
                parent_group=gitlab_group,
                deployment=deployment
            )
            
            if not tutors_group_result["success"]:
                logger.warning(f"Failed to create tutors group: {tutors_group_result['error']}")
                # Don't fail the entire course creation, just log the warning
            else:
                logger.info(f"Created tutors group: {tutors_group_result['gitlab_group'].full_path}")
            
            # Create course projects (assignments, student-template, reference)
            projects_result = self._create_course_projects(
                course=new_course,
                parent_group=gitlab_group,
                deployment=deployment
            )
            
            if not projects_result["success"]:
                logger.warning(f"Failed to create course projects: {projects_result['error']}")
                # Don't fail the entire course creation, just log the warning
            else:
                logger.info(f"Created course projects: {', '.join(projects_result['created_projects'])}")
            
            result["success"] = True
            
            logger.info(f"Created course: {new_course.path} (ID: {new_course.id})")
            
        except GitlabCreateError as e:
            logger.error(f"GitLab error creating course: {e}")
            result["error"] = f"GitLab error: {str(e)}"
        except IntegrityError as e:
            logger.error(f"Database integrity error creating course: {e}")
            result["error"] = f"Database integrity error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error creating course: {e}")
            result["error"] = f"Unexpected error: {str(e)}"
        
        return result
    
    def _create_gitlab_group(
        self,
        name: str,
        path: str,
        parent_id: Optional[int],
        description: str = "",
        parent_group: Optional[Group] = None
    ) -> Tuple[Group, Dict[str, Any]]:
        """
        Create or get GitLab group with enhanced metadata.
        
        Returns:
            Tuple of (Group, enhanced_config_dict)
        """
        # Construct full path
        if parent_group:
            full_path = f"{parent_group.full_path}/{path}"
        elif parent_id:
            logger.info(f"Looking up parent group with ID: {parent_id}")
            parent = self.gitlab.groups.get(parent_id)
            full_path = f"{parent.full_path}/{path}"
        else:
            full_path = path
        
        # Search for existing group
        try:
            groups = self.gitlab.groups.list(all=True)
            existing_groups = [g for g in groups if g.full_path == full_path]
            
            if existing_groups:
                group = self.gitlab.groups.get(existing_groups[0].id)
                logger.info(f"Found existing GitLab group: {group.full_path}")
                
                # Update description if needed
                if description and group.description != description:
                    group.description = description
                    group.save()
                
                # Return group with basic metadata (config will be created by caller)
                return group, {}
                
        except Exception as e:
            logger.warning(f"Error searching for group: {e}")
        
        # Create new group
        payload = {
            "path": path,
            "name": name,
            "description": description
        }
        
        if parent_id:
            payload["parent_id"] = parent_id
        
        try:
            logger.info(f"Creating GitLab group with payload: {payload}")
            group = self.gitlab.groups.create(payload)
            logger.info(f"Created new GitLab group: {group.full_path}")
            
            # Return group with basic metadata (config will be created by caller)
            return group, {}
            
        except GitlabCreateError as e:
            # Check if it's a duplicate error
            if "has already been taken" in str(e):
                # Try to find the existing group
                groups = self.gitlab.groups.list(all=True)
                existing_groups = [g for g in groups if g.full_path == full_path]
                if existing_groups:
                    group = self.gitlab.groups.get(existing_groups[0].id)
                    logger.info(f"Found existing GitLab group after create error: {group.full_path}")
                    return group, {}
            raise
    
    def _create_organization_gitlab_config(self, group: Group) -> Dict[str, Any]:
        """Create GitLab configuration for organization WITH encrypted token."""
        from ..interface.tokens import encrypt_api_key
        
        config = {
            "url": self.gitlab_url,
            "token": encrypt_api_key(self.gitlab_token),  # Only organizations get tokens
            "group_id": int(group.id) if group.id is not None else None,
            "full_path": group.full_path,
            "parent": int(group.parent_id) if group.parent_id is not None else None,
            "parent_id": int(group.parent_id) if group.parent_id is not None else None,
            "namespace_id": group.namespace.get('id') if hasattr(group, 'namespace') else None,
            "namespace_path": group.namespace.get('path') if hasattr(group, 'namespace') else None,
            "web_url": f"{self.gitlab_url}/groups/{group.full_path}",
            "visibility": group.visibility,
            "last_synced_at": datetime.now(timezone.utc).isoformat()
        }
        return config
    
    def _create_child_gitlab_config(self, group: Group) -> Dict[str, Any]:
        """Create GitLab configuration for course families and courses WITHOUT token."""
        config = {
            "url": self.gitlab_url,
            # NO TOKEN - course families and courses get token from parent organization
            "group_id": int(group.id) if group.id is not None else None,
            "full_path": group.full_path,
            "parent": int(group.parent_id) if group.parent_id is not None else None,
            "parent_id": int(group.parent_id) if group.parent_id is not None else None,
            "namespace_id": group.namespace.get('id') if hasattr(group, 'namespace') else None,
            "namespace_path": group.namespace.get('path') if hasattr(group, 'namespace') else None,
            "web_url": f"{self.gitlab_url}/groups/{group.full_path}",
            "visibility": group.visibility,
            "last_synced_at": datetime.now(timezone.utc).isoformat()
        }
        return config
    
    def _validate_gitlab_group(self, group_id: int, expected_path: str) -> bool:
        """Validate if GitLab group exists and matches expected path."""
        try:
            group = self.gitlab.groups.get(group_id)
            # Check if the group's path (not full_path) matches the expected path
            # This handles cases where the group is under a parent
            return group.path == expected_path
        except GitlabGetError:
            return False
        except Exception as e:
            logger.warning(f"Error validating GitLab group {group_id}: {e}")
            return False
    
    def _update_organization_gitlab_properties(
        self,
        organization: Organization,
        gitlab_group: Group,
        gitlab_config: Dict[str, Any]
    ):
        """Update organization with enhanced GitLab properties."""
        if not organization.properties:
            organization.properties = {}
        
        organization.properties["gitlab"] = gitlab_config
        flag_modified(organization, "properties")
        self.db.flush()
        
        # Refresh the object to ensure in-memory state matches database
        self.db.refresh(organization)
        
        logger.info(f"Updated organization {organization.path} with GitLab properties")
    
    def _update_course_family_gitlab_properties(
        self,
        course_family: CourseFamily,
        gitlab_group: Group,
        gitlab_config: Dict[str, Any]
    ):
        """Update course family with enhanced GitLab properties."""
        if not course_family.properties:
            course_family.properties = {}
        
        course_family.properties["gitlab"] = gitlab_config
        flag_modified(course_family, "properties")
        self.db.flush()
        
        # Refresh the object to ensure in-memory state matches database
        self.db.refresh(course_family)
        
        logger.info(f"Updated course family {course_family.path} with GitLab properties")
    
    def _update_course_gitlab_properties(
        self,
        course: Course,
        gitlab_group: Group,
        gitlab_config: Dict[str, Any]
    ):
        """Update course with enhanced GitLab properties."""
        if not course.properties:
            course.properties = {}
        
        course.properties["gitlab"] = gitlab_config
        flag_modified(course, "properties")
        self.db.flush()
        
        # Refresh the object to ensure in-memory state matches database
        self.db.refresh(course)
        
        logger.info(f"Updated course {course.path} with GitLab properties")
    
    def _create_students_group(
        self,
        course: Course,
        parent_group: Group,
        deployment: ComputorDeploymentConfig
    ) -> Dict[str, Any]:
        """Create students group under a course."""
        result = {
            "success": False,
            "gitlab_group": None,
            "error": None
        }
        
        try:
            # Check if students group already exists
            students_path = "students"
            full_path = f"{parent_group.full_path}/{students_path}"
            
            # Try to find existing students group
            existing_groups = parent_group.subgroups.list(search=students_path)
            students_group = None
            
            for group in existing_groups:
                if group.path == students_path:
                    students_group = self.gitlab.groups.get(group.id)
                    logger.info(f"Students group already exists: {students_group.full_path}")
                    result["gitlab_group"] = students_group
                    result["success"] = True
                    return result
            
            # Create students group
            group_data = {
                'name': 'Students',
                'path': students_path,
                'parent_id': parent_group.id,
                'description': f'Students group for {course.title}',
                'visibility': 'private'  # Students group should be private
            }
            
            students_group = self.gitlab.groups.create(group_data)
            logger.info(f"Created students group: {students_group.full_path}")
            
            # Update course properties to include students group info
            if not course.properties:
                course.properties = {}
            
            if "gitlab" not in course.properties:
                course.properties["gitlab"] = {}
            
            course.properties["gitlab"]["students_group"] = {
                "group_id": students_group.id,
                "full_path": students_group.full_path,
                "web_url": f"{self.gitlab_url}/groups/{students_group.full_path}",
                "created_at": datetime.now().isoformat()
            }
            
            flag_modified(course, "properties")
            self.db.flush()
            self.db.refresh(course)
            
            result["gitlab_group"] = students_group
            result["success"] = True
            
        except GitlabCreateError as e:
            logger.error(f"Failed to create students group: {e}")
            result["error"] = str(e)
        except Exception as e:
            logger.error(f"Unexpected error creating students group: {e}")
            result["error"] = str(e)
        
        return result
    
    def _create_tutors_group(
        self,
        course: Course,
        parent_group: Group,
        deployment: ComputorDeploymentConfig
    ) -> Dict[str, Any]:
        """Create tutors group under a course."""
        result = {
            "success": False,
            "gitlab_group": None,
            "error": None
        }
        
        try:
            # Check if tutors group already exists
            tutors_path = "tutors"
            full_path = f"{parent_group.full_path}/{tutors_path}"
            
            # Try to find existing tutors group
            existing_groups = parent_group.subgroups.list(search=tutors_path)
            tutors_group = None
            
            for group in existing_groups:
                if group.path == tutors_path:
                    tutors_group = self.gitlab.groups.get(group.id)
                    logger.info(f"Tutors group already exists: {tutors_group.full_path}")
                    result["gitlab_group"] = tutors_group
                    result["success"] = True
                    return result
            
            # Create tutors group
            group_data = {
                'name': 'Tutors',
                'path': tutors_path,
                'parent_id': parent_group.id,
                'description': f'Tutors group for {course.title}',
                'visibility': 'private'  # Tutors group should be private
            }
            
            tutors_group = self.gitlab.groups.create(group_data)
            logger.info(f"Created tutors group: {tutors_group.full_path}")
            
            # Update course properties to include tutors group info
            if not course.properties:
                course.properties = {}
            
            if "gitlab" not in course.properties:
                course.properties["gitlab"] = {}
            
            course.properties["gitlab"]["tutors_group"] = {
                "group_id": tutors_group.id,
                "full_path": tutors_group.full_path,
                "web_url": f"{self.gitlab_url}/groups/{tutors_group.full_path}",
                "created_at": datetime.now().isoformat()
            }
            
            flag_modified(course, "properties")
            self.db.flush()
            self.db.refresh(course)
            
            result["gitlab_group"] = tutors_group
            result["success"] = True
            
        except GitlabCreateError as e:
            logger.error(f"Failed to create tutors group: {e}")
            result["error"] = str(e)
        except Exception as e:
            logger.error(f"Unexpected error creating tutors group: {e}")
            result["error"] = str(e)
        
        return result
    
    def _create_course_projects(
        self,
        course: Course,
        parent_group: Group,
        deployment: ComputorDeploymentConfig
    ) -> Dict[str, Any]:
        """Create course projects (student-template and assignments) under a course.
        
        Creates:
        - student-template: Processed version for students (no solutions)
        - assignments: Full example content with solutions for lecturers/tutors (reference repository)
        """
        result = {
            "success": False,
            "created_projects": [],
            "existing_projects": [],
            "error": None
        }
        
        # Create both student-template and assignments repositories
        project_configs = [
            {
                "name": "Student Template",
                "path": "student-template",
                "description": f"Template repository for students in {course.title}",
                "visibility": "private"
            },
            {
                "name": "Assignments",
                "path": "assignments",
                "description": f"Reference repository with full example content for {course.title}",
                "visibility": "private"
            }
        ]
        
        try:
            for project_config in project_configs:
                project_path = project_config["path"]
                full_path = f"{parent_group.full_path}/{project_path}"
                
                # Check if project already exists
                existing_projects = self.gitlab.projects.list(
                    search=project_path,
                    namespace_id=parent_group.id
                )
                
                project_exists = False
                for existing in existing_projects:
                    # Handle namespace as dict or object
                    namespace_id = existing.namespace.get('id') if hasattr(existing.namespace, 'get') else existing.namespace.id
                    if existing.path == project_path and namespace_id == parent_group.id:
                        logger.info(f"Project already exists: {existing.path_with_namespace}")
                        result["existing_projects"].append(project_path)
                        project_exists = True
                        break
                
                if not project_exists:
                    # Create project
                    project_data = {
                        'name': project_config["name"],
                        'path': project_path,
                        'namespace_id': parent_group.id,
                        'description': project_config["description"],
                        'visibility': project_config["visibility"],
                        'initialize_with_readme': True,
                        'default_branch': 'main'
                    }
                    
                    project = self.gitlab.projects.create(project_data)
                    logger.info(f"Created project: {project.path_with_namespace}")
                    result["created_projects"].append(project_path)
            
            # Update course properties to include projects info
            if not course.properties:
                course.properties = {}
            
            if "gitlab" not in course.properties:
                course.properties["gitlab"] = {}
            
            course.properties["gitlab"]["projects"] = {
                "student_template": {
                    "path": "student-template",
                    "full_path": f"{parent_group.full_path}/student-template",
                    "web_url": f"{self.gitlab_url}/{parent_group.full_path}/student-template",
                    "description": "Template repository for students"
                },
                "assignments": {
                    "path": "assignments",
                    "full_path": f"{parent_group.full_path}/assignments",
                    "web_url": f"{self.gitlab_url}/{parent_group.full_path}/assignments",
                    "description": "Reference repository with full example content"
                },
                "created_at": datetime.now().isoformat()
            }
            
            # Store URLs at the top level for easy access
            course.properties["gitlab"]["student_template_url"] = f"{self.gitlab_url}/{parent_group.full_path}/student-template"
            course.properties["gitlab"]["assignments_url"] = f"{self.gitlab_url}/{parent_group.full_path}/assignments"
            
            # Tell SQLAlchemy that the properties field has been modified
            flag_modified(course, "properties")
            
            self.db.flush()
            self.db.refresh(course)
            
            result["success"] = True
            
        except Exception as e:
            logger.error(f"Failed to create course projects: {e}")
            result["error"] = str(e)
        
        return result
    
    def add_member_to_group(
        self,
        group_id: int,
        user_id: int,
        access_level: int = 30  # Developer access by default
    ) -> Dict[str, Any]:
        """Add a member to a GitLab group.
        
        Access levels:
        - 10: Guest
        - 20: Reporter  
        - 30: Developer
        - 40: Maintainer
        - 50: Owner
        """
        result = {
            "success": False,
            "member": None,
            "error": None
        }
        
        try:
            group = self.gitlab.groups.get(group_id)
            member = group.members.create({
                'user_id': user_id,
                'access_level': access_level
            })
            
            logger.info(f"Added user {user_id} to group {group.full_path} with access level {access_level}")
            
            result["member"] = member
            result["success"] = True
            
        except GitlabCreateError as e:
            if "Member already exists" in str(e):
                logger.warning(f"User {user_id} is already a member of group {group_id}")
                result["error"] = "Member already exists"
                # Still consider this a success
                result["success"] = True
            else:
                logger.error(f"Failed to add member to group: {e}")
                result["error"] = str(e)
        except Exception as e:
            logger.error(f"Unexpected error adding member to group: {e}")
            result["error"] = str(e)
        
        return result
    
    def remove_member_from_group(
        self,
        group_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """Remove a member from a GitLab group."""
        result = {
            "success": False,
            "error": None
        }
        
        try:
            group = self.gitlab.groups.get(group_id)
            group.members.delete(user_id)
            
            logger.info(f"Removed user {user_id} from group {group.full_path}")
            
            result["success"] = True
            
        except GitlabDeleteError as e:
            logger.error(f"Failed to remove member from group: {e}")
            result["error"] = str(e)
        except Exception as e:
            logger.error(f"Unexpected error removing member from group: {e}")
            result["error"] = str(e)
        
        return result
    
    def add_student_to_course(
        self,
        course: Course,
        gitlab_user_id: int
    ) -> Dict[str, Any]:
        """Add a student to a course by adding them to the students group."""
        result = {
            "success": False,
            "error": None
        }
        
        try:
            # Get students group info from course properties
            if not course.properties or not course.properties.get("gitlab", {}).get("students_group"):
                result["error"] = "Course does not have a students group configured"
                return result
            
            students_group_id = course.properties["gitlab"]["students_group"]["group_id"]
            
            # Add member to students group with Developer access
            add_result = self.add_member_to_group(
                group_id=students_group_id,
                user_id=gitlab_user_id,
                access_level=30  # Developer access for students
            )
            
            if add_result["success"]:
                logger.info(f"Added student {gitlab_user_id} to course {course.path}")
                result["success"] = True
            else:
                result["error"] = add_result["error"]
            
        except Exception as e:
            logger.error(f"Error adding student to course: {e}")
            result["error"] = str(e)
        
        return result
    
    def add_lecturer_to_course(
        self,
        course: Course,
        gitlab_user_id: int
    ) -> Dict[str, Any]:
        """Add a lecturer to a course by adding them to the main course group."""
        result = {
            "success": False,
            "error": None
        }
        
        try:
            # Get course group info from properties
            if not course.properties or not course.properties.get("gitlab", {}).get("group_id"):
                result["error"] = "Course does not have a GitLab group configured"
                return result
            
            course_group_id = course.properties["gitlab"]["group_id"]
            
            # Add member to course group with Maintainer access
            add_result = self.add_member_to_group(
                group_id=course_group_id,
                user_id=gitlab_user_id,
                access_level=40  # Maintainer access for lecturers
            )
            
            if add_result["success"]:
                logger.info(f"Added lecturer {gitlab_user_id} to course {course.path}")
                result["success"] = True
            else:
                result["error"] = add_result["error"]
            
        except Exception as e:
            logger.error(f"Error adding lecturer to course: {e}")
            result["error"] = str(e)
        
        return result
    
    def initialize_course_projects_content(
        self,
        course: Course,
        deployment: ComputorDeploymentConfig
    ) -> Dict[str, Any]:
        """Initialize course project (student-template only) with proper content structure."""
        result = {
            "success": False,
            "initialized_projects": [],
            "error": None
        }
        
        try:
            # Get course GitLab properties
            gitlab_props = course.properties.get("gitlab", {})
            projects = gitlab_props.get("projects", {})
            
            if not projects:
                result["error"] = "Course has no GitLab projects configured"
                return result
            
            # Only initialize student-template project
            if "student_template" in projects:
                template_result = self._initialize_student_template_project(
                    course, projects["student_template"], deployment
                )
                if template_result["success"]:
                    result["initialized_projects"].append("student-template")
                else:
                    logger.warning(f"Failed to initialize student-template project: {template_result['error']}")
            
            result["success"] = len(result["initialized_projects"]) > 0
            
        except Exception as e:
            logger.error(f"Failed to initialize course projects content: {e}")
            result["error"] = str(e)
        
        return result
    
    # ===== DEPRECATED METHODS =====
    # The following methods are no longer needed with the Example Library paradigm.
    # Assignments and reference repositories are obsolete - examples are stored in MinIO
    # and deployed directly to student-template repositories.
    # These methods are kept for reference but should not be used.
    
    def _initialize_assignments_project(
        self,
        course: Course,
        project_info: Dict[str, Any],
        deployment: ComputorDeploymentConfig
    ) -> Dict[str, Any]:
        """Initialize assignments project with proper structure and meta.yaml."""

        raise NotImplementedException()
    
    def _initialize_student_template_project(
        self,
        course: Course,
        project_info: Dict[str, Any],
        deployment: ComputorDeploymentConfig
    ) -> Dict[str, Any]:
        """Initialize student template project with basic structure."""
        result = {"success": False, "error": None}
        
        try:
            # For now, we'll create the structure locally and then describe what would be pushed
            with tempfile.TemporaryDirectory() as temp_dir:
                repo_path = os.path.join(temp_dir, "student-template")
                os.makedirs(repo_path, exist_ok=True)
                
                # Create student template structure
                assignments_dir = os.path.join(repo_path, "assignments")
                os.makedirs(assignments_dir, exist_ok=True)
                
                # Create project README
                readme_path = os.path.join(repo_path, "README.md")
                if not os.path.exists(readme_path):
                    with open(readme_path, 'w') as f:
                        f.write(f"# {course.title} - Student Repository\n\n")
                        f.write(f"Welcome to {course.title}!\n\n")
                        f.write(f"This is your personal repository for course assignments.\n\n")
                        f.write(f"## Getting Started\n\n")
                        f.write(f"1. Clone this repository to your local machine\n")
                        f.write(f"2. Complete assignments in the `assignments/` directory\n")
                        f.write(f"3. Commit and push your solutions\n\n")
                        f.write(f"## Structure\n\n")
                        f.write(f"- `assignments/`: Your assignment solutions go here\n")
                        f.write(f"- Each assignment should be in its own subdirectory\n")
                
                # Create assignments README
                assignments_readme = os.path.join(assignments_dir, "README.md")
                with open(assignments_readme, 'w') as f:
                    f.write(f"# Assignments\n\n")
                    f.write(f"This directory contains your assignment solutions.\n\n")
                    f.write(f"Create a new directory for each assignment and put your solution files there.\n")
                
                # Create .gitignore for common development files
                gitignore_path = os.path.join(repo_path, ".gitignore")
                if not os.path.exists(gitignore_path):
                    with open(gitignore_path, 'w') as f:
                        f.write("# IDE files\n")
                        f.write(".vscode/\n")
                        f.write(".idea/\n")
                        f.write("*.swp\n")
                        f.write("*.swo\n")
                        f.write("\n# OS files\n")
                        f.write(".DS_Store\n")
                        f.write("Thumbs.db\n")
                        f.write("\n# Build artifacts\n")
                        f.write("*.o\n")
                        f.write("*.exe\n")
                        f.write("__pycache__/\n")
                        f.write("*.pyc\n")
                
                # Note: In full implementation, would commit and push:
                # - git add .
                # - git commit -m "Initialize student template with basic structure"
                # - git push origin main
                
                result["success"] = True
                logger.info(f"Initialized student template project for course {course.path}")
                
        except Exception as e:
            logger.error(f"Failed to initialize student template project: {e}")
            result["error"] = str(e)
        
        return result
    
    def _initialize_reference_project(
        self,
        course: Course,
        project_info: Dict[str, Any],
        deployment: ComputorDeploymentConfig
    ) -> Dict[str, Any]:
        """Initialize reference project with instructor materials."""
        result = {"success": False, "error": None}
        
        try:
            # For now, we'll create the structure locally and then describe what would be pushed
            with tempfile.TemporaryDirectory() as temp_dir:
                repo_path = os.path.join(temp_dir, "reference")
                os.makedirs(repo_path, exist_ok=True)
                
                # Create reference structure
                solutions_dir = os.path.join(repo_path, "solutions")
                grading_dir = os.path.join(repo_path, "grading")
                materials_dir = os.path.join(repo_path, "materials")
                
                os.makedirs(solutions_dir, exist_ok=True)
                os.makedirs(grading_dir, exist_ok=True)
                os.makedirs(materials_dir, exist_ok=True)
                
                # Create project README
                readme_path = os.path.join(repo_path, "README.md")
                if not os.path.exists(readme_path):
                    with open(readme_path, 'w') as f:
                        f.write(f"# {course.title} - Reference Materials\n\n")
                        f.write(f"This repository contains instructor reference materials for {course.title}.\n\n")
                        f.write(f"## Structure\n\n")
                        f.write(f"- `solutions/`: Reference solutions for assignments\n")
                        f.write(f"- `grading/`: Grading scripts and rubrics\n")
                        f.write(f"- `materials/`: Additional course materials and resources\n")
                        f.write(f"\n**Note**: This repository contains sensitive instructor materials. Keep access restricted.\n")
                
                # Create structure READMEs
                for dir_path, dir_name, description in [
                    (solutions_dir, "Solutions", "Reference solutions for course assignments"),
                    (grading_dir, "Grading", "Automated grading scripts and rubrics"),
                    (materials_dir, "Materials", "Additional course materials and resources")
                ]:
                    dir_readme = os.path.join(dir_path, "README.md")
                    with open(dir_readme, 'w') as f:
                        f.write(f"# {dir_name}\n\n")
                        f.write(f"{description}.\n\n")
                        f.write(f"Add files and subdirectories as needed for course content.\n")
                
                # Note: In full implementation, would commit and push:
                # - git add .
                # - git commit -m "Initialize reference project with instructor materials structure"
                # - git push origin main
                
                result["success"] = True
                logger.info(f"Initialized reference project for course {course.path}")
                
        except Exception as e:
            logger.error(f"Failed to initialize reference project: {e}")
            result["error"] = str(e)
        
        return result
    
    # END OF DEPRECATED METHODS