"""WebSocket events for profile and submission-group changes.

``user:profile_updated`` goes to the user's own ``user:<id>`` inbox.
``submission_group:updated`` goes to the group's scope channel and to each
member's inbox, never to ``course:<id>``, which every course member may
subscribe to. Both are published only after the transaction commits.
"""

import asyncio
import json
from types import SimpleNamespace

import pytest

from computor_backend.api import results as results_api
from computor_backend.business_logic import profiles as profiles_bl
from computor_backend.business_logic import submissions as submissions_bl
from computor_backend.model.artifact import SubmissionArtifact, SubmissionGrade
from computor_backend.model.course import SubmissionGroup
from computor_backend.websocket import event_publisher
from computor_backend.websocket.event_publisher import (
    publish_submission_group_updated,
    publish_user_profile_updated,
)
from computor_backend.websocket.pubsub import CHANNEL_PREFIX


class FakeRedis:
    def __init__(self, fail=False):
        self.published = []
        self._fail = fail

    def publish(self, channel, message):
        if self._fail:
            raise ConnectionError("redis is down")
        self.published.append((channel, json.loads(message)))


@pytest.fixture
def fake_redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(event_publisher, "_get_sync_redis", lambda: fake)
    return fake


class FakeQuery:
    def __init__(self, result):
        self._result = result

    def options(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def join(self, *args, **kwargs):
        return self

    def first(self):
        return self._result

    def all(self):
        return self._result


class FakeDb:
    """Query double keyed by model; anything else returns ``other``."""

    def __init__(self, objects=None, other=None):
        self.objects = objects or {}
        self.other = other

    def query(self, model):
        if isinstance(model, type):
            return FakeQuery(self.objects.get(model))
        return FakeQuery(self.other)

    def add(self, obj):
        self.added = obj

    def commit(self):
        pass

    def refresh(self, obj):
        pass


class Recorder:
    def __init__(self):
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))


def _group():
    return SimpleNamespace(id="g-1", course_id="c-1", course_content_id="cc-1")


# --- publishers ------------------------------------------------------------


def test_profile_event_goes_to_own_inbox(fake_redis):
    publish_user_profile_updated("u-1", "de")

    assert len(fake_redis.published) == 1
    channel, message = fake_redis.published[0]
    assert channel == f"{CHANNEL_PREFIX}user:u-1"
    assert message["type"] == "user:profile_updated"
    assert message["data"]["user_id"] == "u-1"
    assert message["data"]["language_code"] == "de"


def test_submission_group_event_goes_to_group_and_member_inboxes(fake_redis):
    publish_submission_group_updated(
        "c-1", "cc-1", "g-1", ["u-1", "u-2"], grading=0.8
    )

    channels = [channel for channel, _ in fake_redis.published]
    assert channels == [
        f"{CHANNEL_PREFIX}submission_group:g-1",
        f"{CHANNEL_PREFIX}user:u-1",
        f"{CHANNEL_PREFIX}user:u-2",
    ]
    for _, message in fake_redis.published:
        assert message["type"] == "submission_group:updated"
        data = message["data"]
        assert {k: data[k] for k in (
            "course_id", "course_content_id", "submission_group_id",
            "status", "result", "grading",
        )} == {
            "course_id": "c-1", "course_content_id": "cc-1",
            "submission_group_id": "g-1",
            "status": None, "result": None, "grading": 0.8,
        }


def test_publish_failure_is_logged_not_raised(monkeypatch, caplog):
    monkeypatch.setattr(event_publisher, "_get_sync_redis", lambda: FakeRedis(fail=True))

    publish_user_profile_updated("u-1", "de")
    publish_submission_group_updated("c-1", "cc-1", "g-1", ["u-1"], status="submitted")

    assert "Failed to publish" in caplog.text


# --- profile path ----------------------------------------------------------


