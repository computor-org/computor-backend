"""Backend Message interface with SQLAlchemy model."""

import re
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, not_, exists

from computor_types.messages import (
    MessageInterface as MessageInterfaceBase,
    MessageQuery,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.message import Message, MessageRead


# Regex pattern for tags: #scope::value (alphanumeric, hyphens, underscores)
TAG_PATTERN = re.compile(r'#([a-zA-Z0-9_-]+)::([a-zA-Z0-9_-]+)')


def extract_tags_from_title(title: str) -> list[tuple[str, str]]:
    """Extract tags from title in format #scope::value.

    Args:
        title: Message title string

    Returns:
        List of (scope, value) tuples
    """
    return TAG_PATTERN.findall(title)


def build_tag_filter(tag: str) -> str:
    """Build a SQL LIKE pattern for a tag.

    Args:
        tag: Tag in format "scope::value"

    Returns:
        Pattern for LIKE query (e.g., "%#ai::request%")
    """
    return f"%#{tag}%"


def build_tag_scope_filter(scope: str) -> str:
    """Build a SQL LIKE pattern for a tag scope wildcard.

    Args:
        scope: Tag scope (e.g., "ai" to match any #ai::* tag)

    Returns:
        Pattern for LIKE query (e.g., "%#ai::%")
    """
    return f"%#{scope}::%"


class MessageInterface(MessageInterfaceBase, BackendEntityInterface):
    """Backend-specific Message interface with model attached."""

    model = Message
    endpoint = "messages"
    cache_ttl = 300

    @staticmethod
    def search(db: Session, query, params: Optional[MessageQuery], reader_user_id: Optional[str] = None):
        """Apply search filters to message query.

        Args:
            db: Database session
            query: SQLAlchemy query object
            params: Query parameters
            reader_user_id: Current user ID for unread filtering (optional)
        """
        if params is None:
            return query

        if params.id is not None:
            query = query.filter(Message.id == params.id)
        if params.parent_id is not None:
            query = query.filter(Message.parent_id == params.parent_id)
        if params.author_id is not None:
            query = query.filter(Message.author_id == params.author_id)

        # Target filters (hierarchy order)
        if params.organization_id is not None:
            query = query.filter(Message.organization_id == params.organization_id)
        if params.course_family_id is not None:
            query = query.filter(Message.course_family_id == params.course_family_id)
        if params.course_id is not None:
            query = query.filter(Message.course_id == params.course_id)
        if params.course_content_id is not None:
            query = query.filter(Message.course_content_id == params.course_content_id)
        if params.course_group_id is not None:
            query = query.filter(Message.course_group_id == params.course_group_id)
        if params.submission_group_id is not None:
            query = query.filter(Message.submission_group_id == params.submission_group_id)
        if params.course_member_id is not None:
            query = query.filter(Message.course_member_id == params.course_member_id)
        if params.user_id is not None:
            query = query.filter(Message.user_id == params.user_id)

        # Scope filter (filter by message scope type)
        if params.scope is not None:
            if params.scope == "global":
                query = query.filter(
                    and_(
                        Message.organization_id.is_(None),
                        Message.course_family_id.is_(None),
                        Message.course_id.is_(None),
                        Message.course_content_id.is_(None),
                        Message.course_group_id.is_(None),
                        Message.submission_group_id.is_(None),
                        Message.course_member_id.is_(None),
                        Message.user_id.is_(None),
                    )
                )
            elif params.scope == "organization":
                query = query.filter(Message.organization_id.isnot(None))
            elif params.scope == "course_family":
                query = query.filter(Message.course_family_id.isnot(None))
            elif params.scope == "course":
                query = query.filter(Message.course_id.isnot(None))
            elif params.scope == "course_content":
                query = query.filter(Message.course_content_id.isnot(None))
            elif params.scope == "course_group":
                query = query.filter(Message.course_group_id.isnot(None))
            elif params.scope == "submission_group":
                query = query.filter(Message.submission_group_id.isnot(None))
            elif params.scope == "course_member":
                query = query.filter(Message.course_member_id.isnot(None))
            elif params.scope == "user":
                query = query.filter(Message.user_id.isnot(None))

        # Datetime boundary filters
        if params.created_after is not None:
            query = query.filter(Message.created_at >= params.created_after)
        if params.created_before is not None:
            query = query.filter(Message.created_at <= params.created_before)

        # Unread filter (requires reader_user_id)
        if params.unread is not None and reader_user_id is not None:
            read_exists = exists().where(
                and_(
                    MessageRead.message_id == Message.id,
                    MessageRead.reader_user_id == reader_user_id
                )
            )
            if params.unread:
                # Unread only: no MessageRead record exists for this user
                query = query.filter(not_(read_exists))
            else:
                # Read only: MessageRead record exists for this user
                query = query.filter(read_exists)

        # Tag filtering
        if params.tags is not None and len(params.tags) > 0:
            tag_conditions = [Message.title.ilike(build_tag_filter(tag)) for tag in params.tags]
            if params.tags_match_all:
                # AND logic: must match ALL tags
                query = query.filter(and_(*tag_conditions))
            else:
                # OR logic: match ANY tag
                query = query.filter(or_(*tag_conditions))

        # Tag scope wildcard filter
        if params.tag_scope is not None:
            query = query.filter(Message.title.ilike(build_tag_scope_filter(params.tag_scope)))

        return query
