# Advanced Usage Guide

This guide covers the advanced features of the Computor API Client, including role-based views, custom endpoints, file operations, and workflow management.

## Table of Contents

- [Role-Based View Clients](#role-based-view-clients)
- [Custom Endpoint Clients](#custom-endpoint-clients)
- [File Operations](#file-operations)
- [Task & Workflow Management](#task--workflow-management)
- [System Administration](#system-administration)
- [Authentication](#authentication)
- [Submission & Testing](#submission--testing)
- [Example Management](#example-management)

## Role-Based View Clients

The Computor platform provides specialized view endpoints for different user roles: students, tutors, and lecturers. Each role has a dedicated client with role-appropriate methods.

### Student View Client

Access course content and track your progress as a student:

```python
async with ComputorClient(base_url="http://localhost:8000") as client:
    await client.authenticate(username="student@example.com", password="password")

    # Get courses I'm enrolled in
    my_courses = await client.student_view.get_my_courses()

    # Get course contents
    course_contents = await client.student_view.get_my_course_contents(
        course_id="course123"
    )

    # Get detailed view of specific content
    content = await client.student_view.get_course_content_detail(
        course_content_id="content456"
    )
```

### Tutor View Client

Manage students and provide feedback as a tutor:

```python
async with ComputorClient(base_url="http://localhost:8000") as client:
    await client.authenticate(username="tutor@example.com", password="password")

    # Get courses I'm tutoring
    my_courses = await client.tutor_view.get_my_courses()

    # Get students I'm responsible for
    students = await client.tutor_view.get_course_members()

    # View specific student's course contents
    student_contents = await client.tutor_view.get_student_course_contents(
        course_member_id="member123"
    )

    # Update student grades
    updated = await client.tutor_view.update_student_grades(
        course_member_id="member123",
        course_content_id="content456",
        grades_data={
            "grade": 85,
            "feedback": "Great work! Consider improving..."
        }
    )
```

### Lecturer View Client

Full course management as a lecturer:

```python
async with ComputorClient(base_url="http://localhost:8000") as client:
    await client.authenticate(username="lecturer@example.com", password="password")

    # Get courses I'm teaching
    my_courses = await client.lecturer_view.get_my_courses()

    # Get course contents I manage
    contents = await client.lecturer_view.get_my_course_contents(
        course_id="course123"
    )

    # Create new course content
    new_content = await client.lecturer_view.create_course_content(
        course_id="course123",
        content_data={
            "title": "Week 5: Advanced Topics",
            "content_type": "assignment",
            "description": "Complete the advanced exercise",
            "due_date": "2025-11-01T23:59:59Z"
        }
    )

    # Update course content
    updated = await client.lecturer_view.update_course_content(
        course_content_id="content456",
        content_data={"description": "Updated description"}
    )

    # Delete course content
    await client.lecturer_view.delete_course_content("content456")
```

## Custom Endpoint Clients

### Authentication Client

Manage authentication, SSO, and auth plugins:

```python
async with ComputorClient(base_url="http://localhost:8000") as client:
    # Get available authentication providers
    providers = await client.auth.get_providers()

    # Login with username/password
    auth_result = await client.auth.login(
        username="user@example.com",
        password="password"
    )

    # Initiate SSO login
    sso_redirect = await client.auth.sso_login(provider="keycloak")

    # Refresh token
    refreshed = await client.auth.refresh_token(refresh_token)

    # Register new user
    user = await client.auth.register({
        "email": "newuser@example.com",
        "name": "New User",
        "provider": "keycloak"
    })

    # Logout
    await client.auth.logout()

    # Admin: Manage auth plugins
    plugins = await client.auth.list_plugins()
    await client.auth.enable_plugin("keycloak")
    await client.auth.disable_plugin("local")
    await client.auth.reload_plugins()
```

## File Operations

### Storage Client

Upload, download, and manage files in MinIO storage:

```python
async with ComputorClient(base_url="http://localhost:8000") as client:
    await client.authenticate(username="user@example.com", password="password")

    # Upload file
    result = await client.storage.upload(
        file_path="document.pdf",
        bucket_name="documents",
        object_key="user123/document.pdf",
        metadata={"user_id": "user123", "type": "assignment"}
    )

    # Download file
    content = await client.storage.download(
        object_key="user123/document.pdf",
        output_path="./downloads/document.pdf"
    )

    # Get presigned URL for direct access
    presigned = await client.storage.get_presigned_url(
        bucket_name="documents",
        object_key="user123/document.pdf",
        expiration=3600,  # 1 hour
        operation="get"
    )
    print(f"Direct URL: {presigned['url']}")

    # Copy object
    await client.storage.copy(
        source_bucket="documents",
        source_key="user123/document.pdf",
        dest_bucket="archive",
        dest_key="2025/user123/document.pdf"
    )

    # Bucket management
    buckets = await client.storage.list_buckets()
    await client.storage.create_bucket("new-bucket")
    stats = await client.storage.get_bucket_stats("documents")
    await client.storage.delete_bucket("old-bucket")
```

## Task & Workflow Management

### Task Client

Manage asynchronous Temporal workflows:

```python
async with ComputorClient(base_url="http://localhost:8000") as client:
    await client.authenticate(username="admin", password="password")

    # Get available task types
    task_types = await client.tasks.get_task_types()

    # Submit task
    task = await client.tasks.submit_task({
        "task_type": "process_submission",
        "payload": {
            "submission_id": "sub123",
            "test_suite": "comprehensive"
        }
    })
    task_id = task['id']

    # Poll for status
    import asyncio
    while True:
        status = await client.tasks.get_status(task_id)
        print(f"Task state: {status['state']}")

        if status['state'] in ['completed', 'failed']:
            break

        await asyncio.sleep(2)

    # Get result
    result = await client.tasks.get_result(task_id)

    # Cancel task
    await client.tasks.cancel_task(task_id)

    # List all tasks
    tasks = await client.tasks.list_tasks(params={
        "state": "running",
        "limit": 10
    })

    # Get worker status
    worker_status = await client.tasks.get_worker_status()
```

## System Administration

### System Admin Client

Deploy organizations, courses, and manage GitLab integration:

```python
async with ComputorClient(base_url="http://localhost:8000") as client:
    await client.authenticate(username="admin", password="password")

    # Deploy organization via Temporal
    org_workflow = await client.system.deploy_organization({
        "name": "University of Example",
        "gitlab_group_path": "uni-example",
        "description": "Main university organization"
    })
    workflow_id = org_workflow['workflow_id']

    # Check deployment status
    status = await client.system.get_deployment_status(workflow_id)

    # Deploy course family
    family = await client.system.deploy_course_family({
        "organization_id": "org123",
        "name": "Computer Science",
        "gitlab_subgroup_path": "cs"
    })

    # Deploy course
    course = await client.system.deploy_course({
        "course_family_id": "family123",
        "name": "Data Structures",
        "gitlab_subgroup_path": "data-structures"
    })

    # Create complete hierarchy from config
    hierarchy = await client.system.create_hierarchy({
        "organizations": [...],
        "course_families": [...],
        "courses": [...]
    })

    # Generate student template repository
    template = await client.system.generate_student_template("course123")

    # Generate assignments repository
    assignments = await client.system.generate_assignments("course123")

    # Check GitLab configuration status
    gitlab_status = await client.system.get_gitlab_status("course123")
```

### Deployment Client

Deploy from configuration files:

```python
async with ComputorClient(base_url="http://localhost:8000") as client:
    await client.authenticate(username="admin", password="password")

    # Validate configuration
    validation = await client.deploy.validate_config({
        "organizations": [...],
        "courses": [...]
    })

    # Deploy from config object
    deployment = await client.deploy.deploy_from_config({
        "organizations": [...],
        "courses": [...]
    })

    # Deploy from YAML
    yaml_content = """
    organizations:
      - name: My University
        gitlab_group_path: my-uni
    """
    deployment = await client.deploy.deploy_from_yaml(yaml_content)

    # Get deployment status
    status = await client.deploy.get_deployment_status(
        deployment['workflow_id']
    )
```

## Submission & Testing

### Submission Client

Upload submissions and manage grading:

```python
async with ComputorClient(base_url="http://localhost:8000") as client:
    await client.authenticate(username="student@example.com", password="password")

    # Upload submission artifact
    artifact = await client.submissions.upload_artifact(
        file_path="my_solution.zip",
        metadata={
            "course_content_id": "content123",
            "version": "1.0",
            "comment": "Final submission"
        }
    )
    artifact_id = artifact['id']

    # Test artifact
    test = await client.submissions.test_artifact(
        artifact_id,
        test_data={"test_suite": "comprehensive", "timeout": 300}
    )

    # List test results
    tests = await client.submissions.list_artifact_tests(artifact_id)

    # Grading (tutor/lecturer role)
    grade = await client.submissions.create_grade(
        artifact_id,
        grade_data={
            "points": 85,
            "max_points": 100,
            "feedback": "Great work!",
            "grader_id": "tutor123"
        }
    )

    # Update grade
    updated_grade = await client.submissions.update_grade(
        grade['id'],
        grade_data={"points": 90, "feedback": "Updated after review"}
    )

    # Reviews
    review = await client.submissions.create_review(
        artifact_id,
        review_data={
            "comment": "Code quality is excellent",
            "suggestions": ["Consider adding more tests"]
        }
    )
```

### Test Execution Client

Execute tests directly:

```python
async with ComputorClient(base_url="http://localhost:8000") as client:
    await client.authenticate(username="student@example.com", password="password")

    # Create and execute test
    test = await client.tests.create_test({
        "artifact_id": "artifact123",
        "test_suite": "unit_tests",
        "timeout": 120
    })

    # Get test execution status
    status = await client.tests.get_test_status(test['id'])
```

## Example Management

### Example Client

Manage code templates and examples:

```python
async with ComputorClient(base_url="http://localhost:8000") as client:
    await client.authenticate(username="lecturer@example.com", password="password")

    # Upload example package
    example = await client.examples.upload_example(
        file_path="python_starter.zip",
        metadata={
            "name": "Python Starter Template",
            "language": "python",
            "version": "1.0.0"
        }
    )
    example_id = example['id']

    # Create new version
    version = await client.examples.create_version(
        example_id,
        version_data={
            "version": "1.1.0",
            "changelog": "Added examples",
            "breaking_changes": False
        }
    )

    # Add dependency
    dep = await client.examples.add_dependency(
        example_id,
        dependency_data={
            "dependency_example_id": "pytest_template",
            "version_constraint": ">=1.0.0"
        }
    )

    # List dependencies
    deps = await client.examples.list_dependencies(example_id)

    # List versions
    versions = await client.examples.list_versions(example_id)

    # Download example
    content = await client.examples.download_example(
        example_id,
        output_path="./template.zip"
    )

    # Download specific version
    version_content = await client.examples.download_version(
        version_id="ver123",
        output_path="./template_v1.0.zip"
    )

    # Remove dependency
    await client.examples.remove_dependency("dep123")
```

## Base Classes for Custom Clients

If you need to create your own custom client, you can extend the provided base classes:

```python
from computor_client.advanced_base import CustomActionClient
import httpx

class MyCustomClient(CustomActionClient):
    """Custom client for special endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/my-custom-endpoint"
        )

    async def my_custom_action(self, param: str):
        """Execute custom action."""
        return await self.custom_post(
            "action",
            {"parameter": param}
        )

    async def get_custom_data(self, id: str):
        """Get custom data."""
        return await self.custom_get(f"data/{id}")

# Use in client
async with ComputorClient(base_url="http://localhost:8000") as client:
    my_client = MyCustomClient(client._client)
    result = await my_client.my_custom_action("test")
```

Available base classes:
- `CustomActionClient` - Generic custom endpoint support
- `RoleBasedViewClient` - Role-specific view endpoints
- `FileOperationClient` - File upload/download operations
- `TaskClient` - Workflow/task management
- `AuthenticationClient` - Authentication operations

## Error Handling

All clients use custom exceptions for better error handling:

```python
from computor_client import (
    ComputorNotFoundError,
    ComputorAuthenticationError,
    ComputorValidationError,
    ComputorServerError,
)

async with ComputorClient(base_url="http://localhost:8000") as client:
    try:
        user = await client.users.get("nonexistent-id")
    except ComputorNotFoundError as e:
        print(f"User not found: {e.message}")
    except ComputorAuthenticationError as e:
        print(f"Authentication failed: {e.message}")
    except ComputorValidationError as e:
        print(f"Validation error: {e.message}")
        print(f"Details: {e.detail}")
    except ComputorServerError as e:
        print(f"Server error: {e.message}")
```

## See Also

- [Basic Usage Examples](./examples/basic_usage.py)
- [Role-Based View Examples](./examples/role_based_views.py)
- [Custom Endpoint Examples](./examples/custom_endpoints.py)
- [Main README](./README.md)
