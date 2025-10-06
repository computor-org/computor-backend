# Computor Client Quick Reference

Quick reference guide for the most common operations with the Computor API Client.

## Installation & Setup

```bash
# Install package
pip install -e computor-client/

# Requires computor-types
pip install -e computor-types/
```

## Basic Connection

```python
import asyncio
from computor_client import ComputorClient

async def main():
    async with ComputorClient(base_url="http://localhost:8000") as client:
        # Authenticate
        await client.authenticate(username="user@example.com", password="password")

        # Your code here...

asyncio.run(main())
```

## CRUD Operations (Standard)

```python
# CREATE
new_org = await client.organizations.create(OrganizationCreate(...))

# READ (get by ID)
org = await client.organizations.get(org_id)

# READ (list all)
orgs = await client.organizations.list()

# READ (with query params)
orgs = await client.organizations.list(OrganizationQuery(name="University"))

# UPDATE
updated = await client.organizations.update(org_id, OrganizationUpdate(...))

# DELETE
await client.organizations.delete(org_id)
```

## Role-Based Views

### Student
```python
# Get my enrolled courses
courses = await client.student_view.get_my_courses()

# Get course contents
contents = await client.student_view.get_my_course_contents(course_id="...")

# Get specific content
content = await client.student_view.get_course_content_detail(content_id="...")
```

### Tutor
```python
# Get students I'm tutoring
students = await client.tutor_view.get_course_members()

# View student's progress
progress = await client.tutor_view.get_student_course_contents(member_id="...")

# Update grades
await client.tutor_view.update_student_grades(
    member_id="...",
    content_id="...",
    grades_data={"grade": 85, "feedback": "Good work!"}
)
```

### Lecturer
```python
# Get my teaching courses
courses = await client.lecturer_view.get_my_courses()

# Create course content
content = await client.lecturer_view.create_course_content(
    course_id="...",
    content_data={"title": "Assignment 1", "type": "assignment"}
)

# Update content
await client.lecturer_view.update_course_content(
    content_id="...",
    content_data={"description": "Updated description"}
)
```

## File Operations

```python
# Upload file
result = await client.storage.upload(
    file_path="document.pdf",
    bucket_name="submissions",
    object_key="student123/assignment.pdf"
)

# Download file
content = await client.storage.download(
    object_key="student123/assignment.pdf",
    output_path="./downloads/assignment.pdf"
)

# Get presigned URL (direct access)
url_info = await client.storage.get_presigned_url(
    bucket_name="submissions",
    object_key="student123/assignment.pdf",
    expiration=3600  # 1 hour
)
direct_url = url_info['url']

# List buckets
buckets = await client.storage.list_buckets()

# Bucket stats
stats = await client.storage.get_bucket_stats("submissions")
```

## Task Management

```python
# Submit task
task = await client.tasks.submit_task({
    "task_type": "process_submission",
    "payload": {"submission_id": "sub123"}
})

# Get status
status = await client.tasks.get_status(task['id'])

# Get result
result = await client.tasks.get_result(task['id'])

# Cancel task
await client.tasks.cancel_task(task['id'])

# List tasks
tasks = await client.tasks.list_tasks(params={"state": "running"})
```

## Submissions & Testing

```python
# Upload submission
artifact = await client.submissions.upload_artifact(
    file_path="solution.zip",
    metadata={"course_content_id": "content123"}
)

# Test submission
test = await client.submissions.test_artifact(
    artifact['id'],
    test_data={"test_suite": "comprehensive"}
)

# Get test status
status = await client.tests.get_test_status(test['id'])

# List tests
tests = await client.submissions.list_artifact_tests(artifact['id'])

# Create grade
grade = await client.submissions.create_grade(
    artifact['id'],
    grade_data={"points": 85, "feedback": "Great work!"}
)

# List grades
grades = await client.submissions.list_grades(artifact['id'])
```

## System Administration

```python
# Deploy organization
org_workflow = await client.system.deploy_organization({
    "name": "University",
    "gitlab_group_path": "uni"
})

# Deploy course family
family = await client.system.deploy_course_family({
    "organization_id": "org123",
    "name": "Computer Science"
})

# Deploy course
course = await client.system.deploy_course({
    "course_family_id": "family123",
    "name": "Data Structures"
})

# Check deployment status
status = await client.system.get_deployment_status(workflow_id)

# Generate student template
await client.system.generate_student_template("course123")

# Generate assignments
await client.system.generate_assignments("course123")

# GitLab status
gitlab_status = await client.system.get_gitlab_status("course123")
```

