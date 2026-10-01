"""Additive course assistant policy; omitted values inherit, unknown keys survive."""
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict


class AssistantPolicy(BaseModel):
    action_mode: Literal["ask", "edit", "work", "agent"] = "ask"
    completion: Literal["off", "single-line", "multi-line"] = "off"
    independent_check: bool = False
    model_config = ConfigDict(extra="forbid", strict=True)


class AssistantPolicyOverride(BaseModel):
    action_mode: Optional[Literal["ask", "edit", "work", "agent"]] = None
    completion: Optional[Literal["off", "single-line", "multi-line"]] = None
    independent_check: Optional[bool] = None
    model_config = ConfigDict(extra="forbid", strict=True)


def resolve_assistant_policy(course_properties, content_properties) -> Optional[AssistantPolicy]:
    """No stored policy preserves the legacy contract; overrides merge by field."""
    course = (course_properties or {}).get("assistant_policy")
    content = (content_properties or {}).get("assistant_policy")
    if course is None and content is None:
        return None
    base = AssistantPolicy.model_validate(course or {}).model_dump()
    override = AssistantPolicyOverride.model_validate(content or {})
    base.update(override.model_dump(exclude_none=True))
    return AssistantPolicy.model_validate(base)


def merge_assistant_properties(existing: dict, changes: dict) -> dict:
    """Property updates preserve unrelated keys and unspecified policy controls."""
    merged = {**(existing or {}), **changes}
    policy = changes.get("assistant_policy")
    if isinstance(policy, dict):
        merged["assistant_policy"] = {**((existing or {}).get("assistant_policy") or {}), **policy}
    return merged
