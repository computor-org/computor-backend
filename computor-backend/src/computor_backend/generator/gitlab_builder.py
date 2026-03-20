"""
GitLab builder with integrated database operations and property storage.

Creates GitLab groups for the organization/course-family/course hierarchy
and stores the corresponding metadata in database properties.
Used by Temporal activities in temporal_hierarchy_management.py.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
from gitlab import Gitlab
from gitlab.v4.objects import Group
from gitlab.exceptions import GitlabCreateError, GitlabGetError
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.attributes import flag_modified

from computor_types.gitlab import GitLabConfig
from computor_types.deployments_refactored import (
    OrganizationConfig,
    CourseFamilyConfig,
    CourseConfig,
)
from computor_types.organizations import (
    OrganizationCreate,
    OrganizationProperties
)
from computor_types.course_families import (
    CourseFamilyCreate,
    CourseFamilyProperties
)
from computor_types.courses import (
    CourseCreate,
    CourseProperties
)
from computor_backend.model.organization import Organization
from computor_backend.model.course import CourseFamily, Course
from computor_backend.repositories.organization import OrganizationRepository
from ..custom_types import Ltree


logger = logging.getLogger(__name__)


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
    ):
        """
        Initialize the GitLab builder.

        Args:
            db_session: SQLAlchemy database session
            gitlab_url: GitLab instance URL
            gitlab_token: GitLab access token
        """
        self.db = db_session
        self.gitlab_url = gitlab_url  # Store original URL for database
        self.gitlab_token = gitlab_token
        
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

    def _create_organization(
        self,
        org_config: OrganizationConfig,
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
            logger.info(f"Creating organization with path: {org_config.path}")
            # Check if organization already exists in database
            existing_org = self.org_repo.find_by_path(org_config.path)
            
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
                            org_config.path
                        )
                        if not is_valid:
                            # Need to recreate GitLab group
                            logger.warning(f"GitLab group for organization {existing_org.path} no longer exists")
                            gitlab_group, _ = self._create_gitlab_group(
                                org_config.name,
                                org_config.path,
                                org_config.gitlab.parent,
                                org_config.description or ""
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
                            org_config.name,
                            org_config.path,
                            org_config.gitlab.parent,
                            org_config.description or ""
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
                        org_config.name,
                        org_config.path,
                        org_config.gitlab.parent,
                        org_config.description or ""
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
            logger.info(f"Creating new organization GitLab group with parent: {org_config.gitlab.parent}")
            gitlab_group, _ = self._create_gitlab_group(
                org_config.name,
                org_config.path,
                org_config.gitlab.parent,
                org_config.description or ""
            )
            result["gitlab_group"] = gitlab_group
            result["gitlab_created"] = True
            
            # Create organization-specific config with encrypted token
            gitlab_config = self._create_organization_gitlab_config(gitlab_group)
            
            # Create organization in database
            logger.info(f"Creating organization with gitlab_config: {gitlab_config}")
            org_data = OrganizationCreate(
                title=org_config.name,
                description=org_config.description,
                path=org_config.path,
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
        family_config: CourseFamilyConfig,
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
                CourseFamily.path == Ltree(family_config.path)
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
                            f"{parent_group.full_path}/{family_config.path}"
                        )
                        if not is_valid:
                            # Recreate GitLab group
                            gitlab_group, _ = self._create_gitlab_group(
                                family_config.name,
                                family_config.path,
                                parent_group_id,
                                family_config.description or "",
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
                            family_config.name,
                            family_config.path,
                            parent_group_id,
                            family_config.description or "",
                            parent_group
                        )
                        result["gitlab_group"] = gitlab_group
                        result["gitlab_created"] = True

                        # Create documents repository if group was just created
                        logger.info(f"Creating documents repository for course family group {gitlab_group.id}")
                        self._create_documents_repository(gitlab_group.id)

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
                        family_config.name,
                        family_config.path,
                        parent_group_id,
                        family_config.description or "",
                        parent_group
                    )
                    result["gitlab_group"] = gitlab_group
                    result["gitlab_created"] = True

                    # Create documents repository if group was just created
                    logger.info(f"Creating documents repository for course family group {gitlab_group.id}")
                    self._create_documents_repository(gitlab_group.id)

                    # Create child-specific config WITHOUT token
                    gitlab_config = self._create_child_gitlab_config(gitlab_group)

                    # Update properties
                    self._update_course_family_gitlab_properties(
                        existing_family,
                        gitlab_group,
                        gitlab_config
                    )

                # Ensure documents repository exists (even if group already existed)
                if result.get("gitlab_group"):
                    group_id = result["gitlab_group"].id
                    logger.info(f"Ensuring documents repository exists for group {group_id}")
                    self._create_documents_repository(group_id)
                
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
                family_config.name,
                family_config.path,
                parent_group_id,
                family_config.description or "",
                parent_group
            )
            result["gitlab_group"] = gitlab_group
            result["gitlab_created"] = True

            # Create documents repository in the course family group
            logger.info(f"Creating documents repository for course family group {gitlab_group.id}")
            docs_created = self._create_documents_repository(gitlab_group.id)
            if docs_created:
                logger.info("Documents repository created successfully")
            else:
                logger.warning("Failed to create documents repository, but continuing...")

            # Create child-specific config WITHOUT token
            gitlab_config = self._create_child_gitlab_config(gitlab_group)

            # Create course family in database
            family_data = CourseFamilyCreate(
                title=family_config.name,
                description=family_config.description or "",
                path=family_config.path,
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
        course_config: CourseConfig,
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
                Course.path == Ltree(course_config.path)
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
                            f"{parent_group.full_path}/{course_config.path}"
                        )
                        if not is_valid:
                            # Recreate GitLab group
                            gitlab_group, _ = self._create_gitlab_group(
                                course_config.name,
                                course_config.path,
                                parent_group_id,
                                course_config.description or "",
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
                            course_config.name,
                            course_config.path,
                            parent_group_id,
                            course_config.description or "",
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
                        course_config.name,
                        course_config.path,
                        parent_group_id,
                        course_config.description or "",
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
                        )
                    
                    if not students_group_result["success"]:
                        logger.warning(f"Failed to create students group: {students_group_result['error']}")
                    else:
                        logger.info(f"Ensured students group exists: {students_group_result['gitlab_group'].full_path}")
                    
                    # Ensure tutors group exists for existing course
                    tutors_group_result = self._create_tutors_group(
                        course=existing_course,
                        parent_group=result["gitlab_group"],
                        )
                    
                    if not tutors_group_result["success"]:
                        logger.warning(f"Failed to create tutors group: {tutors_group_result['error']}")
                    else:
                        logger.info(f"Ensured tutors group exists: {tutors_group_result['gitlab_group'].full_path}")
                    
                    # Ensure course projects exist for existing course
                    projects_result = self._create_course_projects(
                        course=existing_course,
                        parent_group=result["gitlab_group"],
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
                course_config.name,
                course_config.path,
                parent_group_id,
                course_config.description or "",
                parent_group
            )
            result["gitlab_group"] = gitlab_group
            result["gitlab_created"] = True
            
            # Create child-specific config WITHOUT token
            gitlab_config = self._create_child_gitlab_config(gitlab_group)
            
            # Create course in database
            course_data = CourseCreate(
                title=course_config.name,
                description=course_config.description or "",
                path=course_config.path,
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
        from computor_types.tokens import encrypt_api_key
        
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

    def _create_documents_repository(self, course_family_group_id: int) -> bool:
        """
        Create a documents repository in the course family's GitLab group.

        Args:
            course_family_group_id: GitLab group ID of the course family

        Returns:
            True if repository was created or already exists, False on error
        """
        try:
            # Get the course family group
            try:
                group = self.gitlab.groups.get(course_family_group_id)
            except GitlabGetError as e:
                logger.error(f"Failed to get GitLab group {course_family_group_id}: {e}")
                return False

            # Check if documents repository already exists
            repo_path = f"{group.full_path}/documents"
            project = None
            repo_already_exists = False

            try:
                # Try to get the repository
                project = self.gitlab.projects.get(repo_path.replace('/', '%2F'))
                logger.info(f"Documents repository already exists: {repo_path}")
                repo_already_exists = True
            except GitlabGetError:
                # Repository doesn't exist, create it
                pass

            # If repository already exists, check if README exists before creating
            if repo_already_exists and project:
                try:
                    # Try to get README.md
                    project.files.get(file_path='README.md', ref='main')
                    logger.info(f"README.md already exists in documents repository")
                    return True  # Repository and README both exist, nothing to do
                except Exception:
                    # README doesn't exist, we'll create it below
                    logger.info(f"README.md does not exist, will create it")
                    pass

            # Create documents repository only if it doesn't exist
            if not repo_already_exists:
                logger.info(f"Creating documents repository in group: {group.full_path}")
            else:
                logger.info(f"Repository exists, will add README if missing")

            readme_content = """# Documents Repository

