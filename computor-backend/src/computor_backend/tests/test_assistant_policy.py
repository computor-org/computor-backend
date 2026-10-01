"""Synthetic contract tests for course inheritance and backwards compatibility."""
import pytest
from pydantic import ValidationError
from computor_types.assistant_policy import AssistantPolicy, resolve_assistant_policy, merge_assistant_properties
from computor_types.courses import CourseProperties, CourseUpdate
from computor_types.course_contents import CourseContentProperties

pytestmark = pytest.mark.unit


def test_legacy_course_has_no_new_policy():
    assert resolve_assistant_policy({}, {}) is None
    assert resolve_assistant_policy(None, None) is None
    assert "properties" not in CourseUpdate(title="Changed").model_dump(exclude_unset=True)


def test_partial_override_preserves_independent_controls():
    course = {"assistant_policy": {"action_mode": "ask", "completion": "single-line"}}
    resolved = resolve_assistant_policy(course, {"assistant_policy": {"action_mode": "edit"}})
    assert resolved.model_dump() == {
        "action_mode": "edit", "completion": "single-line", "independent_check": False,
    }
    check = resolve_assistant_policy(course, {"assistant_policy": {"independent_check": True}})
    assert check.independent_check is True
    assert check.action_mode == "ask"
    assert check.completion == "single-line"


def test_null_override_fields_inherit():
    resolved = resolve_assistant_policy(
        {"assistant_policy": {"completion": "off"}},
        {"assistant_policy": {"completion": None, "independent_check": True}},
    )
    assert resolved.completion == "off"
    assert resolved.independent_check is True


def test_unknown_properties_round_trip_and_unrelated_updates_do_not_erase_policy():
    props = {"assistant_policy": {"action_mode": "ask", "completion": "off"},
             "custom_course_data": {"label": "public fixture"}}
    dto = CourseUpdate(properties=props)
    encoded = dto.model_dump(exclude_unset=True)["properties"]
    assert encoded["custom_course_data"] == props["custom_course_data"]
    assert encoded["assistant_policy"]["action_mode"] == "ask"
    assert CourseProperties.model_validate(encoded).assistant_policy.completion == "off"


@pytest.mark.parametrize("policy", [
    {"action_mode": "yolo"}, {"completion": "on"}, {"independent_check": "false"},
    {"allow_shell": True},
])
def test_invalid_policy_is_rejected_at_storage_boundaries(policy):
    with pytest.raises(ValidationError):
        CourseProperties(assistant_policy=policy)
    with pytest.raises(ValidationError):
        CourseContentProperties(assistant_policy=policy)


def test_default_explicit_course_policy_is_ask_only():
    assert AssistantPolicy().model_dump() == {
        "action_mode": "ask", "completion": "off", "independent_check": False,
    }


def test_property_patch_preserves_policy_and_custom_keys():
    original = {"custom": {"keep": 1}, "assistant_policy": {"action_mode": "ask", "completion": "single-line"}}
    merged = merge_assistant_properties(original, {"another": 2})
    assert merged["assistant_policy"] == original["assistant_policy"]
    changed = merge_assistant_properties(original, {"assistant_policy": {"action_mode": "edit"}})
    assert changed["assistant_policy"] == {"action_mode": "edit", "completion": "single-line"}
    assert changed["custom"] == {"keep": 1}
    assert original["assistant_policy"]["action_mode"] == "ask"
    assert merge_assistant_properties(original, {"assistant_policy": None})["assistant_policy"] is None
