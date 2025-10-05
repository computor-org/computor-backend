"""
Message repository for direct database access with optional caching.

This module provides the MessageRepository class that handles
all database operations for Message entities with transparent caching.
"""

from typing import List, Optional, Set
from sqlalchemy.orm import Session

from .base import BaseRepository
from ..model.message import Message


class MessageRepository(BaseRepository[Message]):
    """
    Repository for Message entity database operations with optional caching.

    Caching is automatic when cache instance is provided to constructor.
    """

    def __init__(self, db: Session, cache=None):
        """
        Initialize message repository.

        Args:
            db: SQLAlchemy session
            cache: Optional Cache instance (enables transparent caching)
        """
        super().__init__(db, Message, cache)

    # ========================================================================
    # Cache configuration
    # ========================================================================

    @property
    def entity_type(self) -> str:
        """Entity type identifier for cache keys."""
        return "message"

    def get_ttl(self) -> int:
        """Messages are frequently created and read - use 5 minute TTL."""
        return 300  # 5 minutes

    def get_entity_tags(self, entity: Message) -> Set[str]:
        """
        Get cache tags for a message.

        Tags:
        - message:{id} - The specific message
        - message:list - All message listings
        - course_content:{content_id} - All messages for this content
        - message:content:{content_id} - Content-specific messages
        - submission_group:{group_id} - All messages for this group
        - message:group:{group_id} - Group-specific messages
        - user:{author_id} - All messages by this author
        - message:author:{author_id} - Author-specific messages
        """
        tags = {
            f"message:{entity.id}",
            "message:list",
        }

        if entity.course_content_id:
            tags.add(f"course_content:{entity.course_content_id}")
            tags.add(f"message:content:{entity.course_content_id}")

        if entity.submission_group_id:
            tags.add(f"submission_group:{entity.submission_group_id}")
            tags.add(f"message:group:{entity.submission_group_id}")

        if entity.author_id:
            tags.add(f"user:{entity.author_id}")
            tags.add(f"message:author:{entity.author_id}")

        return tags

    def get_list_tags(self, **filters) -> Set[str]:
        """Get cache tags for list queries."""
        tags = {"message:list"}

        if "course_content_id" in filters:
            tags.add(f"message:content:{filters['course_content_id']}")
            tags.add(f"course_content:{filters['course_content_id']}")

        if "submission_group_id" in filters:
            tags.add(f"message:group:{filters['submission_group_id']}")
            tags.add(f"submission_group:{filters['submission_group_id']}")

        if "author_id" in filters:
            tags.add(f"message:author:{filters['author_id']}")
            tags.add(f"user:{filters['author_id']}")

        return tags

    # ========================================================================
    # Specialized queries (with caching if enabled)
    # ========================================================================

    def find_by_course_content(self, course_content_id: str) -> List[Message]:
        """
        Find all messages for a course content (cached if enabled).

        Args:
            course_content_id: Course content identifier

        Returns:
            List of messages for the content
        """
        return self.find_by(course_content_id=course_content_id)

    def find_by_submission_group(self, submission_group_id: str) -> List[Message]:
        """
        Find all messages for a submission group (cached if enabled).

        Args:
            submission_group_id: Submission group identifier

        Returns:
            List of messages for the group
        """
        return self.find_by(submission_group_id=submission_group_id)

    def find_by_author(self, author_id: str) -> List[Message]:
        """
        Find all messages by an author (cached if enabled).

        Args:
            author_id: Author user identifier

        Returns:
            List of messages by the author
        """
        return self.find_by(author_id=author_id)

    def find_active_messages(self) -> List[Message]:
        """
        Find all non-archived messages (cached if enabled).

        Returns:
            List of active messages
        """
        return self.find_by(archived_at=None)

    def find_unread_by_user(self, user_id: str, course_content_id: Optional[str] = None) -> List[Message]:
        """
        Find unread messages for a user (cached if enabled).

        Args:
            user_id: User identifier
            course_content_id: Optional course content filter

        Returns:
            List of unread messages
        """
        # Try cache if enabled
        cache_key_suffix = f"unread:{user_id}"
        if course_content_id:
            cache_key_suffix += f":{course_content_id}"

        if self._use_cache():
            key = self.cache.key(self.entity_type, cache_key_suffix)
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return [self._deserialize_entity(item) for item in cached]

        # Query DB
        from ..model.message import MessageRead
        from sqlalchemy import and_

        query = self.db.query(Message).outerjoin(
            MessageRead,
            and_(
                MessageRead.message_id == Message.id,
                MessageRead.reader_user_id == user_id
            )
        ).filter(
            Message.archived_at.is_(None),
            MessageRead.id.is_(None),  # Not read
            Message.author_id != user_id  # Not own messages
        )

        if course_content_id:
            query = query.filter(Message.course_content_id == course_content_id)

        entities = query.all()

        # Cache if enabled
        if self._use_cache():
            key = self.cache.key(self.entity_type, cache_key_suffix)
            serialized = [self._serialize_entity(e) for e in entities]
            cache_tags = {
                "message:list",
                f"user:{user_id}",
                f"message:unread:{user_id}"
            }
            if course_content_id:
                cache_tags.add(f"message:content:{course_content_id}")

            self.cache.set_with_tags(
                key=key,
                payload=serialized,
                tags=cache_tags,
                ttl=self.get_ttl()
            )

        return entities
