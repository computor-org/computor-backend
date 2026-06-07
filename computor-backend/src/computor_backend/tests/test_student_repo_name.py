"""Unit tests for ``student_repo_name`` — the collision-free naming that
replaces the legacy bare-``username`` Forgejo student repo name."""
from computor_backend.business_logic.course_git import student_repo_name


class TestStudentRepoName:
    def test_strips_trailing_template_token(self):
        assert student_repo_name("math--algo--template", "mmusterm") == "math--algo-mmusterm"

    def test_strips_simple_template_suffix(self):
        assert student_repo_name("algo-template", "jdoe") == "algo-jdoe"

    def test_underscore_template_suffix(self):
        assert student_repo_name("algo_template", "jdoe") == "algo-jdoe"

    def test_case_insensitive_template(self):
        assert student_repo_name("Algo-Template", "jdoe") == "Algo-jdoe"

    def test_no_template_suffix_kept_whole(self):
        assert student_repo_name("starter", "jdoe") == "starter-jdoe"

    def test_includes_handle_so_distinct_students_differ(self):
        a = student_repo_name("c--template", "alice")
        b = student_repo_name("c--template", "bob")
        assert a != b and a.endswith("-alice") and b.endswith("-bob")

    def test_template_only_name_falls_back(self):
        # A repo literally named "template" reduces to a non-empty base.
        assert student_repo_name("template", "jdoe") == "repo-jdoe"
