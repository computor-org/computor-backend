"""
Example usage of custom endpoint clients.

This demonstrates file operations, task management, system administration,
and other non-CRUD operations.
"""

import asyncio
from pathlib import Path
from computor_client import ComputorClient


async def file_operations_example():
    """Example of file upload/download operations."""

    async with ComputorClient(base_url="http://localhost:8000") as client:
        await client.authenticate(username="admin", password="password")

        print("=== File Operations ===\n")

        # Upload a file
        file_path = Path("example_submission.zip")
        if file_path.exists():
            result = await client.storage.upload(
                file_path=file_path,
                bucket_name="submissions",
                object_key="student123/assignment1.zip",
                metadata={"student_id": "student123", "assignment": "1"}
            )
            print(f"✅ Uploaded file: {result}")

        # Get presigned URL for direct access
        presigned = await client.storage.get_presigned_url(
            bucket_name="submissions",
            object_key="student123/assignment1.zip",
            expiration=3600  # 1 hour
        )
        print(f"🔗 Presigned URL: {presigned.get('url')}")

        # List buckets
        buckets = await client.storage.list_buckets()
        print(f"\n📦 Available buckets: {len(buckets)}")
        for bucket in buckets:
            print(f"   - {bucket.get('name')}")

        # Get bucket statistics
        if buckets:
            stats = await client.storage.get_bucket_stats(buckets[0]['name'])
            print(f"\n📊 Bucket stats: {stats}")

        # Download a file
        downloaded = await client.storage.download(
            object_key="student123/assignment1.zip",
            output_path="./downloads/assignment1.zip"
        )
        print(f"✅ Downloaded {len(downloaded)} bytes")


async def task_management_example():
    """Example of task/workflow management."""

    async with ComputorClient(base_url="http://localhost:8000") as client:
        await client.authenticate(username="admin", password="password")

        print("\n=== Task Management ===\n")

        # Get available task types
        task_types = await client.tasks.get_task_types()
        print(f"📋 Available task types: {len(task_types)}")
        for task_type in task_types:
            print(f"   - {task_type}")

        # Submit a task
        task = await client.tasks.submit_task({
            "task_type": "process_submission",
            "payload": {
                "submission_id": "sub123",
                "test_suite": "basic_tests"
            }
        })
        task_id = task.get('id')
        print(f"\n✅ Submitted task: {task_id}")

        # Poll for status
        for i in range(5):
            await asyncio.sleep(2)  # Wait 2 seconds
            status = await client.tasks.get_status(task_id)
            print(f"   Status check {i+1}: {status.get('state', 'unknown')}")

            if status.get('state') in ['completed', 'failed']:
                break

        # Get result
        result = await client.tasks.get_result(task_id)
        print(f"\n📊 Task result: {result}")

        # Get worker status
        worker_status = await client.tasks.get_worker_status()
        print(f"\n⚙️  Worker status: {worker_status}")


async def system_admin_example():
    """Example of system administration operations."""

    async with ComputorClient(base_url="http://localhost:8000") as client:
        await client.authenticate(username="admin", password="password")

        print("\n=== System Administration ===\n")

        # Deploy organization via Temporal workflow
        org_workflow = await client.system.deploy_organization({
            "name": "Test University",
            "gitlab_group_path": "test-uni",
            "description": "Test organization for demo"
        })
        workflow_id = org_workflow.get('workflow_id')
        print(f"🏢 Organization deployment started: {workflow_id}")

        # Check deployment status
        status = await client.system.get_deployment_status(workflow_id)
        print(f"   Status: {status.get('state', 'unknown')}")

        # Deploy course family
        family_workflow = await client.system.deploy_course_family({
            "organization_id": "org123",
            "name": "Computer Science",
            "gitlab_subgroup_path": "cs"
        })
        print(f"\n🎓 Course family deployment started: {family_workflow.get('workflow_id')}")

        # Generate student template for course
        template_result = await client.system.generate_student_template("course123")
        print(f"\n📝 Student template generation: {template_result}")

        # Check GitLab status for course
        gitlab_status = await client.system.get_gitlab_status("course123")
        print(f"\n🦊 GitLab status: {gitlab_status}")


