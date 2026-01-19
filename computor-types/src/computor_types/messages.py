from datetime import datetime
from typing import Optional, Literal, List, Protocol
from pydantic import BaseModel, ConfigDict, Field, computed_field

from computor_types.base import BaseEntityGet, BaseEntityList, EntityInterface, ListQuery


class MessageTargetProtocol(Protocol):
    """
    Protocol for objects that have message target fields.

    Used for duck-typing SQLAlchemy models and Pydantic DTOs
    when determining WebSocket broadcast channels.
    """
    submission_group_id: Optional[str]
    course_content_id: Optional[str]
    course_group_id: Optional[str]
    course_id: Optional[str]
    course_family_id: Optional[str]
    organization_id: Optional[str]

MessageScope = Literal[
    "global",           # All users in the system can see
    "organization",     # Organization-level message
    "course_family",    # Course family-level message
    "course",           # Course-level message
    "course_content",   # Attached to specific course content
    "course_group",     # Attached to a course group
    "submission_group", # Attached to a submission group
    "course_member",    # Direct message to a course member
    "user",             # Direct message to a user (outside course context)
]


class MessageAuthor(BaseModel):
    """Author information for a message."""
    id: str = Field(..., description="User ID of the author")
    given_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Author's given name")
    family_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Author's family name")

    model_config = ConfigDict(from_attributes=True)


class MessageAuthorCourseMember(BaseModel):
    """Course member context for the message author (when message is in a course context)."""
    id: str = Field(..., description="Course member ID")
    course_role_id: str = Field(..., description="Role of the author in the course (e.g., '_student', '_tutor', '_lecturer')")
    course_id: str = Field(..., description="Course ID")

    model_config = ConfigDict(from_attributes=True)

class MessageCreate(BaseModel):
    # author_id is always the current user; set in API
    parent_id: Optional[str] = None
    level: int = Field(default=0)
    title: str
    content: str

    # Targets (at least one should be provided, or none for global)
    # Hierarchy: organization > course_family > course > course_content/course_group > submission_group > course_member > user
    organization_id: Optional[str] = Field(None, description="Organization-level message")
    course_family_id: Optional[str] = Field(None, description="Course family-level message")
    course_id: Optional[str] = Field(None, description="Course-level message")
    course_content_id: Optional[str] = Field(None, description="Course content-level message")
    course_group_id: Optional[str] = Field(None, description="Course group-level message")
    submission_group_id: Optional[str] = Field(None, description="Submission group-level message")
    course_member_id: Optional[str] = Field(None, description="Direct message to a course member")
    user_id: Optional[str] = Field(None, description="Direct message to a user (outside course context)")

class MessageUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

class MessageGet(BaseEntityGet):
    id: str
    title: str
    content: str
    level: int
    parent_id: Optional[str] = None
    author_id: str
    author: Optional[MessageAuthor] = Field(None, description="Author details (user info)")
    author_course_member: Optional[MessageAuthorCourseMember] = Field(
        None, description="Author's course member context (only for course-scoped messages)"
    )
    is_read: bool = False
    is_author: bool = Field(False, description="True if the requesting user is the message author")
    is_deleted: bool = Field(False, description="True if the message has been soft-deleted")
    deleted_by: Optional[str] = Field(None, description="Who deleted the message (author/moderator/admin)")

    # Target fields (determines scope)
    organization_id: Optional[str] = None
    course_family_id: Optional[str] = None
    course_id: Optional[str] = None
    course_content_id: Optional[str] = None
    course_group_id: Optional[str] = None
    submission_group_id: Optional[str] = None
    course_member_id: Optional[str] = None
    user_id: Optional[str] = None

    @computed_field
    @property
    def scope(self) -> MessageScope:
        """Determine message scope based on target fields (priority order: most specific first)"""
        if self.user_id is not None:
            return "user"
        if self.course_member_id is not None:
            return "course_member"
        if self.submission_group_id is not None:
            return "submission_group"
        if self.course_group_id is not None:
            return "course_group"
        if self.course_content_id is not None:
            return "course_content"
        if self.course_id is not None:
            return "course"
        if self.course_family_id is not None:
            return "course_family"
        if self.organization_id is not None:
            return "organization"
        # No target set = global message
        return "global"

    model_config = ConfigDict(from_attributes=True)

