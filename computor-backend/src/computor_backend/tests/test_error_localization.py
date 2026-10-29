"""Error responses in the reader's language (computor-org/issues#539, B5)."""

import ast
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from computor_backend.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from computor_backend.exceptions import localization, messages_de
from computor_backend.exceptions.error_handlers import computor_exception_handler
from computor_backend.middleware.upload_limiter import UploadSizeLimiterMiddleware

PACKAGE = Path(__file__).resolve().parents[1]

# Modules whose refusals reach learners, tutors and lecturers in normal use.
# Admin-only modules (system, services, user administration, Coder template
# management, deployment machinery) stay in English.
USER_FACING_MODULES = [
    "api/auth.py", "api/courses.py", "api/course_contents.py", "api/course_deployment.py",
    "api/course_member_import.py", "api/documents.py", "api/invites.py", "api/lecturer.py",
    "api/messages.py", "api/results.py", "api/sessions.py", "api/storage.py",
    "api/submissions.py", "api/tests.py", "api/tutor.py", "api/user.py",
    "business_logic/auth.py", "business_logic/consent.py", "business_logic/content_visibility.py",
    "business_logic/course_analytics.py", "business_logic/course_content_move.py",
    "business_logic/course_member_comments.py", "business_logic/course_member_import.py",
    "business_logic/course_registration.py", "business_logic/crud.py",
    "business_logic/documents.py", "business_logic/instance_limits.py",
    "business_logic/lecturer_deployment.py", "business_logic/messages/core.py",
    "business_logic/messages/lifecycle.py", "business_logic/messages/mentions.py",
    "business_logic/messages/permissions.py", "business_logic/profiles.py",
    "business_logic/public_testing_admission.py", "business_logic/public_workspace_capacity.py",
    "business_logic/student_description.py", "business_logic/submission_limits.py",
    "business_logic/submissions.py", "business_logic/testing_orchestration.py",
    "business_logic/tutor.py", "business_logic/workspace_launch_context.py",
    "interfaces/course.py", "interfaces/course_member.py", "interfaces/user.py",
    "permissions/auth.py", "permissions/handlers_course.py", "permissions/handlers_scoped.py",
    "repositories/course_member_gradings_view.py", "repositories/student_view.py",
    "services/dependency_sync.py", "services/tutor_test_storage.py", "storage_security.py",
    "database.py", "business_logic/cascade_deletion.py",
]


