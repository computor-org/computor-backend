from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, Field, computed_field
from sqlalchemy.orm import Session, selectinload

from ctutor_backend.interface.base import BaseEntityGet, BaseEntityList, EntityInterface, ListQuery
from ctutor_backend.model.message import Message
from ctutor_backend.model.course import CourseMember, SubmissionGroup, CourseGroup, CourseContent

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


def message_search(db: Session, query, params: Optional[MessageQuery]):
    from sqlalchemy import or_

    query = query.options(selectinload(Message.author))
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

    # Special handling: If both submission_group_id and course_content_id are provided,
    # use OR logic to show messages from EITHER source (for unified content view)
    if params.submission_group_id is not None and params.course_content_id is not None:
        query = query.filter(
            or_(
                Message.submission_group_id == params.submission_group_id,
                Message.course_content_id == params.course_content_id
            )
        )
    elif params.submission_group_id is not None:
        query = query.filter(Message.submission_group_id == params.submission_group_id)
    elif params.course_content_id is not None:
        query = query.filter(Message.course_content_id == params.course_content_id)

    if params.course_group_id is not None:
        query = query.filter(Message.course_group_id == params.course_group_id)

    # Handle course_id query
    if params.course_id is not None:
        if params.course_id_all_messages:
            # Return ALL messages related to this course (any target type)
            # This includes: direct course messages, course_member, submission_group, course_group, course_content
            course_filters = []
            course_filters.append(Message.course_id == params.course_id)
            course_filters.append(Message.course_member_id.in_(
                db.query(CourseMember.id).filter(CourseMember.course_id == params.course_id)
            ))
            course_filters.append(Message.submission_group_id.in_(
                db.query(SubmissionGroup.id).filter(SubmissionGroup.course_id == params.course_id)
            ))
            course_filters.append(Message.course_group_id.in_(
                db.query(CourseGroup.id).filter(CourseGroup.course_id == params.course_id)
            ))
            course_filters.append(Message.course_content_id.in_(
                db.query(CourseContent.id).filter(CourseContent.course_id == params.course_id)
            ))
            query = query.filter(or_(*course_filters))
        else:
            # Return ONLY messages where message.course_id == course_id (course-scoped messages only)
            query = query.filter(Message.course_id == params.course_id)

    return query


class MessageInterface(EntityInterface):
    create = MessageCreate
    get = MessageGet
    list = MessageList
    update = MessageUpdate
    query = MessageQuery
    search = message_search
    endpoint = "messages"
    model = Message
    cache_ttl = 60
