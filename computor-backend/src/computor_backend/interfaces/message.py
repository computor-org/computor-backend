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


# Regex pattern for tags: #<non-whitespace> (e.g., #ai, #ai-help, #ai::request)
TAG_PATTERN = re.compile(r'#(\S+)')


def extract_tags_from_title(title: Optional[str]) -> list[str]:
    """Extract tags from title. A tag is # followed by non-whitespace.

    Examples: "#ai" -> ["ai"], "#ai-help #review" -> ["ai-help", "review"]

    Args:
        title: Message title string (None returns empty list)

    Returns:
        List of tag strings (without the # prefix)
    """
    if not title:
        return []
    return TAG_PATTERN.findall(title)


def build_tag_regex(tag: str) -> str:
    """Build a PostgreSQL regex for an exact standalone tag match.

    Matches #<tag> as a standalone token: preceded by whitespace or
    start-of-string, followed by whitespace, punctuation, or end-of-string.
    Does NOT match longer tags (e.g., "ai" won't match "#ai-response").

    Args:
        tag: Tag string without # prefix (e.g., "ai", "ai-help")

    Returns:
        PostgreSQL regex pattern (e.g., "(^|\\s)#ai([\\s,.]|$)")
    """
    escaped = re.escape(tag)
    return f"(^|\\s)#{escaped}([\\s,;.!?]|$)"


def build_tag_prefix_regex(prefix: str) -> str:
    """Build a PostgreSQL regex for a tag prefix match.

    Matches any tag that starts with the given prefix.
    E.g., prefix="ai" matches "#ai", "#ai-help", "#ai-response".

    Args:
        prefix: Tag prefix without # (e.g., "ai" to match any #ai* tag)

    Returns:
        PostgreSQL regex pattern (e.g., "(^|\\s)#ai")
    """
    escaped = re.escape(prefix)
    return f"(^|\\s)#{escaped}"


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

        # Tag filtering (exact standalone match using PostgreSQL regex)
        if params.tags is not None and len(params.tags) > 0:
            tag_conditions = [Message.title.op('~')(build_tag_regex(tag)) for tag in params.tags]
            if params.tags_match_all:
                # AND logic: must match ALL tags
                query = query.filter(and_(*tag_conditions))
            else:
                # OR logic: match ANY tag
                query = query.filter(or_(*tag_conditions))

        # Tag prefix filter (e.g., "ai" matches #ai, #ai-help, #ai-response, etc.)
        if params.tag_scope is not None:
            query = query.filter(Message.title.op('~')(build_tag_prefix_regex(params.tag_scope)))

        return query
