# Temporal Workflows

This guide explains how Computor uses Temporal.io for asynchronous workflow orchestration and long-running operations.

## What is Temporal?

Temporal is a workflow orchestration platform that:
- Executes long-running operations reliably
- Handles failures and retries automatically
- Provides visibility into workflow execution
- Scales horizontally
- Maintains workflow state

## Temporal Architecture in Computor

```
┌──────────────────┐
│   FastAPI API    │
│   (Trigger)      │
└────────┬─────────┘
         │
         │ Start Workflow
         ▼
┌──────────────────┐
│ Temporal Server  │
│  (Orchestrator)  │
└────────┬─────────┘
         │
         │ Schedule Activities
         ▼
┌──────────────────┐
│ Temporal Worker  │
│  (Executor)      │
└────────┬─────────┘
         │
         │ Execute
         ▼
┌──────────────────┐
│ External Services│
│ - GitLab API     │
│ - MinIO          │
│ - Database       │
└──────────────────┘
```

## Temporal Components

### 1. Workflows

Workflows define the orchestration logic:

```python
# computor-backend/src/computor_backend/tasks/temporal_hierarchy_management.py
from datetime import timedelta
from temporalio import workflow
from typing import Dict, Any

@workflow.defn
class CreateCourseHierarchyWorkflow:
    """Workflow to create course hierarchy in GitLab."""

    @workflow.run
    async def run(self, course_id: str) -> Dict[str, Any]:
        """
        Create GitLab groups and repositories for a course.

        Args:
            course_id: Course ID

        Returns:
            Dictionary with created resources
        """
        # Execute activities in sequence
        # Activity 1: Create course group
        group_result = await workflow.execute_activity(
            create_course_group_activity,
            course_id,
            start_to_close_timeout=timedelta(minutes=5),
        )

        # Activity 2: Create student subgroup
        student_group_result = await workflow.execute_activity(
            create_student_subgroup_activity,
            {
                "course_id": course_id,
                "parent_group_id": group_result["group_id"],
            },
            start_to_close_timeout=timedelta(minutes=5),
        )

        # Activity 3: Create assignment repository
        repo_result = await workflow.execute_activity(
            create_assignment_repository_activity,
            {
                "course_id": course_id,
                "group_id": group_result["group_id"],
            },
            start_to_close_timeout=timedelta(minutes=10),
        )

        return {
            "course_id": course_id,
            "group_id": group_result["group_id"],
            "student_group_id": student_group_result["group_id"],
            "repository_url": repo_result["repository_url"],
        }
```

### 2. Activities

Activities perform the actual work:

```python
# computor-backend/src/computor_backend/tasks/temporal_hierarchy_management.py
from temporalio import activity
import logging

logger = logging.getLogger(__name__)

@activity.defn
async def create_course_group_activity(course_id: str) -> Dict[str, Any]:
    """
    Create GitLab group for course.

    Args:
        course_id: Course ID

    Returns:
        Dictionary with group_id
    """
    # Get database session
    from computor_backend.database import SessionLocal
    db = SessionLocal()

    try:
        # Fetch course
        from computor_backend.model.course import Course
        course = db.query(Course).filter_by(id=course_id).first()
        if not course:
            raise ValueError(f"Course {course_id} not found")

        # Create GitLab group
        from computor_backend.services.gitlab_utils import get_gitlab_client
        gitlab = get_gitlab_client()

        group = gitlab.groups.create({
            "name": course.name,
            "path": f"course-{course.id}",
            "visibility": "private",
        })

        # Update course with GitLab group ID
        course.gitlab_group_id = group.id
        db.commit()

        logger.info(f"Created GitLab group {group.id} for course {course_id}")

        return {
            "group_id": group.id,
            "group_url": group.web_url,
        }

    except Exception as e:
        logger.error(f"Failed to create course group: {e}")
        raise
    finally:
        db.close()
```

### 3. Worker

