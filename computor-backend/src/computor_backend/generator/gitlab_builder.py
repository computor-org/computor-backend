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
        
        # Docker-aware client on a stable base URL
        from ..git_provider.gitlab import make_gitlab_client
        from ..utils.docker_utils import transform_localhost_url
        api_url = transform_localhost_url(gitlab_url)  # kept for log messages below

        self.gitlab = make_gitlab_client(gitlab_url, gitlab_token)
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
                # Course-group-only model: never create/validate a GitLab group for
                # the org. Refresh the recorded connection + hand-made parent, return.
                from computor_backend.utils.encryption import encrypt_secret
                from sqlalchemy.orm.attributes import flag_modified
                props = existing_org.properties or {}
                props["gitlab"] = {
                    **(props.get("gitlab") or {}),
                    "url": self.gitlab_url,
                    "token": encrypt_secret(self.gitlab_token),
                    "parent": org_config.gitlab.parent,
                }
                existing_org.properties = props
                flag_modified(existing_org, "properties")
                self.db.flush()
                result["success"] = True
                return result
            
            # Create new organization (DB only).
            # Course-group-only model: we DO NOT create a GitLab group for the
            # organization — the lecturer builds the org/family group structure by
            # hand. We only record the connection (url + token) and the hand-made
            # ``parent`` group under which course groups are created (_create_course).
            from computor_backend.utils.encryption import encrypt_secret
            logger.info(
                "Skipping GitLab org group creation (course-group-only model); "
                "recording hand-made parent group %s", org_config.gitlab.parent,
            )
            gitlab_config = {
                "url": self.gitlab_url,
                "token": encrypt_secret(self.gitlab_token),
                "parent": org_config.gitlab.parent,
                "last_synced_at": datetime.now(timezone.utc).isoformat(),
            }
            
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
                # Course-group-only model: no GitLab subgroup for the family.
                result["success"] = True
                return result
            
            # Create new course family (DB only).
            # Course-group-only model: no GitLab subgroup is created for the
            # course family — the lecturer owns the group structure by hand.
            logger.info("Skipping GitLab course-family group creation (course-group-only model)")
            gitlab_config = {"url": self.gitlab_url}

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
                
                # Course group lives under the organization's hand-made parent.
                parent_gitlab_config = organization.properties.get("gitlab", {})
                parent_group_id = parent_gitlab_config.get("parent")

                if not parent_group_id:
                    result["error"] = "Organization missing GitLab parent group (gitlab.parent)"
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
                            gitlab_config = self._build_gitlab_config(gitlab_group)
                            
                            # Update properties
                            self._set_gitlab_properties(existing_course, gitlab_config)
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
                        gitlab_config = self._build_gitlab_config(gitlab_group)
                        
                        # Update properties
                        self._set_gitlab_properties(existing_course, gitlab_config)
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
                    gitlab_config = self._build_gitlab_config(gitlab_group)
                    
                    # Update properties
                    self._set_gitlab_properties(existing_course, gitlab_config)
                
                # Ensure students group exists for existing course
                if result.get("gitlab_group"):
                    students_group_result = self._ensure_subgroup(existing_course, result["gitlab_group"], "students", "Students", "students_group")
                    
                    if not students_group_result["success"]:
                        logger.warning(f"Failed to create students group: {students_group_result['error']}")
                    else:
                        logger.info(f"Ensured students group exists: {students_group_result['gitlab_group'].full_path}")
                    
                    # Ensure tutors group exists for existing course
                    tutors_group_result = self._ensure_subgroup(existing_course, result["gitlab_group"], "tutors", "Tutors", "tutors_group")
                    
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
            # Course-group-only model: the course group is created directly under
            # the organization's hand-made *parent* group (we no longer create
            # org/family groups). The lecturer records it as org.properties.gitlab.parent.
            parent_gitlab_config = organization.properties.get("gitlab", {})
            parent_group_id = parent_gitlab_config.get("parent")

            if not parent_group_id:
                result["error"] = "Organization missing GitLab parent group (gitlab.parent)"
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
            gitlab_config = self._build_gitlab_config(gitlab_group)
            
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
            students_group_result = self._ensure_subgroup(new_course, gitlab_group, "students", "Students", "students_group")

            if not students_group_result["success"]:
                logger.warning(f"Failed to create students group: {students_group_result['error']}")
                # Don't fail the entire course creation, just log the warning
            else:
                logger.info(f"Created students group: {students_group_result['gitlab_group'].full_path}")

            # Create tutors group under the course
            tutors_group_result = self._ensure_subgroup(new_course, gitlab_group, "tutors", "Tutors", "tutors_group")

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
    
    def _build_gitlab_config(self, group: Group, include_token: bool = False) -> Dict[str, Any]:
        """GitLab connection config for a group. Only organizations carry a
        token (course families/courses inherit it from the parent org)."""
        config = {
            "url": self.gitlab_url,
            "group_id": int(group.id) if group.id is not None else None,
            "full_path": group.full_path,
            "parent": int(group.parent_id) if group.parent_id is not None else None,
            "parent_id": int(group.parent_id) if group.parent_id is not None else None,
            "namespace_id": group.namespace.get('id') if hasattr(group, 'namespace') else None,
            "namespace_path": group.namespace.get('path') if hasattr(group, 'namespace') else None,
            "web_url": f"{self.gitlab_url}/groups/{group.full_path}",
            "visibility": group.visibility,
            "last_synced_at": datetime.now(timezone.utc).isoformat(),
        }
        if include_token:
            from computor_backend.utils.encryption import encrypt_secret
            config["token"] = encrypt_secret(self.gitlab_token)
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

    def _set_gitlab_properties(self, entity, gitlab_config: Dict[str, Any]):
        """Write the gitlab config block onto any hierarchy entity's properties."""
        if not entity.properties:
            entity.properties = {}
        entity.properties["gitlab"] = gitlab_config
        flag_modified(entity, "properties")
        self.db.flush()
        self.db.refresh(entity)
        logger.info(f"Updated {type(entity).__name__} {entity.path} with GitLab properties")
    
    def _ensure_subgroup(
        self,
        course: Course,
        parent_group: Group,
        path: str,
        name: str,
        prop_key: str,
    ) -> Dict[str, Any]:
        """Idempotently create a ``path`` subgroup (e.g. students/tutors) under a
        course group, recording it on ``course.properties['gitlab'][prop_key]``."""
        result = {"success": False, "gitlab_group": None, "error": None}

        try:
            existing_groups = parent_group.subgroups.list(search=path)
            for group in existing_groups:
                if group.path == path:
                    subgroup = self.gitlab.groups.get(group.id)
                    logger.info(f"{name} group already exists: {subgroup.full_path}")
                    result["gitlab_group"] = subgroup
                    result["success"] = True
                    return result

            subgroup = self.gitlab.groups.create({
                'name': name,
                'path': path,
                'parent_id': parent_group.id,
                'description': f'{name} group for {course.title}',
                'visibility': 'private',
            })
            logger.info(f"Created {name.lower()} group: {subgroup.full_path}")

            if not course.properties:
                course.properties = {}
            if "gitlab" not in course.properties:
                course.properties["gitlab"] = {}
            course.properties["gitlab"][prop_key] = {
                "group_id": subgroup.id,
                "full_path": subgroup.full_path,
                "web_url": f"{self.gitlab_url}/groups/{subgroup.full_path}",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            flag_modified(course, "properties")
            self.db.flush()
            self.db.refresh(course)

            result["gitlab_group"] = subgroup
            result["success"] = True
        except GitlabCreateError as e:
            logger.error(f"Failed to create {name.lower()} group: {e}")
            result["error"] = str(e)
        except Exception as e:
            logger.error(f"Unexpected error creating {name.lower()} group: {e}")
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
        
        # Create the template + reference repositories. The names are the current
        # defaults; existing courses keep whatever names are stored in their
        # ``properties.gitlab.projects`` (consumers read the stored full_path/url).
        project_configs = [
            {
                "name": "Template",
                "path": "template",
                "description": f"Template repository for students in {course.title}",
                "visibility": "private"
            },
            {
                "name": "Reference",
                "path": "reference",
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
            
            # The ``student_template`` / ``assignments`` keys are role slots
            # (kept for back-compat with existing consumers); the stored path/url
            # values carry the actual repo names — now ``template`` / ``reference``.
            course.properties["gitlab"]["projects"] = {
                "student_template": {
                    "path": "template",
                    "full_path": f"{parent_group.full_path}/template",
                    "web_url": f"{self.gitlab_url}/{parent_group.full_path}/template",
                    "description": "Template repository for students"
                },
                "assignments": {
                    "path": "reference",
                    "full_path": f"{parent_group.full_path}/reference",
                    "web_url": f"{self.gitlab_url}/{parent_group.full_path}/reference",
                    "description": "Reference repository with full example content"
                },
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            # Store URLs at the top level for easy access
            course.properties["gitlab"]["student_template_url"] = f"{self.gitlab_url}/{parent_group.full_path}/template"
            course.properties["gitlab"]["assignments_url"] = f"{self.gitlab_url}/{parent_group.full_path}/reference"
            
            # Tell SQLAlchemy that the properties field has been modified
            flag_modified(course, "properties")
            
            self.db.flush()
            self.db.refresh(course)
            
            result["success"] = True
            
        except Exception as e:
            logger.error(f"Failed to create course projects: {e}")
            result["error"] = str(e)
        
        return result