This repository contains course materials and lecture documents for students.

## Purpose

This is the central location for:
- Lecture slides and notes
- Course syllabus and schedules
- Reading materials and references
- Assignment descriptions
- Additional learning resources

## Organization

Organize your materials in subdirectories by topic, week, or module as needed.

## Access

Documents are automatically synchronized and made available to students through the course platform.

---
*This repository is automatically managed by the Computor platform.*
"""

            # Only create repository if it doesn't exist
            if not repo_already_exists:
                project_data = {
                    'name': 'Documents',
                    'path': 'documents',
                    'namespace_id': course_family_group_id,
                    'description': 'Course materials and lecture documents',
                    'visibility': 'private',
                    'initialize_with_readme': False,  # We'll add our own README
                }

                project = self.gitlab.projects.create(project_data)
                logger.info(f"Created documents repository: {project.path_with_namespace}")

            # Create and commit README.md only if repository was just created or README is missing
            if project:
                try:
                    file_data = {
                        'file_path': 'README.md',
                        'branch': 'main',
                        'content': readme_content,
                        'commit_message': 'Initial commit: Add README' if not repo_already_exists else 'Add README.md'
                    }
                    project.files.create(file_data)
                    logger.info(f"Added README.md to documents repository")
                except Exception as e:
                    # This will fail if README already exists, which is fine
                    logger.debug(f"README.md creation skipped or failed (may already exist): {e}")

            return True

        except GitlabCreateError as e:
            if "has already been taken" in str(e):
                logger.info(f"Documents repository already exists (conflict during creation)")
                return True
            logger.error(f"GitLab error creating documents repository: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating documents repository: {e}")
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
                "created_at": datetime.now(timezone.utc).isoformat()
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
                "created_at": datetime.now(timezone.utc).isoformat()
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
                "created_at": datetime.now(timezone.utc).isoformat()
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