## Authentication

```python
# Login
auth = await client.auth.login(
    username="user@example.com",
    password="password"
)

# Get providers
providers = await client.auth.get_providers()

# SSO login
sso = await client.auth.sso_login(provider="keycloak")

# Refresh token
refreshed = await client.auth.refresh_token(refresh_token)

# Logout
await client.auth.logout()
```

## Example Management

```python
# Upload example
example = await client.examples.upload_example(
    file_path="template.zip",
    metadata={"name": "Python Starter", "version": "1.0.0"}
)

# Download example
content = await client.examples.download_example(
    example_id="...",
    output_path="./template.zip"
)

# Create version
version = await client.examples.create_version(
    example_id="...",
    version_data={"version": "1.1.0", "changelog": "Added tests"}
)

# Add dependency
dep = await client.examples.add_dependency(
    example_id="...",
    dependency_data={"dependency_example_id": "...", "version_constraint": ">=1.0.0"}
)

# List versions
versions = await client.examples.list_versions(example_id="...")
```

## Error Handling

```python
from computor_client import (
    ComputorNotFoundError,
    ComputorAuthenticationError,
    ComputorValidationError,
    ComputorServerError,
)

try:
    user = await client.users.get("invalid-id")
except ComputorNotFoundError:
    print("Not found")
except ComputorAuthenticationError:
    print("Auth failed")
except ComputorValidationError as e:
    print(f"Validation error: {e.detail}")
except ComputorServerError:
    print("Server error")
```

## Common Patterns

### Polling Task Status
```python
import asyncio

task = await client.tasks.submit_task({...})

while True:
    status = await client.tasks.get_status(task['id'])
    if status['state'] in ['completed', 'failed']:
        break
    await asyncio.sleep(2)

result = await client.tasks.get_result(task['id'])
```

### Batch Operations
```python
# Create multiple items
items = [...]
created = []
for item_data in items:
    item = await client.items.create(item_data)
    created.append(item)
```

### File Upload with Progress (manual)
```python
import os

file_path = "large_file.zip"
file_size = os.path.getsize(file_path)

# For progress tracking, you'll need to implement chunked upload
# or use the streaming capabilities
result = await client.storage.upload(file_path, ...)
print(f"Uploaded {file_size} bytes")
```

## Available Clients

### CRUD Clients (Auto-generated)
- `client.accounts`
- `client.organizations`
- `client.course_families`
- `client.courses`
- `client.users`
- `client.groups`
- `client.roles`
- `client.profiles`
- `client.messages`
- `client.extensions`
- `client.languages`
- `client.execution_backends`
- ... and 25+ more

### Custom Clients
- `client.auth` - Authentication & SSO
- `client.storage` - File operations
- `client.tasks` - Workflow management
- `client.system` - Admin operations
- `client.examples` - Template management
- `client.submissions` - Submission handling
- `client.tests` - Test execution
- `client.deploy` - Deployment operations

### Role-Based Clients
- `client.student_view` - Student endpoints
- `client.tutor_view` - Tutor endpoints
- `client.lecturer_view` - Lecturer endpoints

## Configuration

```python
# Custom timeout
client = ComputorClient(
    base_url="http://localhost:8000",
    timeout=60.0  # seconds
)

# Disable SSL verification (development only!)
client = ComputorClient(
    base_url="http://localhost:8000",
    verify_ssl=False
)

# Custom headers
client = ComputorClient(
    base_url="http://localhost:8000",
    headers={"X-Custom-Header": "value"}
)

# Use existing token
async with ComputorClient(...) as client:
    await client.set_token("your-jwt-token")
```

## Tips & Best Practices

1. **Always use context manager**: Ensures proper cleanup
   ```python
   async with ComputorClient(...) as client:
       # Your code
   ```

2. **Handle errors gracefully**: Use specific exception types

3. **Use type hints**: Import Pydantic models from `computor_types`

4. **Poll with delays**: Don't hammer the API
   ```python
   await asyncio.sleep(2)  # Wait between status checks
   ```

5. **Close connections**: Let context manager handle it

6. **Check documentation**: See `ADVANCED_USAGE.md` for detailed examples

## Need More Help?

- **Basic Usage**: See `examples/basic_usage.py`
- **Role-Based Views**: See `examples/role_based_views.py`
- **Custom Endpoints**: See `examples/custom_endpoints.py`
- **Advanced Guide**: See `ADVANCED_USAGE.md`
- **Main README**: See `README.md`
- **Project Info**: See `../CLAUDE.md`
