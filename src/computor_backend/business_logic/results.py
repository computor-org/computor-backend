"""Business logic for test results management."""
import logging
from uuid import UUID

from sqlalchemy.orm import Session

from computor_backend.api.exceptions import NotFoundException
from computor_backend.model.result import Result
from computor_backend.permissions.core import check_permissions
from computor_backend.permissions.principal import Principal
from computor_types.tasks import TaskStatus, map_int_to_task_status
from computor_backend.tasks import get_task_executor

logger = logging.getLogger(__name__)


async def get_result_status(
    result_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> TaskStatus:
    """Fetch the latest task status for a result from the task executor."""

    result = (
        check_permissions(permissions, Result, "get", db)
        .filter(Result.id == result_id)
        .first()
    )

    if result is None:
        raise NotFoundException()

    if not result.test_system_id:
        return map_int_to_task_status(result.status)

    try:
        task_executor = get_task_executor()
        task_info = await task_executor.get_task_status(result.test_system_id)
        return task_info.status
    except Exception as e:
        logger.warning(f"Failed to get task status for result {result_id}: {e}")
        return TaskStatus.FAILED
