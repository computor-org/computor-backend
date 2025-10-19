from typing import Optional, Literal, TYPE_CHECKING
from pydantic import BaseModel, ConfigDict, Field, computed_field

from computor_types.base import BaseEntityGet, BaseEntityList, EntityInterface, ListQuery

MessageScope = Literal["user", "course_member", "submission_group", "course_group", "course_content", "course"]

class MessageAuthor(BaseModel):
    given_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Author's given name")
    family_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Author's family name")

    model_config = ConfigDict(from_attributes=True)

class MessageCreate(BaseModel):
    # author_id is always the current user; set in API
    parent_id: Optional[str] = None
    level: int = Field(default=0)
    title: str
    content: str

    # Targets (at least one should be provided)
    user_id: Optional[str] = None
    course_member_id: Optional[str] = None
    submission_group_id: Optional[str] = None
    course_group_id: Optional[str] = None
    course_content_id: Optional[str] = None
    course_id: Optional[str] = None

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
    author: Optional[MessageAuthor] = Field(None, description="Author details")
    is_read: bool = False
    is_author: bool = Field(False, description="True if the requesting user is the message author")

    user_id: Optional[str] = None
    course_member_id: Optional[str] = None
    submission_group_id: Optional[str] = None
    course_group_id: Optional[str] = None
    course_content_id: Optional[str] = None
    course_id: Optional[str] = None

    @computed_field
    @property
    def scope(self) -> MessageScope:
        """Determine message scope based on target fields (priority order)"""
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
        # Default fallback (shouldn't happen if data is valid)
        return "course"

    model_config = ConfigDict(from_attributes=True)

class MessageList(BaseEntityList):
    id: str
    title: str
    content: str
    level: int
    parent_id: Optional[str] = None
    author_id: str
    author: Optional[MessageAuthor] = Field(None, description="Author details")
    is_read: bool = False
    is_author: bool = Field(False, description="True if the requesting user is the message author")

    user_id: Optional[str] = None
    course_member_id: Optional[str] = None
    submission_group_id: Optional[str] = None
    course_group_id: Optional[str] = None
    course_content_id: Optional[str] = None
    course_id: Optional[str] = None

    @computed_field
    @property
    def scope(self) -> MessageScope:
        """Determine message scope based on target fields (priority order)"""
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
        # Default fallback (shouldn't happen if data is valid)
        return "course"

    model_config = ConfigDict(from_attributes=True)

class MessageQuery(ListQuery):
    id: Optional[str] = None
    parent_id: Optional[str] = None
    author_id: Optional[str] = None
    user_id: Optional[str] = None
    course_member_id: Optional[str] = None
    submission_group_id: Optional[str] = None
    course_group_id: Optional[str] = None
    course_content_id: Optional[str] = None
    course_id: Optional[str] = None
    # Special parameter: when True, returns ALL messages related to the course (any target type)
    course_id_all_messages: Optional[bool] = None
    # Filter by message scope (e.g., "course", "course_content", "submission_group")
    scope: Optional[MessageScope] = None


class MessageInterface(EntityInterface):
    create = MessageCreate
    get = MessageGet
    list = MessageList
    update = MessageUpdate
    query = MessageQuery