def _profile_env(monkeypatch, language_code):
    profile = SimpleNamespace(id="p-1", user_id="u-1", language_code=language_code)
    monkeypatch.setattr(profiles_bl, "get_owned_or_404", lambda **kw: profile)
    monkeypatch.setattr(profiles_bl, "apply_update", lambda **kw: profile)
    recorder = Recorder()
    monkeypatch.setattr(profiles_bl, "publish_user_profile_updated", recorder)
    return recorder


@pytest.mark.parametrize("language_code", ["de", None])
def test_profile_language_change_publishes(monkeypatch, language_code):
    recorder = _profile_env(monkeypatch, language_code)

    profiles_bl.update_profile(
        "p-1", {"language_code": language_code}, SimpleNamespace(), FakeDb()
    )

    assert recorder.calls == [(("u-1", language_code), {})]


def test_profile_change_without_language_publishes_nothing(monkeypatch):
    recorder = _profile_env(monkeypatch, None)

    profiles_bl.update_profile("p-1", {"bio": "x"}, SimpleNamespace(), FakeDb())

    assert recorder.calls == []


# --- submission-group announcement -----------------------------------------


def test_announcement_waits_for_commit_and_names_members(monkeypatch):
    callbacks = []
    monkeypatch.setattr(
        submissions_bl, "register_post_commit", lambda db, cb: callbacks.append(cb)
    )
    recorder = Recorder()
    monkeypatch.setattr(submissions_bl, "publish_submission_group_updated", recorder)
    db = FakeDb({SubmissionGroup: _group()}, other=[("u-1",), ("u-2",)])

    submissions_bl.announce_submission_group_updated(db, "g-1", result="finished")

    assert recorder.calls == []
    for cb in callbacks:
        cb()
    assert recorder.calls == [(
        ("c-1", "cc-1", "g-1", ["u-1", "u-2"]),
        {"status": None, "result": "finished", "grading": None},
    )]


@pytest.fixture
def announced(monkeypatch):
    recorder = Recorder()
    monkeypatch.setattr(submissions_bl, "announce_submission_group_updated", recorder)
    monkeypatch.setattr(results_api, "announce_submission_group_updated", recorder)
    return recorder


def test_worker_result_patch_announces(monkeypatch, announced):
    # PATCH /results/{id} is how the test worker reports a finished run.
    db_result = SimpleNamespace(id="r-1", submission_group_id="g-1", status=0)
    monkeypatch.setattr(results_api, "require_public_result_writer", lambda p: None)
    monkeypatch.setattr(
        "computor_backend.permissions.core.check_permissions",
        lambda *a, **k: FakeQuery(db_result),
    )

    class FakeRepo:
        def __init__(self, db, cache):
            pass

        def update_entity(self, entity, updates):
            for key, value in updates.items():
                setattr(entity, key, value)
            return entity

    async def no_json(result_id):
        return None

    monkeypatch.setattr(results_api, "ResultRepository", FakeRepo)
    monkeypatch.setattr(
        "computor_backend.services.result_storage.retrieve_result_json", no_json
    )
    monkeypatch.setattr(
        results_api.ResultGet, "model_validate",
        classmethod(lambda cls, obj, **kw: SimpleNamespace(model_dump=lambda: {})),
    )
    payload = results_api.ResultUpdate(status="finished")

    db = FakeDb()

    asyncio.run(results_api.update_result("r-1", payload, SimpleNamespace(), db, None))

    assert announced.calls == [((db, "g-1"), {"result": "finished"})]


def test_test_result_create_announces(monkeypatch, announced):
    group = SimpleNamespace(
        id="g-1", course_id="c-1",
        course_content=SimpleNamespace(id="cc-1", course_content_type_id="t-1"),
    )
    artifact = SimpleNamespace(id="a-1", submission_group_id="g-1", submission_group=group)
    db = FakeDb({SubmissionArtifact: artifact, submissions_bl.SubmissionGroupMember: object()})
    monkeypatch.setattr(
        submissions_bl, "get_course_member_or_403", lambda *a, **k: SimpleNamespace(id="cm-1")
    )
    monkeypatch.setattr(submissions_bl, "is_course_staff", lambda *a, **k: False)
    monkeypatch.setattr(
        "computor_backend.business_logic.testing_orchestration.enforce_test_limits",
        lambda *a, **k: None,
    )

    asyncio.run(submissions_bl.create_test_result(
        "a-1", "cm-1", "ts-1", None, "queued", None, None, None, "v1", None,
        SimpleNamespace(), db,
    ))

    assert announced.calls == [((db, "g-1"), {"result": "queued"})]


