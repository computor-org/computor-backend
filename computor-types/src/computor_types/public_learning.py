from typing import Literal, Optional
from pydantic import BaseModel, Field


class PublicLearningContentSummary(BaseModel):
    """One learner-visible node in a public course outline."""

    id: str
    title: str
    description: Optional[str] = None
    path: str
    parent_path: Optional[str] = None
    depth: int = 0
    position: float
    kind: str
    type_title: Optional[str] = None
    color: Optional[str] = None
    is_submittable: bool = False


class PublicLearningCourseOutline(BaseModel):
    """Anonymous pedagogical tree for one public course."""

    id: str
    title: str
    description: Optional[str] = None
    language_code: Optional[str] = None
    contents: list[PublicLearningContentSummary] = Field(default_factory=list)
    welcome_content_id: Optional[str] = None
    first_exercise_id: Optional[str] = None
    exercise_count: int = 0
    unit_count: int = 0


class PublicLearningContentGet(BaseModel):
    """Rendered-source payload for one anonymous learner-visible item."""

    id: str
    course_id: str
    title: str
    description: Optional[str] = None
    path: str
    kind: str
    is_submittable: bool
    markdown: str = ""
    selected_language: Optional[str] = None
    available_languages: list[str] = Field(default_factory=list)


class PublicLearningResources(BaseModel):
    """Independent runtimes and provenance, not course navigation.

    Course discovery comes from GET /public/courses and the native reader
    endpoints.  GitHub remains an optional source/reuse destination only.
    """

    desktop_extension_url: str
    codespaces_url: str
    guide_url: str
    source_url: str
    server_execution: Literal["authenticated"] = "authenticated"
