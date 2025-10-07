"""Backend Result interface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.results import (
    ResultInterface as ResultInterfaceBase,
    ResultQuery,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.result import Result


class ResultInterface(ResultInterfaceBase, BackendEntityInterface):
    """Backend-specific Result interface with model attached."""

    model = Result
    endpoint = "results"
    cache_ttl = 300

    @staticmethod
    def search(db: Session, query, params: Optional[ResultQuery]):
        """Apply search filters to result query."""
        if params is None:
            return query

        if params.id is not None:
            query = query.filter(Result.id == params.id)
        if params.submitter_id is not None:
            query = query.filter(Result.submitter_id == params.submitter_id)
        if params.course_member_id is not None:
            query = query.filter(Result.course_member_id == params.course_member_id)
        if params.course_content_id is not None:
            query = query.filter(Result.course_content_id == params.course_content_id)
        if params.course_content_type_id is not None:
            query = query.filter(Result.course_content_type_id == params.course_content_type_id)
        if params.submission_group_id is not None:
            query = query.filter(Result.submission_group_id == params.submission_group_id)
        if params.submission_artifact_id is not None:
            query = query.filter(Result.submission_artifact_id == params.submission_artifact_id)
        if params.execution_backend_id is not None:
            query = query.filter(Result.execution_backend_id == params.execution_backend_id)
        if params.test_system_id is not None:
            query = query.filter(Result.test_system_id == params.test_system_id)
        if params.version_identifier is not None:
            query = query.filter(Result.version_identifier == params.version_identifier)
        if params.status is not None:
            from computor_types.tasks import map_task_status_to_int
            status_int = map_task_status_to_int(params.status)
            query = query.filter(Result.status == status_int)
        if params.result is not None:
            query = query.filter(Result.result == params.result)
        if params.grade is not None:
            query = query.filter(Result.grade == params.grade)
        if params.result_json is not None:
            query = query.filter(Result.result_json == params.result_json)

        # Handle 'latest' flag if needed
        if params.latest:
            # This would require a more complex query to get only the latest result per group
            # For now, just pass through - can be implemented later if needed
            pass

        return query