def _sample(node):
    """English text a raise site produces, with every variable part set to 'X'."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) else "X" for v in node.values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = _sample(node.left), _sample(node.right)
        return None if left is None or right is None else left + right
    if isinstance(node, (ast.Call, ast.Name, ast.Attribute)):
        return "X"
    return None


def _user_facing_texts():
    for module in USER_FACING_MODULES:
        tree = ast.parse((PACKAGE / module).read_text())
        for node in ast.walk(tree):
            texts = []
            if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
                func = node.exc.func
                name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
                if not name.endswith("Exception"):
                    continue
                detail = next((kw.value for kw in node.exc.keywords if kw.arg == "detail"), None)
                if isinstance(detail, ast.Dict):
                    detail = next((v for k, v in zip(detail.keys, detail.values)
                                   if isinstance(k, ast.Constant) and k.value == "message"), None)
                texts.append(detail)
            elif isinstance(node, ast.Return) and isinstance(node.value, ast.Tuple) \
                    and len(node.value.elts) == 2 and module == "storage_security.py":
                texts.append(node.value.elts[1])  # (valid, error) pairs become a detail
            elif isinstance(node, ast.Assign) and module in (
                "business_logic/instance_limits.py", "business_logic/public_workspace_capacity.py",
            ) and any(isinstance(t, ast.Name) and t.id in ("reason", "detail") for t in node.targets):
                value = node.value.body if isinstance(node.value, ast.IfExp) else node.value
                texts.extend([value, node.value.orelse] if isinstance(node.value, ast.IfExp) else [value])
            elif isinstance(node, ast.Return) and module == "business_logic/cascade_deletion.py" \
                    and isinstance(node.value, ast.JoinedStr):
                texts.append(node.value)
            for text_node in texts:
                text = _sample(text_node) if text_node is not None else None
                # Only variable text (str(e), a passed-through reason) has no literal part.
                if text and text.strip("X "):
                    yield f"{module}:{node.lineno}", text


def test_every_user_facing_refusal_has_german():
    missing = [f"{where}: {text}" for where, text in _user_facing_texts()
               if localization.translate_detail_de(text) is None]
    assert not missing, "No German for:\n" + "\n".join(missing)


def test_every_registry_code_has_german():
    registry = yaml.safe_load((PACKAGE.parents[1] / "error_registry.yaml").read_text())
    assert {e["code"] for e in registry["errors"]} <= set(messages_de.CODES)


def test_placeholders_survive_translation():
    for english, german in messages_de.DETAILS.items():
        names = set(localization._PLACEHOLDER.findall(english))
        assert set(localization._PLACEHOLDER.findall(german)) <= names, english


def _request(accept_language=None, user_id=None):
    headers = {"Accept-Language": accept_language} if accept_language else {}
    state = SimpleNamespace()
    if user_id:
        state.user_id = user_id
    return SimpleNamespace(state=state, method="GET", url=SimpleNamespace(path="/x"),
                           scope={"type": "http", "path": "/x"}, client=None, headers=headers)


async def _body(request, exc):
    response = await computor_exception_handler(request, exc)
    return response.status_code, json.loads(response.body)


@pytest.mark.asyncio
async def test_german_reader_gets_german_detail_title_and_the_english_original():
    exc = ForbiddenException(detail="You don't have tutor permissions for this course")
    status, body = await _body(_request("de-AT,en;q=0.5"), exc)
    assert status == 403
    assert body["message"] == "Du hast in diesem Kurs keine Tutorenrechte."
    assert body["title"] == "Keine Berechtigung"
    assert body["message_en"] == "You don't have tutor permissions for this course"
    assert body["error_code"] == "AUTHZ_001"


@pytest.mark.asyncio
async def test_english_reader_keeps_english():
    exc = ForbiddenException(detail="You don't have tutor permissions for this course")
    _, body = await _body(_request("en-US,en;q=0.9"), exc)
    assert body["message"] == body["message_en"] == "You don't have tutor permissions for this course"
    assert body["title"] == "Insufficient Permissions"


@pytest.mark.asyncio
async def test_code_without_detail_uses_the_german_registry_text():
    _, body = await _body(_request("de"), NotFoundException())
    assert body["message"] == "Das Angeforderte wurde nicht gefunden."
    assert body["message_en"] == "The requested resource was not found."


@pytest.mark.asyncio
async def test_variable_parts_are_carried_into_the_german_text():
    exc = ConflictException(detail="Maximum test runs reached for this assignment (5 of 5 used)")
    _, body = await _body(_request("de"), exc)
    assert body["message"] == "Du hast alle Testläufe für diese Aufgabe aufgebraucht (5 von 5)."


@pytest.mark.asyncio
async def test_profile_language_wins_over_the_browser(monkeypatch):
    monkeypatch.setattr(localization, "_profile_language", lambda user_id: "de")
    exc = ForbiddenException(detail="You don't have tutor permissions for this course")
    _, body = await _body(_request("en-US", user_id="u1"), exc)
    assert body["message"] == "Du hast in diesem Kurs keine Tutorenrechte."


@pytest.mark.asyncio
async def test_unknown_detail_stays_english_for_a_german_reader():
    _, body = await _body(_request("de"), ForbiddenException(detail="Something only admins see"))
    assert body["message"] == "Something only admins see"


def test_reason_and_hint_are_translated_sentence_by_sentence():
    text = (
        "Hosted workspaces are at capacity (12 running or starting)."
        " You can keep working without a workspace by installing the Computor"
        " extension in your own VS Code: https://example.org/install"
    )
    assert localization.translate_detail_de(text) == (
        "Die gehosteten Arbeitsumgebungen sind ausgelastet (12 laufen oder starten gerade)."
        " Du kannst auch ohne Arbeitsumgebung weiterarbeiten, wenn du die Computor-Erweiterung"
        " in deinem eigenen VS Code installierst: https://example.org/install"
    )


def test_upload_limit_refusal_carries_a_german_message():
    scope = {"type": "http", "headers": [(b"accept-language", b"de-DE")]}
    response = UploadSizeLimiterMiddleware(app=None, max_size=10)._too_large(2048, 1024, scope)
    body = json.loads(response.body)
    assert body["message"].startswith("Die Anfrage ist zu groß.")
    assert body["detail"]["error"] == body["message_en"]
