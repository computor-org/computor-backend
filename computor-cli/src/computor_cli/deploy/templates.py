"""Generate GitLab student template repositories for deployed courses."""

import click

from computor_cli.auth import get_computor_client
from computor_client import SyncComputorClient
from computor_cli.config import CLIAuthConfig
from computor_cli.utils import run_async

from computor_types.deployment_config import ComputorDeploymentConfig
from computor_types.courses import CourseQuery
from computor_types.organizations import OrganizationQuery
from computor_types.course_families import CourseFamilyQuery


def _generate_student_templates(config: ComputorDeploymentConfig, auth: CLIAuthConfig):
    """Generate GitLab student template repositories for courses with contents."""
    

    client = run_async(get_computor_client(auth))

    click.echo(f"\n🚀 Generating student template repositories...")
    
    # Get API clients
    org_client = client.organizations
    family_client = client.course_families
    course_client = client.courses
    custom_client = SyncComputorClient.from_client(client)
    
    generated_count = 0
    failed_count = 0
    
    # Process each organization
    for org_config in config.organizations:
        # Find the organization
        orgs = run_async(org_client.list(OrganizationQuery(path=org_config.path)))
        if not orgs:
            continue
        org = orgs[0]
        
        # Process each course family
        for family_config in org_config.course_families:
            # Find the course family
            families = run_async(family_client.list(CourseFamilyQuery(
                organization_id=str(org.id),
                path=family_config.path
            )))
            if not families:
                continue
            family = families[0]
            
            # Process each course
            for course_config in family_config.courses:
                # Only process courses that have contents defined
                if not course_config.contents:
                    continue
                    
                # Find the course
                courses = run_async(course_client.list(CourseQuery(
                    course_family_id=str(family.id),
                    path=course_config.path
                )))
                if not courses:
                    continue
                course = courses[0]
                
                # First, generate assignments repository (initial populate from Example Library)
                try:
                    click.echo(f"  Initializing assignments repo for: {course_config.name} ({course_config.path})")
                    custom_client.create(
                        f"system/courses/{course.id}/generate-assignments",
                        {
                            "all": True,
                            "overwrite_strategy": "force_update"
                        }
                    )
                except Exception as e:
                    click.echo(f"    ⚠️  Failed to initialize assignments: {e}")
                
                # Then, generate student template for this course
                try:
                    click.echo(f"  Generating template for: {course_config.name} ({course_config.path})")
                    result = custom_client.create(f"system/courses/{course.id}/generate-student-template", {})
                    
                    if result and result.get('workflow_id'):
                        click.echo(f"    ✅ Template generation started (workflow: {result.get('workflow_id')})")
                        # Wait for completion before proceeding to user repo creation
                        workflow_id = result.get('workflow_id')
                        import time
                        for _ in range(120):  # up to 10 minutes, poll every 5s
                            time.sleep(5)
                            try:
                                task_info = custom_client.get(f"tasks/{workflow_id}/status")
                                status = (task_info or {}).get('status')
                                if status in ['finished', 'failed', 'cancelled']:
                                    click.echo(f"    ▶ Template generation status: {status}")
                                    break
                            except Exception:
                                # Keep trying a bit
                                continue
                        generated_count += 1
                    else:
                        click.echo(f"    ⚠️  Template generation response unclear")
                        failed_count += 1
                except Exception as e:
                    click.echo(f"    ❌ Failed to generate template: {e}")
                    failed_count += 1
    
    # Summary
    if generated_count > 0 or failed_count > 0:
        click.echo(f"\n📊 Student Template Generation Summary:")
        click.echo(f"  ✅ Successfully initiated: {generated_count} templates")
        if failed_count > 0:
            click.echo(f"  ❌ Failed: {failed_count} templates")
