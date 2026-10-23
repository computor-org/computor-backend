"""Unit tests for the self-heal of a student's write grant on their own repository.

No DB and no live Forgejo: the session, the account lookup and the provider
client are faked. The fake client models the one rule that matters here — a
collaborator grant only succeeds for a name Forgejo already knows — so these
exercise ``_maybe_heal_forgejo_collaborator`` together with the real
``_ensure_forgejo_account`` it relies on.

Before the heal created the account, a re-provision whose first grant had
failed handed out a clone token that could read the course template but got
"repository not found" on the student's own repository (computor-org/issues#433).
"""
from types import SimpleNamespace

import pytest

from computor_backend.business_logic import course_git
from computor_backend.model.git_server import GitServer
from computor_backend.utils import bootstrap_admin

FORGEJO = SimpleNamespace(id="srv-1", type="forgejo", base_url="http://computor-forgejo:3030")
STUDENT = SimpleNamespace(id="u-1", email="student42@example.invalid", given_name="Stu", family_name="Dent")


class _FakeQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._result


class _FakeDb:
    def __init__(self):
        self.commits = 0

    def query(self, model):
        return _FakeQuery(FORGEJO if model is GitServer else STUDENT)

    def commit(self):
        self.commits += 1


class _FakeForgejo:
    """Grants succeed only for accounts that exist, as on a real Forgejo."""

    def __init__(self, users=()):
        self.users = set(users)
        self.calls = []

    def ensure_user(self, username, email, full_name, admin_username, admin_password):
        self.calls.append(("ensure_user", username))
        self.users.add(username)
        return True

    def ensure_collaborator(self, owner, repo, username, permission="write"):
        self.calls.append(("ensure_collaborator", owner, repo, username))
        return username in self.users


def _repo(collaborator_added=False):
    return SimpleNamespace(
        mode="managed",
        git_server_id=FORGEJO.id,
        course_member_id="cm-1",
        repo_ref="dsp-2026/student42",
        properties={"forgejo": {"collaborator_added": collaborator_added, "template_read_granted": True}},
        updated_by=None,
    )


@pytest.fixture
def forgejo(monkeypatch):
    client = _FakeForgejo()
    monkeypatch.setattr(course_git, "_resolve_oidc_handle", lambda user_id, db: "student42")
    monkeypatch.setattr(course_git, "_forgejo_admin_basic_auth_for", lambda server: ("admin", "pw"))
    monkeypatch.setattr(course_git, "get_provider_client_for_server", lambda server: client)
    monkeypatch.setattr(bootstrap_admin, "is_bootstrap_admin", lambda user: False)
    return client


class TestHealForgejoCollaborator:
    def test_creates_the_missing_account_before_granting(self, forgejo):
        rec, db = _repo(), _FakeDb()

        course_git._maybe_heal_forgejo_collaborator(rec, STUDENT.id, db)

        assert forgejo.calls == [
            ("ensure_user", "student42"),
            ("ensure_collaborator", "dsp-2026", "student42", "student42"),
        ]
        assert rec.properties["forgejo"]["collaborator_added"] is True
        # The rest of the recorded provisioning state survives the update.
        assert rec.properties["forgejo"]["template_read_granted"] is True
        assert rec.updated_by == STUDENT.id
        assert db.commits == 1

    def test_leaves_a_recorded_grant_alone(self, forgejo):
        rec, db = _repo(collaborator_added=True), _FakeDb()

        course_git._maybe_heal_forgejo_collaborator(rec, STUDENT.id, db)

        assert forgejo.calls == []
        assert db.commits == 0

    def test_a_failed_grant_is_not_recorded_and_retried_later(self, forgejo, monkeypatch):
        monkeypatch.setattr(forgejo, "ensure_collaborator", lambda *args, **kwargs: False)
        rec, db = _repo(), _FakeDb()

        course_git._maybe_heal_forgejo_collaborator(rec, STUDENT.id, db)

        assert rec.properties["forgejo"]["collaborator_added"] is False
        assert db.commits == 0

    def test_no_git_identity_means_no_grant(self, forgejo, monkeypatch):
        # The bootstrap administrator never has a Forgejo identity.
        monkeypatch.setattr(bootstrap_admin, "is_bootstrap_admin", lambda user: True)
        rec, db = _repo(), _FakeDb()

        course_git._maybe_heal_forgejo_collaborator(rec, STUDENT.id, db)

        assert forgejo.calls == []
        assert db.commits == 0
