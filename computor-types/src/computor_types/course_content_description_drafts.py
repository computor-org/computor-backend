"""Lena drafts of a unit description, written from the unit's assignments.

A lecturer asks for a draft (``POST /course-contents/{id}/description-draft``)
and polls it (``GET /course-contents/description-drafts/{job_id}``). The Lena
worker claims the job, writes one draft per language and completes it. Nothing
is stored on the unit: the lecturer saves a draft through the ordinary course
content update (computor-org/issues#559).
"""

import re
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# The unit description column is String(4096); a longer draft could not be saved.
DESCRIPTION_DRAFT_MAX_CHARS = 4096
DESCRIPTION_DRAFT_MAX_LANGUAGES = 4
DESCRIPTION_DRAFT_INSTRUCTION_MAX_CHARS = 1000

DescriptionDraftState = Literal["queued", "running", "done", "failed"]
# Fixed codes rather than free text: worker error text could carry model output.
DescriptionDraftError = Literal["too_long", "invalid_output", "model_error"]

_LANGUAGE_PATTERN = r"^[a-z]{2}$"


class DescriptionDraftAvailability(BaseModel):
    """Whether a Lena worker that writes description drafts is running."""

    enabled: bool


class DescriptionDraftRequest(BaseModel):
    """A lecturer's request for a draft description of a unit."""

    model_config = ConfigDict(extra="forbid")

    instruction: Optional[str] = Field(
        default=None, max_length=DESCRIPTION_DRAFT_INSTRUCTION_MAX_CHARS
    )
    # Two-letter codes as in index_<lang>.md. Omitted: every language the
    # assignments are written in, else the course language.
    languages: Optional[List[str]] = Field(
        default=None, min_length=1, max_length=DESCRIPTION_DRAFT_MAX_LANGUAGES
    )

    @field_validator("instruction")
    @classmethod
    def _blank_instruction_is_none(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("languages")
    @classmethod
    def _valid_languages(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return None
        result: List[str] = []
        for code in value:
            code = code.strip().lower()
            if not re.fullmatch(_LANGUAGE_PATTERN, code):
                raise ValueError(f"Invalid language code: {code!r}")
            if code not in result:
                result.append(code)
        return result


class DescriptionDraftJob(BaseModel):
    """The accepted request."""

    id: str
    state: DescriptionDraftState


class DescriptionDraft(BaseModel):
    """One draft description in one language."""

    model_config = ConfigDict(extra="forbid")

    language: str = Field(pattern=_LANGUAGE_PATTERN)
    description: str = Field(min_length=1, max_length=DESCRIPTION_DRAFT_MAX_CHARS)


class DescriptionDraftStatus(BaseModel):
    """State of a draft job, and the drafts once it is done."""

    id: str
    state: DescriptionDraftState
    drafts: Optional[List[DescriptionDraft]] = None
    error: Optional[DescriptionDraftError] = None


# --- Worker side -------------------------------------------------------------


class DescriptionDraftAssignment(BaseModel):
    """What the worker sees of one assignment in the unit."""

    title: str
    content_type: Optional[str] = None
    # Student-visible assignment text (content/index*.md), possibly shortened.
    text: str = ""
    # Language of ``text``; None for a plain index.md.
    text_language: Optional[str] = None


class DescriptionDraftInput(BaseModel):
    """Everything the worker gets for one job. No student or lecturer data."""

    unit_title: str
    unit_description: Optional[str] = None
    course_title: Optional[str] = None
    languages: List[str]
    instruction: Optional[str] = None
    assignments: List[DescriptionDraftAssignment]


class DescriptionDraftClaim(BaseModel):
    """Answer to a worker's claim: a job, or nothing to do."""

    state: Literal["idle", "claimed"]
    id: Optional[str] = None
    lease: Optional[str] = None
    request: Optional[DescriptionDraftInput] = None


class DescriptionDraftCompletion(BaseModel):
    """The worker's result for a claimed job."""

    model_config = ConfigDict(extra="forbid")

    lease: str = Field(pattern=r"^[0-9]{1,20}$")
    state: Literal["done", "failed"]
    drafts: List[DescriptionDraft] = Field(
        default_factory=list, max_length=DESCRIPTION_DRAFT_MAX_LANGUAGES
    )
    error: Optional[DescriptionDraftError] = None