Workers execute workflows and activities:

```python
# computor-backend/src/computor_backend/tasks/temporal_worker.py
import asyncio
import logging
from temporalio.client import Client
from temporalio.worker import Worker

from computor_backend.settings import settings
from computor_backend.tasks.temporal_hierarchy_management import (
    CreateCourseHierarchyWorkflow,
    create_course_group_activity,
    create_student_subgroup_activity,
    create_assignment_repository_activity,
)

logger = logging.getLogger(__name__)

async def run_worker():
    """Run Temporal worker."""
    # Connect to Temporal server
    client = await Client.connect(
        f"{settings.TEMPORAL_HOST}:{settings.TEMPORAL_PORT}",
        namespace=settings.TEMPORAL_NAMESPACE,
    )

    # Create worker
    worker = Worker(
        client,
        task_queue="computor-tasks",
        workflows=[
            CreateCourseHierarchyWorkflow,
            # Register other workflows...
        ],
        activities=[
            create_course_group_activity,
            create_student_subgroup_activity,
            create_assignment_repository_activity,
            # Register other activities...
        ],
    )

    logger.info("Starting Temporal worker...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(run_worker())
```

### 4. Client

Client starts workflows from API endpoints:

```python
# computor-backend/src/computor_backend/tasks/temporal_client.py
from temporalio.client import Client
from computor_backend.settings import settings

_client = None

async def get_temporal_client() -> Client:
    """Get Temporal client singleton."""
    global _client
    if _client is None:
        _client = await Client.connect(
            f"{settings.TEMPORAL_HOST}:{settings.TEMPORAL_PORT}",
            namespace=settings.TEMPORAL_NAMESPACE,
        )
    return _client
```

## Common Workflow Patterns

### Pattern 1: Sequential Activities

Execute activities one after another:

```python
@workflow.defn
class SequentialWorkflow:
    @workflow.run
    async def run(self, data: str) -> str:
        # Activity 1
        result1 = await workflow.execute_activity(
            activity1,
            data,
            start_to_close_timeout=timedelta(minutes=5),
        )

        # Activity 2 (uses result from activity 1)
        result2 = await workflow.execute_activity(
            activity2,
            result1,
            start_to_close_timeout=timedelta(minutes=5),
        )

        # Activity 3
        result3 = await workflow.execute_activity(
            activity3,
            result2,
            start_to_close_timeout=timedelta(minutes=5),
        )

        return result3
```

### Pattern 2: Parallel Activities

Execute activities in parallel:

```python
import asyncio

@workflow.defn
class ParallelWorkflow:
    @workflow.run
    async def run(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Execute multiple activities in parallel
        tasks = [
            workflow.execute_activity(
                activity1,
                data["param1"],
                start_to_close_timeout=timedelta(minutes=5),
            ),
            workflow.execute_activity(
                activity2,
                data["param2"],
                start_to_close_timeout=timedelta(minutes=5),
            ),
            workflow.execute_activity(
                activity3,
                data["param3"],
                start_to_close_timeout=timedelta(minutes=5),
            ),
        ]

        # Wait for all to complete
        results = await asyncio.gather(*tasks)

        return {
            "result1": results[0],
            "result2": results[1],
            "result3": results[2],
        }
```

### Pattern 3: Error Handling

Handle errors and implement retries:

```python
from temporalio.exceptions import ActivityError

@workflow.defn
class ErrorHandlingWorkflow:
    @workflow.run
    async def run(self, data: str) -> Dict[str, Any]:
        try:
            # Try primary activity
            result = await workflow.execute_activity(
                primary_activity,
                data,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=workflow.RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=10),
                ),
            )
            return {"status": "success", "result": result}

        except ActivityError as e:
            # Log error
            workflow.logger.error(f"Primary activity failed: {e}")

            # Execute fallback activity
            fallback_result = await workflow.execute_activity(
                fallback_activity,
                data,
                start_to_close_timeout=timedelta(minutes=5),
            )
            return {"status": "fallback", "result": fallback_result}
```

