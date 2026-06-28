"""Unit tests for ``build_course_git_descriptor`` (pure (binding, server) -> DTO).

No DB — binding/server stand-ins are SimpleNamespace, matching the attributes
the builder reads.
"""
from types import SimpleNamespace

from computor_backend.business_logic.course_git import build_course_git_descriptor


def _binding(**kw) -> SimpleNamespace:
    base = dict(
        delivery="git",
        student_repo_modes=["managed", "external"],
        template_repo="fam--course--template",
        template_url="https://forge.local/acme/fam--course--template.git",
        default_branch="main",
        git_server_id="srv-1",
    )
    base.update(kw)
    return SimpleNamespace(**base)


class TestBuildCourseGitDescriptor:
    def test_no_binding_is_unconfigured(self):
        d = build_course_git_descriptor("c1", None, None)
        assert d.course_id == "c1"
        assert d.configured is False
        assert d.delivery is None
        assert d.student_repo_modes == []
        assert d.template is None

    def test_git_binding_with_template(self):
        server = SimpleNamespace(type="forgejo", base_url="https://forge.local")
        d = build_course_git_descriptor("c1", _binding(), server)
        assert d.configured is True
        assert d.delivery == "git"
        assert d.student_repo_modes == ["managed", "external"]
        assert d.template is not None
        assert d.template.server_type == "forgejo"
        assert d.template.base_url == "https://forge.local"
        assert d.template.repo == "fam--course--template"
        assert d.template.clone_url.endswith("template.git")
        assert d.template.default_branch == "main"

    def test_download_delivery_has_no_template(self):
        b = _binding(delivery="download", student_repo_modes=["download"], git_server_id=None)
        d = build_course_git_descriptor("c1", b, None)
        assert d.configured is True
        assert d.delivery == "download"
        assert d.student_repo_modes == ["download"]
        assert d.template is None

    def test_default_branch_falls_back_to_main(self):
        server = SimpleNamespace(type="gitlab", base_url="https://gitlab.example")
        d = build_course_git_descriptor("c1", _binding(default_branch=None), server)
        assert d.template.default_branch == "main"

    def test_none_modes_normalize_to_empty_list(self):
        server = SimpleNamespace(type="gitlab", base_url="https://gitlab.example")
        d = build_course_git_descriptor("c1", _binding(student_repo_modes=None), server)
        assert d.student_repo_modes == []
