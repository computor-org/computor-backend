from pydantic import BaseModel, ConfigDict
from typing import Optional
from computor_types.base import BaseEntityGet
from computor_types.course_members import CourseMemberProperties
from computor_types.users import UserList

class TutorCourseMemberCourseContent(BaseModel):
    id: str
    path: str

    model_config = ConfigDict(from_attributes=True)

class TutorCourseMemberGet(BaseModel):
    id: str
    properties: Optional[CourseMemberProperties] = None
    user_id: str
    course_id: str
    course_group_id: Optional[str] = None
    course_role_id: str
    unreviewed_course_contents: list[TutorCourseMemberCourseContent] = []

    user: UserList

    model_config = ConfigDict(from_attributes=True)

class TutorCourseMemberList(BaseModel):
    id: str
    user_id: str
    course_id: str
    course_group_id: Optional[str] = None
    course_role_id: str
    unreviewed: Optional[bool] = None
    # Count of course contents where latest submission is unreviewed
    # (no grades OR latest grade has status = NOT_REVIEWED)
    ungraded_submissions_count: Optional[int] = None
    unread_message_count: Optional[int] = None

    user: UserList

    model_config = ConfigDict(from_attributes=True)