async def submission_testing_example():
    """Example of submission and testing operations."""

    async with ComputorClient(base_url="http://localhost:8000") as client:
        await client.authenticate(username="student@example.com", password="password")

        print("\n=== Submission & Testing ===\n")

        # Upload submission artifact
        submission_file = Path("my_solution.zip")
        if submission_file.exists():
            artifact = await client.submissions.upload_artifact(
                file_path=submission_file,
                metadata={
                    "course_content_id": "content123",
                    "version": "1.0",
                    "comment": "First submission attempt"
                }
            )
            artifact_id = artifact.get('id')
            print(f"✅ Uploaded submission artifact: {artifact_id}")

            # Run tests on artifact
            test_result = await client.submissions.test_artifact(
                artifact_id,
                test_data={
                    "test_suite": "comprehensive",
                    "timeout": 300
                }
            )
            print(f"🧪 Test created: {test_result.get('id')}")

            # Get test status
            test_id = test_result.get('id')
            status = await client.tests.get_test_status(test_id)
            print(f"   Test status: {status.get('state', 'unknown')}")

            # List all tests for artifact
            all_tests = await client.submissions.list_artifact_tests(artifact_id)
            print(f"\n📋 Total tests run: {len(all_tests)}")

            # Get grades
            grades = await client.submissions.list_grades(artifact_id)
            print(f"📊 Grades received: {len(grades)}")


async def example_management():
    """Example of managing code examples and templates."""

    async with ComputorClient(base_url="http://localhost:8000") as client:
        await client.authenticate(username="lecturer@example.com", password="password")

        print("\n=== Example Management ===\n")

        # Upload new example
        example_zip = Path("python_starter_template.zip")
        if example_zip.exists():
            example = await client.examples.upload_example(
                file_path=example_zip,
                metadata={
                    "name": "Python Starter Template",
                    "language": "python",
                    "version": "1.0.0"
                }
            )
            example_id = example.get('id')
            print(f"✅ Uploaded example: {example_id}")

            # Create a new version
            new_version = await client.examples.create_version(
                example_id,
                version_data={
                    "version": "1.1.0",
                    "changelog": "Added error handling examples",
                    "breaking_changes": False
                }
            )
            print(f"📦 Created version: {new_version.get('version')}")

            # Add dependency
            dependency = await client.examples.add_dependency(
                example_id,
                dependency_data={
                    "dependency_example_id": "pytest_template_id",
                    "version_constraint": ">=1.0.0"
                }
            )
            print(f"🔗 Added dependency: {dependency}")

            # List all versions
            versions = await client.examples.list_versions(example_id)
            print(f"\n📚 Total versions: {len(versions)}")
            for v in versions:
                print(f"   - v{v.get('version')} ({v.get('created_at')})")

            # Download example
            downloaded = await client.examples.download_example(
                example_id,
                output_path="./downloads/template.zip"
            )
            print(f"✅ Downloaded example: {len(downloaded)} bytes")


async def authentication_example():
    """Example of advanced authentication operations."""

    async with ComputorClient(base_url="http://localhost:8000") as client:
        print("\n=== Authentication ===\n")

        # Get available auth providers
        providers = await client.auth.get_providers()
        print(f"🔐 Available auth providers: {len(providers)}")
        for provider in providers:
            print(f"   - {provider.get('name')}")

        # Login with username/password
        auth_result = await client.auth.login(
            username="user@example.com",
            password="password"
        )
        access_token = auth_result.get('access_token')
        refresh_token = auth_result.get('refresh_token')
        print(f"\n✅ Logged in successfully")

        # Set token for future requests
        await client.set_token(access_token)

        # Refresh token
        refreshed = await client.auth.refresh_token(refresh_token)
        print(f"🔄 Refreshed access token")

        # Admin: List plugins (requires admin role)
        try:
            plugins = await client.auth.list_plugins()
            print(f"\n🔌 Auth plugins: {len(plugins)}")
            for plugin in plugins:
                print(f"   - {plugin.get('name')}: {plugin.get('enabled')}")
        except Exception as e:
            print(f"⚠️  Plugin management requires admin role")


async def main():
    """Run all custom endpoint examples."""

    print("=" * 60)
    print("Custom Endpoint Client Examples")
    print("=" * 60)

    examples = [
        ("File Operations", file_operations_example),
        ("Task Management", task_management_example),
        ("System Administration", system_admin_example),
        ("Submission & Testing", submission_testing_example),
        ("Example Management", example_management),
        ("Authentication", authentication_example),
    ]

    for name, example_func in examples:
        try:
            await example_func()
        except Exception as e:
            print(f"\n❌ {name} error: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
