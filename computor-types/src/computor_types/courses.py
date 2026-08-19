from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional


    
from computor_types.course_families import CourseFamilyGet
from computor_types.gitlab import GitLabConfig, GitLabConfigGet
from computor_types.base import BaseEntityGet, EntityInterface, ListQuery

from computor_types.custom_types import Ltree

class CourseProperties(BaseModel):
    gitlab: Optional[GitLabConfig] = None
    
    model_config = ConfigDict(
        extra='allow',
    )

class CoursePropertiesGet(BaseModel):
    gitlab: Optional[GitLabConfigGet] = None
    
    model_config = ConfigDict(
        extra='allow',
    )
    
class CourseCreate(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    path: str
    course_family_id: str
    language_code: Optional[str] = None
    properties: Optional[CourseProperties] = None
    # Course-wide defaults for the per-assignment test/submission budgets.
    # None means "no default"; a course content value overrides these, and a
    # submission group value overrides both.
    max_test_runs: Optional[int] = None
    max_submissions: Optional[int] = None
    # Root of the content-visibility chain (issue #338). None inherits and
    # means visible; False hides every course content in this course from
    # students. Unlike the budgets above this is a veto, not a fallback: a
    # course content cannot re-grant visibility the course denied.
    visible: Optional[bool] = None

class CourseGet(BaseEntityGet,CourseCreate):
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    path: str
    course_family_id: str
    organization_id: str
    language_code: Optional[str] = None
    properties: Optional[CoursePropertiesGet] = None
    # Course-wide defaults for the per-assignment test/submission budgets.
    # None means "no default"; a course content value overrides these, and a
    # submission group value overrides both.
    max_test_runs: Optional[int] = None
    max_submissions: Optional[int] = None
    # Root of the content-visibility chain (issue #338). None inherits and
    # means visible; False hides every course content in this course from
    # students. Unlike the budgets above this is a veto, not a fallback: a
    # course content cannot re-grant visibility the course denied.
    visible: Optional[bool] = None

    course_family: Optional[CourseFamilyGet] = None

    @field_validator('path', mode='before')
    @classmethod
    def cast_str_to_ltree(cls, value):
        return str(value)

    model_config = ConfigDict(from_attributes=True)

class CourseList(BaseModel):
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    course_family_id: Optional[str] = None
    organization_id: Optional[str] = None
    path: str
    language_code: Optional[str] = None
    properties: Optional[CoursePropertiesGet] = None
    # Course-wide defaults for the per-assignment test/submission budgets.
    # None means "no default"; a course content value overrides these, and a
    # submission group value overrides both.
    max_test_runs: Optional[int] = None
    max_submissions: Optional[int] = None
    # Root of the content-visibility chain (issue #338). None inherits and
    # means visible; False hides every course content in this course from
    # students. Unlike the budgets above this is a veto, not a fallback: a
    # course content cannot re-grant visibility the course denied.
    visible: Optional[bool] = None

    @field_validator('path', mode='before')
    @classmethod
    def cast_str_to_ltree(cls, value):
        return str(value)

    model_config = ConfigDict(from_attributes=True)

class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    language_code: Optional[str] = None
    # Course-wide defaults for the per-assignment test/submission budgets.
    # None means "no default"; a course content value overrides these, and a
    # submission group value overrides both.
    max_test_runs: Optional[int] = None
    max_submissions: Optional[int] = None
    # Tri-state (issue #338). The backend applies updates with
    # ``model_dump(exclude_unset=True)``, so omitting the key leaves the course
    # alone while sending an explicit ``null`` resets it to "inherit".
    visible: Optional[bool] = None


class CourseQuery(ListQuery):
    id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    path: Optional[str] = None
    course_family_id: Optional[str] = None
    organization_id: Optional[str] = None
    language_code: Optional[str] = None
    provider_url: Optional[str] = None
    full_path: Optional[str] = None
    max_test_runs: Optional[int] = None
    max_submissions: Optional[int] = None
    visible: Optional[bool] = None


class CourseInterface(EntityInterface):
    create = CourseCreate
    get = CourseGet
    list = CourseList
    update = CourseUpdate
    query = CourseQuery
