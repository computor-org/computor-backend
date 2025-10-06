"""
CLI commands for managing Temporal workers.
"""

import click
import asyncio
from typing import Optional, List

from computor_backend.tasks.temporal_worker import run_worker
from computor_backend.tasks.temporal_client import (
    get_temporal_client,
    DEFAULT_TASK_QUEUE
)


@click.group()
def worker():
    """Temporal worker management commands."""
    pass


@worker.command()
@click.option('--queues', default=None, help='Comma-separated list of queue names')
def start(queues: str):
    """
    Start a Temporal worker to process workflows.
    
    Examples:
        ctutor worker start
        ctutor worker start --queues=computor-tasks
    """
    click.echo("Starting Temporal worker...")
    
    # Determine queues
    queue_list = None
    if queues:
        queue_list = [q.strip() for q in queues.split(',')]
    
    if queue_list:
        click.echo(f"Processing queues: {', '.join(queue_list)}")
    else:
        # Default to processing default queue
        queue_list = [DEFAULT_TASK_QUEUE]
        click.echo(f"Processing queue: {DEFAULT_TASK_QUEUE}")
    
    try:
        # Run the worker
        asyncio.run(run_worker(queue_list))
    except KeyboardInterrupt:
        click.echo("\nWorker stopped by user")
    except Exception as e:
        click.echo(f"Worker error: {str(e)}")
        raise click.ClickException(str(e))


@worker.command()
def status():
    """Show Temporal worker and server status."""
    click.echo("Temporal Worker Status")
    click.echo("=====================")
    
    async def check_status():
        try:
            client = await get_temporal_client()
            
            # Try to connect to Temporal
            click.echo("✓ Temporal server connection: OK")
            click.echo(f"  Server: {client.service_client.target_host}")
            click.echo(f"  Namespace: {client.namespace}")
            
            # Show task queue
            click.echo("\nTask Queue:")
            click.echo(f"  - {DEFAULT_TASK_QUEUE}")
            
            click.echo("\nNote: Use Temporal Web UI at http://localhost:8088 for detailed worker and workflow status")
            
        except Exception as e:
            click.echo(f"✗ Temporal server connection: ERROR - {str(e)}")
            click.echo("\nTroubleshooting:")
            click.echo("  1. Check if Temporal server is running: docker ps | grep temporal")
            click.echo("  2. Verify environment variables: TEMPORAL_HOST, TEMPORAL_PORT")
            click.echo("  3. Check docker-compose logs: docker-compose logs temporal")
    
    try:
        asyncio.run(check_status())
    except Exception as e:
        click.echo(f"Status check error: {str(e)}")
        raise click.ClickException(str(e))


@worker.command()
@click.argument('task_type')
@click.option('--params', default='{}', help='JSON parameters for the task')
@click.option('--queue', default='computor-tasks', help='Task queue name')
@click.option('--wait', is_flag=True, help='Wait for task completion')
def test_job(task_type: str, params: str, queue: str, wait: bool):
    """
    Submit a test task/workflow for debugging.
    
    Examples:
        ctutor worker test-job example_long_running --params='{"duration": 10}'
        ctutor worker test-job example_data_processing --params='{"data": [1,2,3]}' --wait
    """
    import json
    from computor_backend.tasks import get_task_executor, TaskSubmission
    
    click.echo(f"Submitting test task: {task_type}")
    
    try:
        # Parse parameters
        parameters = json.loads(params)
        
        # Create task submission
        submission = TaskSubmission(
            task_name=task_type,
            parameters=parameters,
            queue=queue
        )
        
        async def submit_and_wait():
            executor = get_task_executor()
            
            # Submit task
            task_id = await executor.submit_task(submission)
            click.echo(f"Task submitted with ID: {task_id}")
            
            if wait:
                click.echo("Waiting for task completion...")
                # Poll for completion
                while True:
                    await asyncio.sleep(2)
                    try:
                        result = await executor.get_task_result(task_id)
                        if result.status in ['FINISHED', 'FAILED']:
                            click.echo(f"\nTask {result.status}")
                            click.echo(f"Result: {json.dumps(result.result, indent=2)}")
                            if result.error:
                                click.echo(f"Error: {result.error}")
                            break
                    except Exception:
                        # Task still running
                        click.echo(".", nl=False)
        
        asyncio.run(submit_and_wait())
        
    except json.JSONDecodeError:
        raise click.ClickException("Invalid JSON parameters")
    except Exception as e:
        click.echo(f"Test job error: {str(e)}")
        raise click.ClickException(str(e))