class MessageList(BaseEntityList):
    id: str
    title: str
    content: str
    level: int
    parent_id: Optional[str] = None
    author_id: str
    author: Optional[MessageAuthor] = Field(None, description="Author details (user info)")
    author_course_member: Optional[MessageAuthorCourseMember] = Field(
        None, description="Author's course member context (only for course-scoped messages)"
    )
    is_read: bool = False
    is_author: bool = Field(False, description="True if the requesting user is the message author")
    is_deleted: bool = Field(False, description="True if the message has been soft-deleted")
    deleted_by: Optional[str] = Field(None, description="Who deleted the message (author/moderator/admin)")

    # Target fields (determines scope)
    organization_id: Optional[str] = None
    course_family_id: Optional[str] = None
    course_id: Optional[str] = None
    course_content_id: Optional[str] = None
    course_group_id: Optional[str] = None
    submission_group_id: Optional[str] = None
    course_member_id: Optional[str] = None
    user_id: Optional[str] = None

    @computed_field
    @property
    def scope(self) -> MessageScope:
        """Determine message scope based on target fields (priority order: most specific first)"""
        if self.user_id is not None:
            return "user"
        if self.course_member_id is not None:
            return "course_member"
        if self.submission_group_id is not None:
            return "submission_group"
        if self.course_group_id is not None:
            return "course_group"
        if self.course_content_id is not None:
            return "course_content"
        if self.course_id is not None:
            return "course"
        if self.course_family_id is not None:
            return "course_family"
        if self.organization_id is not None:
            return "organization"
        # No target set = global message
        return "global"

    model_config = ConfigDict(from_attributes=True)

class MessageQuery(ListQuery):
    id: Optional[str] = None
    parent_id: Optional[str] = None
    author_id: Optional[str] = None

    # Target filters
    organization_id: Optional[str] = None
    course_family_id: Optional[str] = None
    course_id: Optional[str] = None
    course_content_id: Optional[str] = None
    course_group_id: Optional[str] = None
    submission_group_id: Optional[str] = None
    course_member_id: Optional[str] = None
    user_id: Optional[str] = None

    # Special parameter: when True, returns ALL messages related to the course (any target type)
    course_id_all_messages: Optional[bool] = None
    # Filter by message scope (e.g., "global", "organization", "course", "course_content", "submission_group")
    scope: Optional[MessageScope] = None

    # Datetime boundary filters (based on created_at)
    created_after: Optional[datetime] = Field(
        None, description="Filter messages created at or after this datetime (inclusive)"
    )
    created_before: Optional[datetime] = Field(
        None, description="Filter messages created at or before this datetime (inclusive)"
    )

    # Unread filter (from current API user's perspective)
    unread: Optional[bool] = Field(
        None, description="Filter by read status: True = unread only, False = read only, None = all"
    )

    # Tag filtering (tags in title with format #scope::value)
    tags: Optional[List[str]] = Field(
        None, description="Filter by tags in title (e.g., ['ai::request', 'priority::high'])"
    )
    tags_match_all: Optional[bool] = Field(
        True, description="True = must match ALL tags (AND), False = match ANY tag (OR)"
    )
    tag_scope: Optional[str] = Field(
        None, description="Filter by tag scope prefix (e.g., 'ai' matches any #ai::* tag)"
    )


class MessageInterface(EntityInterface):
    create = MessageCreate
    get = MessageGet
    list = MessageList
    update = MessageUpdate
    query = MessageQuery