def test_test_result_update_announces(monkeypatch, announced):
    result = SimpleNamespace(id="r-1", submission_group_id="g-1", course_member_id="cm-1", status=0)
    db = FakeDb({submissions_bl.Result: result})
    monkeypatch.setattr(submissions_bl, "require_public_result_writer", lambda p: None)
    monkeypatch.setattr(
        "computor_backend.repositories.result.ResultRepository",
        lambda db, cache=None: SimpleNamespace(
            update=lambda eid, updates: (setattr(result, "status", updates["status"]), result)[1]
        ),
    )
    permissions = SimpleNamespace(get_user_id=lambda: "u-1", has_claim=lambda c: True, is_service=False)

    asyncio.run(submissions_bl.update_test_result(
        "r-1", "finished", None, None, None, None, permissions, db
    ))

    assert announced.calls == [((db, "g-1"), {"result": "finished"})]


def test_submit_flag_announces(monkeypatch, announced):
    artifact = SimpleNamespace(
        id="a-1", submit=False, submission_group_id="g-1",
        submission_group=SimpleNamespace(course_id="c-1", course_content=None),
    )
    monkeypatch.setattr(submissions_bl, "check_artifact_access", lambda *a, **k: artifact)
    monkeypatch.setattr(submissions_bl, "is_course_staff", lambda *a, **k: True)
    monkeypatch.setattr(submissions_bl, "enforce_content_visible", lambda *a, **k: None)
    monkeypatch.setattr(submissions_bl, "enforce_max_submissions", lambda *a, **k: None)

    class FakeRepo:
        def __init__(self, db, cache=None):
            pass

        def update(self, eid, updates):
            for key, value in updates.items():
                setattr(artifact, key, value)
            return artifact

    monkeypatch.setattr(submissions_bl, "SubmissionArtifactRepository", FakeRepo)
    db = FakeDb()

    submissions_bl.update_artifact("a-1", True, None, SimpleNamespace(), db)

    assert announced.calls == [((db, "g-1"), {"status": "submitted"})]


def test_grade_create_and_update_announce(monkeypatch, announced):
    artifact = SimpleNamespace(id="a-1", submission_group_id="g-1", submission_group=_group())
    grade_obj = SimpleNamespace(
        id="gr-1", artifact_id="a-1", grade=0.5,
        graded_by=SimpleNamespace(user_id="u-tutor"),
    )
    db = FakeDb({SubmissionArtifact: artifact, SubmissionGrade: grade_obj})
    monkeypatch.setattr(
        submissions_bl, "get_course_member_or_403", lambda *a, **k: SimpleNamespace(id="cm-1")
    )

    class FakeGradeRepo:
        def __init__(self, db, cache=None):
            pass

        def create(self, obj):
            return obj

        def update_entity(self, obj, updates):
            for key, value in updates.items():
                setattr(obj, key, value)
            return obj

    monkeypatch.setattr(submissions_bl, "SubmissionGradeRepository", FakeGradeRepo)

    submissions_bl.create_artifact_grade("a-1", 0.8, 1, None, SimpleNamespace(), db)
    submissions_bl.update_grade(
        "gr-1", 0.9, None, None, SimpleNamespace(get_user_id=lambda: "u-tutor"), db
    )

    assert announced.calls == [
        ((db, "g-1"), {"grading": 0.8}),
        ((db, "g-1"), {"grading": 0.9}),
    ]