### Pattern 4: Long-Running Operations

Handle operations that take hours or days:

```python
@workflow.defn
class LongRunningWorkflow:
    @workflow.run
    async def run(self, deployment_id: str) -> str:
        # Start deployment
        await workflow.execute_activity(
            start_deployment_activity,
            deployment_id,
            start_to_close_timeout=timedelta(minutes=10),
        )

        # Wait for deployment to complete (could take hours)
        # Poll every 5 minutes
        while True:
            status = await workflow.execute_activity(
                check_deployment_status_activity,
                deployment_id,
                start_to_close_timeout=timedelta(minutes=1),
            )

            if status["completed"]:
                break

            # Sleep for 5 minutes
            await asyncio.sleep(300)

        # Run post-deployment tasks
        await workflow.execute_activity(
            post_deployment_activity,
            deployment_id,
            start_to_close_timeout=timedelta(minutes=10),
        )

        return "Deployment completed"
```

### Pattern 5: Child Workflows

Start sub-workflows from a parent workflow:

```python
@workflow.defn
class ParentWorkflow:
    @workflow.run
    async def run(self, course_ids: List[str]) -> List[str]:
        results = []

        # Start child workflow for each course
        for course_id in course_ids:
            result = await workflow.execute_child_workflow(
                CreateCourseHierarchyWorkflow.run,
                course_id,
                id=f"course-hierarchy-{course_id}",
                task_queue="computor-tasks",
            )
            results.append(result)

        return results
```

## Starting Workflows from API

### In API Endpoint

```python
# computor-backend/src/computor_backend/api/courses.py
from fastapi import APIRouter, BackgroundTasks
from computor_backend.tasks.temporal_client import get_temporal_client
from computor_backend.tasks.temporal_hierarchy_management import CreateCourseHierarchyWorkflow

router = APIRouter()

@router.post("/courses/{course_id}/setup-gitlab")
async def setup_course_gitlab(
    course_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Setup GitLab hierarchy for course."""
    # Permission check
    course = db.query(Course).filter_by(id=course_id).first()
    if not course:
        raise NotFoundException("Course not found")

    check_course_permissions(permissions, course, "setup", required_role="_lecturer")

    # Start workflow
    client = await get_temporal_client()
    handle = await client.start_workflow(
        CreateCourseHierarchyWorkflow.run,
        course_id,
        id=f"setup-course-{course_id}",
        task_queue="computor-tasks",
    )

    return {
        "workflow_id": handle.id,
        "status": "started",
        "message": "GitLab setup workflow started",
    }
```

### In Business Logic

```python
# computor-backend/src/computor_backend/business_logic/courses.py
from computor_backend.tasks.temporal_client import get_temporal_client
from computor_backend.tasks.temporal_hierarchy_management import CreateCourseHierarchyWorkflow

async def setup_course_gitlab(
    course_id: str,
    permissions: Principal,
    db: Session,
) -> Dict[str, str]:
    """Setup GitLab hierarchy for course."""
    # Validate course exists
    course = db.query(Course).filter_by(id=course_id).first()
    if not course:
        raise NotFoundException("Course not found")

    # Check permissions
    check_course_permissions(permissions, course, "setup", required_role="_lecturer")

    # Start Temporal workflow
    client = await get_temporal_client()
    handle = await client.start_workflow(
        CreateCourseHierarchyWorkflow.run,
        course_id,
        id=f"setup-course-{course_id}",
        task_queue="computor-tasks",
        execution_timeout=timedelta(hours=1),
    )

    return {
        "workflow_id": handle.id,
        "status": "started",
    }
```

## Checking Workflow Status

### Get Workflow Status

