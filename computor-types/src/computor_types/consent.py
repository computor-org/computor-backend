"""DTOs for the GDPR consent gate.

Note on wording: depending on the legal basis declared in the privacy policy,
"consent" here may be an informed acknowledgment (contract / public task /
legitimate interest) rather than consent-as-legal-basis. The mechanism is the
same; the UI copy must match the policy text.
"""
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ConsentStatusGet(BaseModel):
    """Answer to 'may this user pass the consent gate right now?'."""
    required_version: Optional[str] = Field(
        None, description="Current policy version; null if no policy is configured (gate inactive)"
    )
    has_consented: bool
    granted_at: Optional[datetime] = None


class ConsentCreate(BaseModel):
    policy_version: str = Field(..., description="Must match the current policy version")
    purposes: Optional[Dict[str, bool]] = Field(
        None, description="Granular opt-in purposes, if the policy defines any"
    )


class PolicyTextGet(BaseModel):
    version: str
    lang: str = Field(..., description="Language actually served (after fallback)")
    languages: List[str] = Field(default_factory=list, description="Languages available for this version")
    effective_from: Optional[datetime] = None
    content: str = Field(..., description="Markdown text of the privacy notice")


class PolicyVersionCreate(BaseModel):
    """Admin: publish a new policy version (append-only; texts are write-once)."""
    version: str = Field(..., min_length=1, max_length=64, description="e.g. 2026-07-04")
    effective_from: Optional[datetime] = Field(
        None, description="When this version becomes current; defaults to now. May be in the future (scheduled)."
    )
    texts: Dict[str, str] = Field(
        ..., min_length=1, description="Mapping of language code -> Markdown notice text, e.g. {'de': ..., 'en': ...}"
    )


class PolicyVersionGet(BaseModel):
    id: str
    version: str
    languages: List[str] = []
    effective_from: datetime
    content_hashes: Optional[Dict[str, str]] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
