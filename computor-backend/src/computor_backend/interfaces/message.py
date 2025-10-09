"""Backend Message interface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.messages import (
    MessageInterface as MessageInterfaceBase,
    MessageQuery,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.message import Message


class MessageInterface(MessageInterfaceBase, BackendEntityInterface):
    """Backend-specific Message interface with model attached."""

    model = Message
    endpoint = "messages"
    cache_ttl = 300

    @staticmethod
    def search(db: Session, query, params: Optional[MessageQuery]):
        """Apply search filters to message query."""
        if params is None:
            return query

        if params.id is not None:
            query = query.filter(Message.id == params.id)
        if params.parent_id is not None:
            query = query.filter(Message.parent_id == params.parent_id)
        if params.author_id is not None:
            query = query.filter(Message.author_id == params.author_id)
        if params.user_id is not None:
            query = query.filter(Message.user_id == params.user_id)
        if params.course_member_id is not None:
            query = query.filter(Message.course_member_id == params.course_member_id)
        if params.submission_group_id is not None:
            query = query.filter(Message.submission_group_id == params.submission_group_id)
        if params.course_group_id is not None:
            query = query.filter(Message.course_group_id == params.course_group_id)
        if params.course_content_id is not None:
            query = query.filter(Message.course_content_id == params.course_content_id)
        if params.course_id is not None:
            query = query.filter(Message.course_id == params.course_id)

        # Handle scope parameter if needed
        if params.scope is not None:
            # Scope filters would go here based on MessageScope enum
            pass

        return query