```python
@router.get("/workflows/{workflow_id}/status")
async def get_workflow_status(workflow_id: str):
    """Get status of a workflow."""
    client = await get_temporal_client()

    try:
        handle = client.get_workflow_handle(workflow_id)
        result = await handle.describe()

        return {
            "workflow_id": workflow_id,
            "status": result.status.name,
            "start_time": result.start_time,
            "execution_time": result.execution_time,
        }
    except Exception as e:
        raise NotFoundException(f"Workflow {workflow_id} not found")
```

### Wait for Workflow Completion

```python
@router.get("/workflows/{workflow_id}/result")
async def get_workflow_result(workflow_id: str):
    """Wait for workflow to complete and get result."""
    client = await get_temporal_client()

    try:
        handle = client.get_workflow_handle(workflow_id)

        # Wait for completion (with timeout)
        result = await asyncio.wait_for(
            handle.result(),
            timeout=60.0  # 60 seconds
        )

        return {
            "workflow_id": workflow_id,
            "status": "completed",
            "result": result,
        }
    except asyncio.TimeoutError:
        return {
            "workflow_id": workflow_id,
            "status": "running",
            "message": "Workflow still running",
        }
    except Exception as e:
        raise NotFoundException(f"Workflow {workflow_id} not found")
```

## Real Workflow Examples

### Example 1: Student Template Generation

```python
# computor-backend/src/computor_backend/tasks/temporal_student_template_v2.py
@workflow.defn
class GenerateStudentTemplateWorkflow:
    """Generate template repository for student submissions."""

    @workflow.run
    async def run(self, course_content_id: str) -> Dict[str, Any]:
        """Generate student template."""
        # Activity 1: Fetch course content
        content_data = await workflow.execute_activity(
            fetch_course_content_activity,
            course_content_id,
            start_to_close_timeout=timedelta(minutes=2),
        )

        # Activity 2: Create template repository
        repo_data = await workflow.execute_activity(
            create_template_repository_activity,
            content_data,
            start_to_close_timeout=timedelta(minutes=10),
        )

        # Activity 3: Push template files
        await workflow.execute_activity(
            push_template_files_activity,
            {
                "repo_id": repo_data["repo_id"],
                "files": content_data["template_files"],
            },
            start_to_close_timeout=timedelta(minutes=15),
        )

        # Activity 4: Set repository permissions
        await workflow.execute_activity(
            set_repository_permissions_activity,
            {
                "repo_id": repo_data["repo_id"],
                "course_id": content_data["course_id"],
            },
            start_to_close_timeout=timedelta(minutes=5),
        )

        return {
            "repository_id": repo_data["repo_id"],
            "repository_url": repo_data["repository_url"],
        }
```

### Example 2: Submission Testing

```python
# computor-backend/src/computor_backend/tasks/temporal_student_testing.py
@workflow.defn
class TestStudentSubmissionWorkflow:
    """Test student submission against test cases."""

    @workflow.run
    async def run(self, submission_id: str) -> Dict[str, Any]:
        """Test submission."""
        # Activity 1: Fetch submission
        submission_data = await workflow.execute_activity(
            fetch_submission_activity,
            submission_id,
            start_to_close_timeout=timedelta(minutes=2),
        )

        # Activity 2: Extract and validate files
        files = await workflow.execute_activity(
            extract_submission_files_activity,
            submission_data,
            start_to_close_timeout=timedelta(minutes=5),
        )

        # Activity 3: Run tests in parallel
        test_tasks = []
        for test_case in submission_data["test_cases"]:
            task = workflow.execute_activity(
                run_test_case_activity,
                {
                    "submission_id": submission_id,
                    "test_case_id": test_case["id"],
                    "files": files,
                },
                start_to_close_timeout=timedelta(minutes=10),
            )
            test_tasks.append(task)

        test_results = await asyncio.gather(*test_tasks)

        # Activity 4: Store results
        await workflow.execute_activity(
            store_test_results_activity,
            {
                "submission_id": submission_id,
                "results": test_results,
            },
            start_to_close_timeout=timedelta(minutes=2),
        )

        return {
            "submission_id": submission_id,
            "test_results": test_results,
            "passed": all(r["passed"] for r in test_results),
        }
```

