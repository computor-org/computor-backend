"""Unit tests for the managed-GitLab provider path.

No DB and no live GitLab — the provider client is driven against a tiny in-memory
fake of the python-gitlab API (just enough to exercise group/project creation,
idempotency, fork, and member grants). Real GitLab integration is a separate
follow-up.
"""
from types import SimpleNamespace

import pytest
from gitlab.exceptions import GitlabCreateError

from computor_backend.business_logic.course_git import build_course_git_descriptor
from computor_backend.git_provider.gitlab import (
    GITLAB_MAINTAINER,
    GITLAB_REPORTER,
    GitLabProviderClient,
)
from computor_types.course_git import CourseGitBindingUpsert


# ---------------------------------------------------------------------------
# Mode validation (computor-types)
# ---------------------------------------------------------------------------


class TestStudentRepoModeValidation:
    def test_gitlab_managed_is_accepted(self):
        b = CourseGitBindingUpsert(student_repo_modes=["gitlab_managed"])
        assert b.student_repo_modes == ["gitlab_managed"]

    def test_mixed_known_modes_accepted(self):
        modes = ["forgejo", "gitlab_managed", "gitlab_byo", "download"]
        assert CourseGitBindingUpsert(student_repo_modes=modes).student_repo_modes == modes

    def test_unknown_mode_rejected(self):
        with pytest.raises(ValueError):
            CourseGitBindingUpsert(student_repo_modes=["gitlab_managed", "nonsense"])


# ---------------------------------------------------------------------------
# Descriptor exposes the new mode (pure projection, no DB)
# ---------------------------------------------------------------------------


class TestDescriptorGitlabManaged:
    def test_descriptor_carries_gitlab_managed_mode(self):
        binding = SimpleNamespace(
            delivery="git",
            student_repo_modes=["gitlab_managed"],
            template_repo="root/fam--course/template",
            template_url="https://gitlab.example/root/fam--course/template.git",
            default_branch="main",
            git_server_id="srv-gl",
        )
        server = SimpleNamespace(type="gitlab", base_url="https://gitlab.example")
        d = build_course_git_descriptor("c1", binding, server)
        assert d.configured is True
        assert d.student_repo_modes == ["gitlab_managed"]
        assert d.template.server_type == "gitlab"
        assert d.template.repo == "root/fam--course/template"


# ---------------------------------------------------------------------------
# Tiny in-memory fake of the python-gitlab surface the client uses
# ---------------------------------------------------------------------------


class _FakeMembers:
    def __init__(self):
        self._by_user = {}

    def create(self, data):
        uid = data["user_id"]
        if uid in self._by_user:
            raise GitlabCreateError("member exists", response_code=409)
        m = SimpleNamespace(user_id=uid, access_level=data["access_level"], save=lambda: None)
        self._by_user[uid] = m
        return m

    def get(self, uid):
        return self._by_user[uid]


class _FakeGroup:
    def __init__(self, gl, gid, path, full_path, parent_id):
        self._gl = gl
        self.id = gid
        self.path = path
        self.full_path = full_path
        self.parent_id = parent_id
        self.members = _FakeMembers()

    @property
    def subgroups(self):
        gl = self._gl
        parent_id = self.id

        class _Mgr:
            def list(self, search=None, all=False):
                return [
                    g for g in gl._groups.values()
                    if g.parent_id == parent_id and (search is None or g.path == search)
                ]

        return _Mgr()


class _FakeProject:
    def __init__(self, gl, pid, path, path_with_namespace, namespace_id):
        self.id = pid
        self.path = path
        self.path_with_namespace = path_with_namespace
        self.namespace = {"id": namespace_id}
        self.import_status = "finished"
        self.members = _FakeMembers()


