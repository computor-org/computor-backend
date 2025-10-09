"""Custom clients for non-CRUD endpoints."""

from typing import Optional, Dict, Any, List, Union
from pathlib import Path
import httpx
from pydantic import BaseModel

from .base import (
    AuthenticationClient,
    FileOperationClient,
    TaskClient,
    CustomActionClient,
)


class ComputorAuthClient(AuthenticationClient):
    """Client for authentication endpoints (/auth/*)."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/auth",
        )

    async def register(
        self,
        registration_data: Union[BaseModel, Dict[str, Any]]
    ) -> Any:
        """Register a new user with SSO provider."""
        return await self.custom_post("register", registration_data)

    async def sso_callback(
        self,
        provider: str,
        code: str,
        state: Optional[str] = None
    ) -> Any:
        """Handle SSO callback from provider."""
        params = {"code": code}
        if state:
            params["state"] = state
        return await self.custom_get(f"{provider}/callback", params=params)

    async def refresh_local_token(self, refresh_token: str) -> Any:
        """Refresh local access token."""
        return await self.custom_post(
            "refresh/local",
            {"refresh_token": refresh_token}
        )

    # Admin plugin management
    async def list_plugins(self) -> List[Any]:
        """List all available authentication plugins (admin only)."""
        return await self.custom_get("admin/plugins")

    async def enable_plugin(self, plugin_name: str) -> Any:
        """Enable an authentication plugin (admin only)."""
        return await self.custom_post(f"admin/plugins/{plugin_name}/enable")

    async def disable_plugin(self, plugin_name: str) -> Any:
        """Disable an authentication plugin (admin only)."""
        return await self.custom_post(f"admin/plugins/{plugin_name}/disable")

    async def reload_plugins(self) -> Any:
        """Reload all authentication plugins (admin only)."""
        return await self.custom_post("admin/plugins/reload")


class StorageFileClient(FileOperationClient):
    """Client for file storage operations (/storage/*)."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/storage",
        )

    async def upload(
        self,
        file_path: Union[str, Path],
        bucket_name: Optional[str] = None,
        object_key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Upload a file to storage.

        Args:
            file_path: Path to file to upload
            bucket_name: Target bucket name
            object_key: Object key/path in bucket
            metadata: Additional metadata

        Returns:
            Upload response with file information
        """
        additional_data = {}
        if bucket_name:
            additional_data['bucket_name'] = bucket_name
        if object_key:
            additional_data['object_key'] = object_key
        if metadata:
            additional_data['metadata'] = metadata

        return await self.upload_file(file_path, "upload", additional_data)

    async def download(
        self,
        object_key: str,
        output_path: Optional[Union[str, Path]] = None,
    ) -> bytes:
        """
        Download a file from storage.

        Args:
            object_key: Object key/path in storage
            output_path: Optional local path to save file

        Returns:
            File content as bytes
        """
        return await self.download_file(f"download/{object_key}", output_path)

    async def copy(
        self,
        source_bucket: str,
        source_key: str,
        dest_bucket: str,
        dest_key: str,
    ) -> Any:
        """Copy an object within or between buckets."""
        return await self.custom_post("copy", {
            "source_bucket": source_bucket,
            "source_key": source_key,
            "dest_bucket": dest_bucket,
            "dest_key": dest_key,
        })

    async def get_presigned_url(
        self,
        bucket_name: str,
        object_key: str,
        expiration: int = 3600,
        operation: str = "get"
    ) -> Any:
        """
        Generate a presigned URL for direct file access.

        Args:
            bucket_name: Bucket name
            object_key: Object key/path
            expiration: URL expiration in seconds
            operation: Operation type ('get', 'put', etc.)

        Returns:
            Presigned URL information
        """
        return await self.custom_post("presigned-url", {
            "bucket_name": bucket_name,
            "object_key": object_key,
            "expiration": expiration,
            "operation": operation,
        })

    async def list_buckets(self) -> List[Any]:
        """List all available storage buckets."""
        return await self.custom_get("buckets")

    async def create_bucket(self, bucket_name: str) -> Any:
        """Create a new storage bucket."""
        return await self.custom_post("buckets", {"bucket_name": bucket_name})

    async def delete_bucket(self, bucket_name: str) -> None:
        """Delete a storage bucket."""
        await self.custom_delete(f"buckets/{bucket_name}")

    async def get_bucket_stats(self, bucket_name: str) -> Any:
        """Get usage statistics for a bucket."""
        return await self.custom_get(f"buckets/{bucket_name}/stats")


class ComputorTaskClient(TaskClient):
    """Client for task management endpoints (/tasks/*)."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/tasks",
        )

    async def get_task_types(self) -> List[Any]:
        """Get list of available task types."""
        return await self.custom_get("types")

    async def get_worker_status(self) -> Any:
        """Get Temporal worker status."""
        return await self.custom_get("workers/status")

    async def get_task(self, task_id: str) -> Any:
        """Get task information by ID."""
        return await self.custom_get(str(task_id))

    async def delete_task(self, task_id: str) -> None:
        """Delete task from database."""
        await self.custom_delete(str(task_id))


class SystemAdminClient(CustomActionClient):
    """Client for system administration endpoints (/system/*)."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/system",
        )

    # Hierarchy deployment
    async def deploy_organization(self, org_data: Union[BaseModel, Dict[str, Any]]) -> Any:
        """Create organization asynchronously via Temporal workflow."""
        return await self.custom_post("deploy/organizations", org_data)

    async def deploy_course_family(self, family_data: Union[BaseModel, Dict[str, Any]]) -> Any:
        """Create course family asynchronously via Temporal workflow."""
        return await self.custom_post("deploy/course-families", family_data)

    async def deploy_course(self, course_data: Union[BaseModel, Dict[str, Any]]) -> Any:
        """Create course asynchronously via Temporal workflow."""
        return await self.custom_post("deploy/courses", course_data)

    async def create_hierarchy(self, config: Union[BaseModel, Dict[str, Any]]) -> Any:
        """Create complete organization/course hierarchy from configuration."""
        return await self.custom_post("hierarchy/create", config)

    async def get_deployment_status(self, workflow_id: str) -> Any:
        """Get status of hierarchy deployment workflow."""
        return await self.custom_get(f"hierarchy/status/{workflow_id}")

    # Course management
    async def generate_student_template(self, course_id: str) -> Any:
        """Generate student template repository for course."""
        return await self.custom_post(f"courses/{course_id}/generate-student-template")

    async def generate_assignments(self, course_id: str) -> Any:
        """Generate assignments repository for course."""
        return await self.custom_post(f"courses/{course_id}/generate-assignments")

    async def get_gitlab_status(self, course_id: str) -> Any:
        """Check GitLab configuration status for course."""
        return await self.custom_get(f"courses/{course_id}/gitlab-status")


class ExampleClient(FileOperationClient):
    """Client for example/template operations (/examples/*)."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/examples",
        )

    async def list(self, query: Optional[BaseModel] = None) -> List[Any]:
        """
        List examples with optional query parameters.

        Args:
            query: Optional query parameters (ExampleQuery)

        Returns:
            List of examples
        """
        params = {}
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
        return await self.custom_get("", params=params)

    async def get(self, example_id: str) -> Any:
        """
        Get a specific example by ID.

        Args:
            example_id: ID of the example

        Returns:
            Example details
        """
        return await self.custom_get(f"{example_id}")

    async def upload_example(
        self,
        file_path: Union[str, Path],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Upload an example package to MinIO.

        Args:
            file_path: Path to example ZIP file
            metadata: Additional metadata for the example

        Returns:
            Upload response with example information
        """
        return await self.upload_file(file_path, "upload", metadata)

    async def download_example(
        self,
        example_id: str,
        output_path: Optional[Union[str, Path]] = None,
    ) -> bytes:
        """
        Download latest version of an example with dependencies.

        Args:
            example_id: ID of the example
            output_path: Optional local path to save file

        Returns:
            Example file content
        """
        return await self.download_file(f"{example_id}/download", output_path)

    async def download_version(
        self,
        version_id: str,
        output_path: Optional[Union[str, Path]] = None,
    ) -> bytes:
        """
        Download specific version of an example.

        Args:
            version_id: ID of the version
            output_path: Optional local path to save file

        Returns:
            Example version file content
        """
        return await self.download_file(f"download/{version_id}", output_path)

    # Dependencies
    async def add_dependency(
        self,
        example_id: str,
        dependency_data: Union[BaseModel, Dict[str, Any]]
    ) -> Any:
        """Add a dependency to an example."""
        return await self.custom_post(f"{example_id}/dependencies", dependency_data)

    async def list_dependencies(self, example_id: str) -> List[Any]:
        """List dependencies for an example."""
        return await self.custom_get(f"{example_id}/dependencies")

    async def remove_dependency(self, dependency_id: str) -> None:
        """Remove a dependency."""
        await self.custom_delete(f"dependencies/{dependency_id}")

    # Versions
    async def create_version(
        self,
        example_id: str,
        version_data: Union[BaseModel, Dict[str, Any]]
    ) -> Any:
        """Create a new version for an example."""
        return await self.custom_post(f"{example_id}/versions", version_data)

    async def list_versions(self, example_id: str) -> List[Any]:
        """List all versions of an example."""
        return await self.custom_get(f"{example_id}/versions")

    async def get_version(self, version_id: str) -> Any:
        """Get specific version details."""
        return await self.custom_get(f"versions/{version_id}")


class SubmissionClient(CustomActionClient):
    """Client for submission-related operations."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/submissions",
        )

    async def upload_artifact(
        self,
        file_path: Union[str, Path],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Upload a submission artifact (ZIP file).

        Args:
            file_path: Path to submission ZIP file
            metadata: Additional metadata for submission

        Returns:
            Upload response with artifact information
        """
        file_path = Path(file_path)

        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f, 'application/zip')}
            data = metadata or {}

            response = await self.client.post(
                f"{self.base_path}/artifacts",
                files=files,
                data=data
            )

            if response.status_code >= 400:
                from .exceptions import raise_for_status
                raise_for_status(response.status_code, response.json())

            response.raise_for_status()
            return response.json()

    async def test_artifact(
        self,
        artifact_id: str,
        test_data: Optional[Union[BaseModel, Dict[str, Any]]] = None
    ) -> Any:
        """Create and execute test for submission artifact."""
        return await self.custom_post(f"artifacts/{artifact_id}/test", test_data)

    async def list_artifact_tests(self, artifact_id: str) -> List[Any]:
        """List test results for artifact."""
        return await self.custom_get(f"artifacts/{artifact_id}/tests")

    async def update_test(
        self,
        test_id: str,
        test_data: Union[BaseModel, Dict[str, Any]]
    ) -> Any:
        """Update test result."""
        return await self.custom_patch(f"tests/{test_id}", test_data)

    # Grading
    async def create_grade(
        self,
        artifact_id: str,
        grade_data: Union[BaseModel, Dict[str, Any]]
    ) -> Any:
        """Create grade for artifact."""
        return await self.custom_post(f"artifacts/{artifact_id}/grades", grade_data)

    async def list_grades(self, artifact_id: str) -> List[Any]:
        """List grades for artifact."""
        return await self.custom_get(f"artifacts/{artifact_id}/grades")

    async def update_grade(
        self,
        grade_id: str,
        grade_data: Union[BaseModel, Dict[str, Any]]
    ) -> Any:
        """Update existing grade."""
        return await self.custom_patch(f"grades/{grade_id}", grade_data)

    async def delete_grade(self, grade_id: str) -> None:
        """Delete grade."""
        await self.custom_delete(f"grades/{grade_id}")

    # Reviews
    async def create_review(
        self,
        artifact_id: str,
        review_data: Union[BaseModel, Dict[str, Any]]
    ) -> Any:
        """Create review for artifact."""
        return await self.custom_post(f"artifacts/{artifact_id}/reviews", review_data)

    async def list_reviews(self, artifact_id: str) -> List[Any]:
        """List reviews for artifact."""
        return await self.custom_get(f"artifacts/{artifact_id}/reviews")

    async def update_review(
        self,
        review_id: str,
        review_data: Union[BaseModel, Dict[str, Any]]
    ) -> Any:
        """Update existing review."""
        return await self.custom_patch(f"reviews/{review_id}", review_data)

    async def delete_review(self, review_id: str) -> None:
        """Delete review."""
        await self.custom_delete(f"reviews/{review_id}")


class TestExecutionClient(CustomActionClient):
    """Client for test execution endpoints (/tests/*)."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/tests",
        )

    async def create_test(
        self,
        test_data: Union[BaseModel, Dict[str, Any]]
    ) -> Any:
        """Create and execute test for submission artifact."""
        return await self.custom_post("", test_data)

    async def get_test_status(self, result_id: str) -> Any:
        """Get current test execution status."""
        return await self.custom_get(f"status/{result_id}")


class DeploymentClient(CustomActionClient):
    """Client for deployment configuration endpoints (/deploy/*)."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/deploy",
        )

    async def deploy_from_config(
        self,
        config: Union[BaseModel, Dict[str, Any]]
    ) -> Any:
        """Deploy from configuration object."""
        return await self.custom_post("from-config", config)

    async def deploy_from_yaml(
        self,
        yaml_content: str
    ) -> Any:
        """Deploy from YAML file content."""
        return await self.custom_post("from-yaml", {"yaml": yaml_content})

    async def get_deployment_status(self, workflow_id: str) -> Any:
        """Get deployment workflow status."""
        return await self.custom_get(f"status/{workflow_id}")

    async def validate_config(
        self,
        config: Union[BaseModel, Dict[str, Any]]
    ) -> Any:
        """Validate deployment configuration."""
        return await self.custom_post("validate", config)