## Running Temporal Worker

### Via CLI

```bash
# Start worker
computor worker start

# Start worker with specific queue
computor worker start --queue computor-tasks

# Check worker status
computor worker status
```

### Via Script

```bash
# Using Python directly
cd computor-backend
python -m computor_backend.tasks.temporal_worker
```

### Via Docker

Worker can be included in docker-compose:

```yaml
# docker-compose-dev.yaml
services:
  temporal-worker:
    build: ./computor-backend
    command: python -m computor_backend.tasks.temporal_worker
    environment:
      - TEMPORAL_HOST=temporal
      - TEMPORAL_PORT=7233
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/computor
    depends_on:
      - temporal
      - postgres
```

## Monitoring Workflows

### Temporal UI

Access at http://localhost:8088 when Temporal server is running:

- View all workflows
- See workflow history
- Check activity execution
- Inspect workflow state
- Debug failures

### Logging

Add logging to workflows and activities:

```python
import logging

logger = logging.getLogger(__name__)

@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self, data: str):
        workflow.logger.info(f"Starting workflow with data: {data}")

        try:
            result = await workflow.execute_activity(...)
            workflow.logger.info(f"Activity completed: {result}")
            return result
        except Exception as e:
            workflow.logger.error(f"Workflow failed: {e}")
            raise
```

## Best Practices

### 1. Keep Activities Idempotent

Activities should produce same result if executed multiple times:

```python
# ✅ Good: Idempotent
@activity.defn
async def create_gitlab_group_activity(course_id: str):
    gitlab = get_gitlab_client()

    # Check if group already exists
    existing = gitlab.groups.list(search=f"course-{course_id}")
    if existing:
        return {"group_id": existing[0].id}

    # Create new group
    group = gitlab.groups.create({...})
    return {"group_id": group.id}

# ❌ Bad: Not idempotent
@activity.defn
async def create_gitlab_group_activity(course_id: str):
    gitlab = get_gitlab_client()
    group = gitlab.groups.create({...})  # Fails if already exists
    return {"group_id": group.id}
```

### 2. Set Appropriate Timeouts

```python
# Short activity (API call)
await workflow.execute_activity(
    fetch_data_activity,
    data,
    start_to_close_timeout=timedelta(seconds=30),
)

# Long activity (file processing)
await workflow.execute_activity(
    process_large_file_activity,
    file_path,
    start_to_close_timeout=timedelta(minutes=30),
)
```

### 3. Handle Errors Gracefully

```python
@workflow.defn
class RobustWorkflow:
    @workflow.run
    async def run(self, data: str):
        try:
            result = await workflow.execute_activity(
                risky_activity,
                data,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=workflow.RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=1),
                ),
            )
            return result
        except ActivityError as e:
            # Log and handle error
            workflow.logger.error(f"Activity failed after retries: {e}")
            # Execute compensation logic
            await workflow.execute_activity(cleanup_activity, data)
            raise
```

### 4. Use Structured Data

Pass structured data between activities:

```python
from dataclasses import dataclass

@dataclass
class CourseSetupParams:
    course_id: str
    course_name: str
    gitlab_parent_group_id: str

@workflow.defn
class SetupCourseWorkflow:
    @workflow.run
    async def run(self, params: CourseSetupParams):
        # Type-safe parameter passing
        result = await workflow.execute_activity(
            setup_activity,
            params,
            start_to_close_timeout=timedelta(minutes=10),
        )
        return result
```

## Next Steps

- Learn about [Repository Pattern](09-repository-pattern.md)
- Explore [API Development](10-api-development.md)
- Review [Testing Guide](11-testing-guide.md)

---

**Previous**: [← Database & Migrations](07-database-migrations.md) | **Next**: [Repository Pattern →](09-repository-pattern.md)
