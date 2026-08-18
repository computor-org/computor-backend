"""Unit tests for the self-heal of a student's read grant on the course template.

No DB and no live Forgejo: the provider client and the account lookup are
monkeypatched, so these exercise only the decision logic in
``_maybe_heal_forgejo_template_reader``.

The grant is attempted exactly once, at fork creation. Before this heal existed
a failure there was permanent — the student's clone token authenticated fine and
then 403'd on the template forever, so template updates never reached them.
"""
from types import SimpleNamespace

import pytest

from computor_backend.business_logic import course_git


class _FakeDb:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


class _FakeClient:
    """Records every ``ensure_template_reader`` call and answers with `result`."""

    def __init__(self, result=True):
        self.result = result
        self.calls = []

    def ensure_template_reader(self, owner, repo, username):
        self.calls.append((owner, repo, username))
        return self.result


def _repo(template_read_granted=None, mode="managed"):
    forgejo = {"owner": "itpcp-2027", "repo_name": "student-handle", "collaborator_added": True}
    if template_read_granted is not None:
        forgejo["template_read_granted"] = template_read_granted
    return SimpleNamespace(
        mode=mode,
        course_member_id="cm-1",
        properties={"forgejo": forgejo},
        updated_by=None,
    )


def _binding(template_repo="itpcp-2027/template"):
    return SimpleNamespace(template_repo=template_repo)


FORGEJO = SimpleNamespace(type="forgejo", base_url="https://forge.example")


@pytest.fixture
def wired(monkeypatch):
    """The helper with its Forgejo account lookup and provider client faked."""
    client = _FakeClient()
    monkeypatch.setattr(course_git, "_ensure_forgejo_account", lambda user_id, server, db: "handle")
    monkeypatch.setattr(course_git, "get_provider_client_for_server", lambda server: client)
    return client


class TestHealForgejoTemplateReader:
    def test_grants_and_records_the_flag_when_it_was_never_granted(self, wired):
        rec, db = _repo(template_read_granted=False), _FakeDb()

        course_git._maybe_heal_forgejo_template_reader(rec, _binding(), FORGEJO, "u-1", db)

        assert wired.calls == [("itpcp-2027", "template", "handle")]
        assert rec.properties["forgejo"]["template_read_granted"] is True
        # The rest of the recorded provisioning state survives the update.
        assert rec.properties["forgejo"]["collaborator_added"] is True
        assert rec.updated_by == "u-1"
        assert db.commits == 1

    def test_heals_a_record_predating_the_flag(self, wired):
        # Repos provisioned before the flag existed carry no key at all.
        rec, db = _repo(template_read_granted=None), _FakeDb()

        course_git._maybe_heal_forgejo_template_reader(rec, _binding(), FORGEJO, "u-1", db)

        assert len(wired.calls) == 1
        assert rec.properties["forgejo"]["template_read_granted"] is True

    def test_is_a_no_op_once_the_grant_is_recorded(self, wired):
        rec, db = _repo(template_read_granted=True), _FakeDb()

        course_git._maybe_heal_forgejo_template_reader(rec, _binding(), FORGEJO, "u-1", db)

        assert wired.calls == []
        assert db.commits == 0

    def test_leaves_the_flag_unset_when_the_grant_fails(self, wired):
        # Still no Forgejo identity, say — the next provision has to try again.
        wired.result = False
        rec, db = _repo(template_read_granted=False), _FakeDb()

        course_git._maybe_heal_forgejo_template_reader(rec, _binding(), FORGEJO, "u-1", db)

        assert len(wired.calls) == 1
        assert rec.properties["forgejo"]["template_read_granted"] is False
        assert db.commits == 0

    def test_skips_a_member_without_a_forgejo_handle(self, monkeypatch, wired):
        monkeypatch.setattr(course_git, "_ensure_forgejo_account", lambda user_id, server, db: None)
        rec, db = _repo(template_read_granted=False), _FakeDb()

        course_git._maybe_heal_forgejo_template_reader(rec, _binding(), FORGEJO, "u-1", db)

        assert wired.calls == []
        assert db.commits == 0

    def test_skips_non_forgejo_servers(self, wired):
        gitlab = SimpleNamespace(type="gitlab", base_url="https://gitlab.example")
        rec, db = _repo(template_read_granted=False), _FakeDb()

        course_git._maybe_heal_forgejo_template_reader(rec, _binding(), gitlab, "u-1", db)

        assert wired.calls == []

    def test_skips_an_external_repo(self, wired):
        rec, db = _repo(template_read_granted=False, mode="external"), _FakeDb()

        course_git._maybe_heal_forgejo_template_reader(rec, _binding(), FORGEJO, "u-1", db)

        assert wired.calls == []

    def test_skips_a_binding_without_a_usable_template_ref(self, wired):
        rec, db = _repo(template_read_granted=False), _FakeDb()

        course_git._maybe_heal_forgejo_template_reader(rec, _binding("no-slash"), FORGEJO, "u-1", db)
        course_git._maybe_heal_forgejo_template_reader(rec, _binding(None), FORGEJO, "u-1", db)

        assert wired.calls == []
