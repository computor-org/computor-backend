"""
Temporal activity and workflow to generate the assignments repository from Example Library.

This activity clones (or initializes) the assignments repository and, for selected
course contents that have an ExampleVersion assigned, copies the full example files
unmodified into the repository under the assignment directory. After committing and
pushing, it records the HEAD commit SHA into CourseContentDeployment.version_identifier
and ensures CourseContentDeployment.deployment_path is set.
"""
from datetime import timedelta, datetime, timezone
from typing import Any, Dict, List, Optional
import os
import tempfile
import shutil
from pathlib import Path

from temporalio import workflow, activity
from temporalio.common import RetryPolicy

from .temporal_base import BaseWorkflow, WorkflowResult
from .registry import register_task


@activity.defn(name="generate_assignments_repository")
async def generate_assignments_repository_activity(
    course_id: str,
    assignments_url: Optional[str] = None,
    selection: Optional[Dict[str, Any]] = None,
    overwrite_strategy: str = "skip_if_exists",
    commit_message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Populate the assignments repository from Example Library for selected contents.

    Args:
        course_id: Course ID
        assignments_url: Git URL for assignments repo (derived from course if None)
        selection: {course_content_ids|parent_id+include_descendants|all}
        overwrite_strategy: 'skip_if_exists' or 'force_update'
        commit_message: optional commit message
    """
    import git
    from sqlalchemy.orm import joinedload
    from sqlalchemy import and_
    from ..database import get_db
    from ..model.course import Course, CourseContent
    from ..model.deployment import CourseContentDeployment, DeploymentHistory
    from ..model.example import ExampleVersion, Example
    from ..utils.docker_utils import transform_localhost_url
    from ..tasks.temporal_student_template_v2 import download_example_files

    db_gen = next(get_db())
    db = db_gen

    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return {"success": False, "error": f"Course {course_id} not found"}

        org = course.organization
        gitlab_token = None
        if org and org.properties and 'gitlab' in org.properties:
            from ..interface.tokens import decrypt_api_key
            enc = org.properties['gitlab'].get('token')
            if enc:
                try:
                    gitlab_token = decrypt_api_key(enc)
                except Exception:
                    gitlab_token = None

        # Determine assignments URL if not provided
        if not assignments_url:
            course_props = course.properties or {}
            course_gitlab = course_props.get('gitlab', {})
            provider = (org.properties or {}).get('gitlab', {}).get('url') if org and org.properties else None
            full_path_course = course_gitlab.get('full_path')
            if provider and full_path_course:
                assignments_url = f"{provider}/{full_path_course}/assignments.git"
            else:
                return {"success": False, "error": "assignments_url not provided and cannot be derived"}

        assignments_url = transform_localhost_url(assignments_url)

        # Selection of contents
        selected_ids: List[str] = []
        if selection:
            ids = selection.get('course_content_ids') or []
            if ids:
                selected_ids = ids
            elif selection.get('parent_id'):
                parent_id = selection.get('parent_id')
                include_desc = bool(selection.get('include_descendants', True))
                parent = db.query(CourseContent).filter(CourseContent.id == parent_id).first()
                if parent:
                    q = db.query(CourseContent).filter(CourseContent.course_id == course_id)
                    if include_desc:
                        q = q.filter(CourseContent.path.descendant_of(parent.path))
                    else:
                        q = q.filter(CourseContent.id == parent.id)
                    selected_ids = [str(cc.id) for cc in q.all()]
            elif selection.get('all'):
                selected_ids = [str(cid) for (cid,) in db.query(CourseContent.id).filter(CourseContent.course_id == course_id).all()]

        # Fetch contents with deployments/example versions
        if selected_ids:
            contents = db.query(CourseContent).options(
                joinedload(CourseContent.deployment).joinedload(CourseContentDeployment.example_version).joinedload(ExampleVersion.example).joinedload(Example.repository)
            ).filter(
                and_(
                    CourseContent.id.in_(selected_ids),
                    CourseContent.archived_at.is_(None)
                )
            ).all()
        else:
            contents = db.query(CourseContent).options(
                joinedload(CourseContent.deployment).joinedload(CourseContentDeployment.example_version).joinedload(ExampleVersion.example).joinedload(Example.repository)
            ).filter(
                and_(
                    CourseContent.course_id == course_id,
                    CourseContent.archived_at.is_(None)
                )
            ).all()

        # Prepare repo workdir
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = os.path.join(temp_dir, 'assignments')

            # Authenticated URL if HTTP + token
            auth_url = assignments_url
            if gitlab_token and 'http' in assignments_url:
                from urllib.parse import urlparse, urlunparse
                parsed = urlparse(assignments_url)
                auth_netloc = f"oauth2:{gitlab_token}@{parsed.hostname}"
                if parsed.port:
                    auth_netloc += f":{parsed.port}"
                auth_url = urlunparse((parsed.scheme, auth_netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))

            # Clone
            try:
                if gitlab_token and 'http' in assignments_url:
                    repo = git.Repo.clone_from(auth_url, repo_path)
                else:
                    repo = git.Repo.clone_from(assignments_url, repo_path)
            except Exception as e:
                return {"success": False, "error": f"Clone failed: {str(e)}"}

            processed = 0
            errors: List[str] = []

            # Write each content
            for content in contents:
                try:
                    if not content.deployment or not content.deployment.example_version:
                        continue
                    ev = content.deployment.example_version
                    example = ev.example
                    if not example or not example.repository:
                        continue

                    # Build dir
                    directory_name = content.deployment.deployment_path or str(example.identifier)
                    target_dir = Path(repo_path) / directory_name

                    if target_dir.exists() and overwrite_strategy != 'force_update':
                        # Skip existing
                        continue

                    # Ensure dir and clear if forcing
                    if target_dir.exists() and overwrite_strategy == 'force_update':
                        shutil.rmtree(target_dir)
                    target_dir.mkdir(parents=True, exist_ok=True)

                    # Download full example content
                    files = await download_example_files(example.repository, ev)
                    for rel_path, data in files.items():
                        file_path = target_dir / rel_path
                        file_path.parent.mkdir(parents=True, exist_ok=True)
                        file_path.write_bytes(data)

                    # Update deployment path if needed
                    if not content.deployment.deployment_path:
                        content.deployment.deployment_path = directory_name

                    processed += 1
                except Exception as e:
                    errors.append(f"{str(content.path)}: {str(e)}")
                    # Do not fail the entire run; continue

            # Commit/push if changed
            pushed = False
            try:
                repo.git.add(A=True)
                if repo.is_dirty() or repo.untracked_files:
                    message = commit_message or f"Initialize/update assignments ({processed} items)"
                    repo.index.commit(message)
                    repo.git.push('origin', 'main')
                    pushed = True
                else:
                    pushed = True  # Nothing to do counts as success
            except Exception as e:
                errors.append(f"Push failed: {str(e)}")
                pushed = False

            # Record commit in deployments if pushed
            if pushed:
                try:
                    head_sha = repo.head.commit.hexsha
                    for content in contents:
                        if content.deployment:
                            content.deployment.version_identifier = head_sha
                            # Ensure source identity is stored
                            try:
                                ev = content.deployment.example_version
                                if ev and ev.example and not content.deployment.example_identifier:
                                    from ctutor_backend.custom_types import Ltree
                                    content.deployment.example_identifier = Ltree(str(ev.example.identifier))
                                if ev and ev.version_tag and not content.deployment.version_tag:
                                    content.deployment.version_tag = ev.version_tag
                            except Exception:
                                pass
                            # History entry
                            # Ensure history example_identifier is proper ltree
                            from ctutor_backend.custom_types import Ltree
                            hist = DeploymentHistory(
                                deployment_id=content.deployment.id,
                                action="updated",
                                example_version_id=content.deployment.example_version_id,
                                example_identifier=(
                                    Ltree(str(ev.example.identifier)) if ev and ev.example
                                    else (
                                        getattr(content.deployment, 'example_identifier', None)
                                    )
                                ),
                                version_tag=(ev.version_tag if ev else getattr(content.deployment, 'version_tag', None))
                            )
                            db.add(hist)
                    db.commit()
                except Exception:
                    pass

            return {
                "success": processed > 0 and pushed,
                "processed_count": processed,
                "errors": errors,
            }
    finally:
        try:
            db_gen.close()
        except Exception:
            pass


@register_task
@workflow.defn(name="generate_assignments_repository", sandboxed=False)
class GenerateAssignmentsRepositoryWorkflow(BaseWorkflow):
    @classmethod
    def get_name(cls) -> str:
        return "generate_assignments_repository"

    @classmethod
    def get_task_queue(cls) -> str:
        return "computor-tasks"

    @classmethod
    def get_execution_timeout(cls) -> timedelta:
        return timedelta(minutes=20)

    @workflow.run
    async def run(self, params: Dict[str, Any]) -> WorkflowResult:
        course_id = params.get('course_id')
        assignments_url = params.get('assignments_url')
        selection = params.get('selection')
        overwrite = params.get('overwrite_strategy', 'skip_if_exists')
        commit_message = params.get('commit_message')

        if not course_id:
            return WorkflowResult(status="failed", result=None, error="course_id is required")

        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=5),
            maximum_interval=timedelta(minutes=1),
            maximum_attempts=3,
            backoff_coefficient=2.0,
        )

        try:
            result = await workflow.execute_activity(
                generate_assignments_repository_activity,
                args=[course_id, assignments_url, selection, overwrite, commit_message],
                start_to_close_timeout=timedelta(minutes=20),
                retry_policy=retry_policy,
            )
            return WorkflowResult(status="completed" if result.get('success') else "failed", result=result)
        except Exception as e:
            return WorkflowResult(status="failed", result=None, error=str(e))
