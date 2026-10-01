"""A full cold template refresh must fit inside its submitted Temporal deadline."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from computor_types.tasks import TaskSubmission

from computor_backend.tasks.registry import task_registry
from computor_backend.tasks.temporal_coder_setup import (
    BuildWorkspaceImagesWorkflow,
    PushCoderTemplatesWorkflow,
)
from computor_backend.tasks.temporal_executor import TemporalTaskExecutor


@pytest.mark.asyncio
async def test_six_serial_cold_templates_can_complete_with_one_retry_per_step():
    # Independent duration scenario: each of the six image builds uses its
    # second 60-minute attempt, then push and rollout each use a second
    # 10-minute attempt. Discovery and cleanup add another 11 minutes.
    six_templates = ["bash", "jupyter", "matlab-ui", "matlab-vscode", "ubuntu-desktop", "vscode"]
    planned_duration = 6 * (2 * timedelta(minutes=60) + 2 * timedelta(minutes=10)
                            + 2 * timedelta(minutes=10)) + timedelta(minutes=11)
    client = AsyncMock()
    submission = TaskSubmission(
        task_name="push_coder_templates",
        parameters={"build_images": True, "templates": six_templates},
    )

    with patch("computor_backend.tasks.temporal_executor.get_temporal_client", return_value=client), \
         patch.object(task_registry, "get_task", return_value=PushCoderTemplatesWorkflow):
        await TemporalTaskExecutor().submit_task(submission)

    start = client.start_workflow.call_args.kwargs
    assert start["workflow"] is PushCoderTemplatesWorkflow
    assert start["arg"] == submission.parameters
    assert planned_duration + timedelta(minutes=30) < start["execution_timeout"]
    assert start["execution_timeout"] < timedelta(days=2)


@pytest.mark.asyncio
async def test_six_serial_image_builds_can_complete_with_one_retry_each():
    # The admin build-only endpoint also submits a serial workflow. On a cold
    # host, each image may need both allowed 60-minute attempts.
    six_templates = ["bash", "jupyter", "matlab-ui", "matlab-vscode", "ubuntu-desktop", "vscode"]
    planned_duration = len(six_templates) * 2 * timedelta(minutes=60)
    client = AsyncMock()
    submission = TaskSubmission(
        task_name="build_workspace_images",
        parameters={"templates": six_templates},
    )

    with patch("computor_backend.tasks.temporal_executor.get_temporal_client", return_value=client), \
         patch.object(task_registry, "get_task", return_value=BuildWorkspaceImagesWorkflow):
        await TemporalTaskExecutor().submit_task(submission)

    start = client.start_workflow.call_args.kwargs
    assert start["workflow"] is BuildWorkspaceImagesWorkflow
    assert start["arg"] == submission.parameters
    assert planned_duration + timedelta(minutes=30) < start["execution_timeout"]
    assert start["execution_timeout"] < timedelta(days=1)
