from typing import Literal
from pydantic import BaseModel


class PublicLearningCourse(BaseModel):
    slug: Literal["beginner", "intermediate", "advanced"]
    title: str
    exercises: int
    languages: list[str]
    manifest_url: str
    examples_url: str
    license: str


class PublicLearningResources(BaseModel):
    courses: list[PublicLearningCourse]
    desktop_extension_url: str
    codespaces_url: str
    guide_url: str
    server_execution: Literal["authenticated"] = "authenticated"
