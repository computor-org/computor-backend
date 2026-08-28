"""Who may raise a submission budget, and how far the change reaches (#393).

The student-facing refusal tells them to "ask your lecturer if you need another
attempt", which was advice nobody could act on: the limit is per assignment, so
granting *one* student more attempts had no route at all. The group-level
override is that route, and a tutor — the person actually reading the
submission — is allowed to use it.

Everything else on a submission group stays lecturer-only, which is why the
payload is its own narrow model rather than ``SubmissionGroupUpdate``.
"""
import uuid

import pytest
from pydantic import ValidationError

from computor_backend.business_logic import tutor
from computor_backend.business_logic.submission_limits import resolve_limits
from computor_backend.exceptions import BadRequestException, ForbiddenException
from computor_types.tutor_submission_groups import TutorSubmissionGroupLimitsUpdate


COURSE_ID = str(uuid.uuid4())
GROUP_ID = str(uuid.uuid4())


class _Group:
    """Stand-in for the submission_group row being edited."""

    def __init__(self, max_test_runs=None, max_submissions=None):
        self.id = GROUP_ID
        self.course_id = COURSE_ID
        self.max_test_runs = max_test_runs
        self.max_submissions = max_submissions


class _Result:
    """Chainable query stub whose ``first()`` is fixed up front."""

    def __init__(self, value):
        self._value = value

    def filter(self, *args, **kwargs):
        return self

    def options(self, *args, **kwargs):
        return self

    def first(self):
        return self._value


class _Session:
    def __init__(self, group):
        self._group = group

    def query(self, *args, **kwargs):
        return _Result(self._group)


class _Repo:
    """Records what the business logic asked to write."""

    written = None

    def __init__(self, db, cache=None):
        pass

    def update_entity(self, entity, updates):
        type(self).written = dict(updates)
        for key, value in updates.items():
            setattr(entity, key, value)
        return entity


@pytest.fixture
def wired(monkeypatch):
    """Wire the function to stubs and return a caller taking (role, payload)."""
    _Repo.written = None
    monkeypatch.setattr(tutor, "SubmissionGroupRepository", _Repo)
    monkeypatch.setattr(tutor, "set_db_user", lambda db, user_id: None)
    monkeypatch.setattr(
        tutor, "get_tutor_submission_group",
        lambda group_id, permissions, db, cache=None: group_id,
    )

    def _call(group, payload, *, is_tutor=True):
        monkeypatch.setattr(
            tutor, "check_course_permissions",
            lambda permissions, model, role, db: _Result(object() if is_tutor else None),
        )

        class _Principal:
            user_id = str(uuid.uuid4())

            def get_user_id_or_throw(self):
                return self.user_id

        return tutor.update_tutor_submission_group_limits(
            GROUP_ID, payload, _Principal(), _Session(group), None
        )

    return _call


# --------------------------------------------------------------------------
# Authorisation
# --------------------------------------------------------------------------

def test_a_tutor_may_grant_extra_submissions(wired):
    group = _Group()
    wired(group, TutorSubmissionGroupLimitsUpdate(max_submissions=4))
    assert group.max_submissions == 4


def test_someone_without_the_tutor_role_is_refused(wired):
    with pytest.raises(ForbiddenException):
        wired(
            _Group(),
            TutorSubmissionGroupLimitsUpdate(max_submissions=4),
            is_tutor=False,
        )
    assert _Repo.written is None


def test_a_missing_group_is_not_found(wired):
    from computor_backend.exceptions import NotFoundException

    with pytest.raises(NotFoundException):
        wired(None, TutorSubmissionGroupLimitsUpdate(max_submissions=4))


# --------------------------------------------------------------------------
# Tri-state payload: absent / null / number
# --------------------------------------------------------------------------

def test_an_omitted_field_leaves_the_other_override_alone(wired):
    """Setting submissions must not silently clear a test-run grant."""
    group = _Group(max_test_runs=9, max_submissions=1)
    wired(group, TutorSubmissionGroupLimitsUpdate(max_submissions=4))
    assert _Repo.written == {"max_submissions": 4}
    assert group.max_test_runs == 9


def test_null_clears_the_override_so_the_group_inherits_again(wired):
    group = _Group(max_submissions=4)
    wired(group, TutorSubmissionGroupLimitsUpdate(max_submissions=None))
    assert _Repo.written == {"max_submissions": None}
    assert group.max_submissions is None


def test_an_empty_payload_is_rejected_rather_than_written(wired):
    with pytest.raises(BadRequestException):
        wired(_Group(), TutorSubmissionGroupLimitsUpdate())
    assert _Repo.written is None


def test_negative_budgets_are_refused_by_the_payload():
    with pytest.raises(ValidationError):
        TutorSubmissionGroupLimitsUpdate(max_submissions=-1)
    with pytest.raises(ValidationError):
        TutorSubmissionGroupLimitsUpdate(max_test_runs=-1)


def test_zero_is_a_real_limit_and_not_unlimited(wired):
    group = _Group()
    wired(group, TutorSubmissionGroupLimitsUpdate(max_submissions=0))
    assert group.max_submissions == 0


# --------------------------------------------------------------------------
# What the override means downstream
# --------------------------------------------------------------------------

class _Holder:
    def __init__(self, max_test_runs=None, max_submissions=None):
        self.max_test_runs = max_test_runs
        self.max_submissions = max_submissions
        self.course = None


def test_the_grant_wins_over_the_assignment_and_the_course(wired):
    """The tutor's number is the one enforcement and the trees both read."""
    group = _Group()
    wired(group, TutorSubmissionGroupLimitsUpdate(max_submissions=4))
    content = _Holder(max_submissions=2)
    course = _Holder(max_submissions=1)
    assert resolve_limits(content, group, course)[1] == 4


def test_lowering_below_what_is_already_spent_is_allowed(wired):
    """Nothing already submitted is invalidated; there is simply no budget left."""
    group = _Group(max_submissions=5)
    wired(group, TutorSubmissionGroupLimitsUpdate(max_submissions=1))
    assert group.max_submissions == 1
    assert resolve_limits(_Holder(max_submissions=5), group)[1] == 1