class _FakeGitlab:
    """Just enough of python-gitlab for ensure_course_structure / fork / members."""

    def __init__(self, root_group_id=100, root_full_path="root"):
        self._groups = {}
        self._projects = {}
        self._next_gid = 1
        self._next_pid = 1
        # Pre-seed the registered parent group.
        self._groups[root_group_id] = _FakeGroup(self, root_group_id, "root", root_full_path, None)
        self.groups = self._GroupMgr(self)
        self.projects = self._ProjectMgr(self)

    class _GroupMgr:
        def __init__(self, gl):
            self._gl = gl

        def get(self, gid):
            return self._gl._groups[int(gid)]

        def create(self, data):
            gl = self._gl
            gid = 1000 + gl._next_gid
            gl._next_gid += 1
            parent = gl._groups[int(data["parent_id"])]
            full_path = f"{parent.full_path}/{data['path']}"
            g = _FakeGroup(gl, gid, data["path"], full_path, parent.id)
            gl._groups[gid] = g
            return g

    class _ProjectMgr:
        def __init__(self, gl):
            self._gl = gl

        def list(self, search=None, all=False, namespace_id=None):
            out = []
            for p in self._gl._projects.values():
                if search is not None and p.path != search:
                    continue
                if namespace_id is not None and p.namespace["id"] != namespace_id:
                    continue
                out.append(p)
            return out

        def get(self, ref):
            gl = self._gl
            if isinstance(ref, int) or str(ref).isdigit():
                return gl._projects[int(ref)]
            for p in gl._projects.values():
                if p.path_with_namespace == ref:
                    return p
            from gitlab.exceptions import GitlabGetError

            raise GitlabGetError("404", response_code=404)

        def create(self, data):
            gl = self._gl
            pid = 2000 + gl._next_pid
            gl._next_pid += 1
            ns = gl._groups[int(data["namespace_id"])]
            pwn = f"{ns.full_path}/{data['path']}"
            p = _FakeProject(gl, pid, data["path"], pwn, ns.id)
            gl._projects[pid] = p
            return p

    # Raw HTTP used by gitlab_utils.gitlab_fork_project / gitlab_unprotect_branches
    def http_post(self, path, post_data=None):
        # /projects/{id}/fork
        ns = self._groups[int(post_data["namespace_id"])]
        pid = 2000 + self._next_pid
        self._next_pid += 1
        pwn = f"{ns.full_path}/{post_data['path']}"
        self._projects[pid] = _FakeProject(self, pid, post_data["path"], pwn, ns.id)

    def http_delete(self, path):
        return None  # unprotect: no-op


def _client_with_fake(fake) -> GitLabProviderClient:
    c = GitLabProviderClient("https://gitlab.example", "group-token", None)
    c._gl = lambda: fake  # bypass the real python-gitlab client
    return c


class TestEnsureCourseStructure:
    def test_creates_flat_structure_under_parent_group(self):
        fake = _FakeGitlab(root_group_id=100)
        client = _client_with_fake(fake)

        s = client.ensure_course_structure(100, "fam--course", "My Course")

        assert s["course_group_path"] == "root/fam--course"
        assert s["template_path"] == "root/fam--course/template"
        assert s["reference_path"] == "root/fam--course/reference"
        assert s["students_group_path"] == "root/fam--course/students"
        assert s["template_url"].endswith("root/fam--course/template.git")
        # ids are populated
        assert s["template_project_id"] and s["reference_project_id"] and s["students_group_id"]

    def test_is_idempotent(self):
        fake = _FakeGitlab(root_group_id=100)
        client = _client_with_fake(fake)

        first = client.ensure_course_structure(100, "fam--course")
        second = client.ensure_course_structure(100, "fam--course")

        assert first["course_group_id"] == second["course_group_id"]
        assert first["template_project_id"] == second["template_project_id"]
        assert first["students_group_id"] == second["students_group_id"]
        # No duplicate groups/projects were created.
        assert len(fake._groups) == 3  # root + course + students
        assert len(fake._projects) == 2  # template + reference


class TestProvisionStudentFork:
    def test_fork_into_students_group(self):
        fake = _FakeGitlab(root_group_id=100)
        client = _client_with_fake(fake)
        s = client.ensure_course_structure(100, "fam--course")

        result = client.provision_student_fork(
            s["template_project_id"], s["students_group_id"], "alice"
        )

        assert result.provider_project_id
        full_path = result.properties["gitlab"]["full_path"]
        assert full_path == "root/fam--course/students/alice"
        assert result.http_url.endswith("root/fam--course/students/alice.git")
        assert result.properties["gitlab"]["namespace_id"] == s["students_group_id"]

    def test_fork_is_idempotent(self):
        fake = _FakeGitlab(root_group_id=100)
        client = _client_with_fake(fake)
        s = client.ensure_course_structure(100, "fam--course")

        r1 = client.provision_student_fork(s["template_project_id"], s["students_group_id"], "alice")
        before = len(fake._projects)
        r2 = client.provision_student_fork(s["template_project_id"], s["students_group_id"], "alice")

        assert r1.provider_project_id == r2.provider_project_id
        assert len(fake._projects) == before  # no second fork created


class TestAddMember:
    def test_add_then_idempotent_raise(self):
        fake = _FakeGitlab(root_group_id=100)
        client = _client_with_fake(fake)
        s = client.ensure_course_structure(100, "fam--course")
        r = client.provision_student_fork(s["template_project_id"], s["students_group_id"], "alice")
        project_id = int(r.provider_project_id)

        assert client.add_member(project_id, 7, GITLAB_MAINTAINER) is True
        # Second add for the same user is a 409 the client swallows as success.
        assert client.add_member(project_id, 7, GITLAB_MAINTAINER) is True
        # Reporter on a (different) template project also works.
        assert client.add_member(s["template_project_id"], 7, GITLAB_REPORTER) is True
