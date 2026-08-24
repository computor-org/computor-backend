"""Which repository a template deploy pushes to.

The binding is authoritative when it names a template; legacy
``course.properties['gitlab']`` is the fallback for courses that never got one.
Before this, the legacy value overrode the binding unconditionally — so a
binding could name one repository while the deploy pushed to another, and the
comment above the code said the opposite of what the code did.

Pure projection, no DB: ``_binding_deploy_urls`` takes the binding and returns
the two URLs, so the precedence can be tested without a request or a session.
"""

from types import SimpleNamespace

from computor_backend.api.system import _binding_deploy_urls


def gitlab_binding(**overrides):
    """A binding as adoption writes one: legacy repository names throughout."""
    defaults = dict(
        template_url="https://gitlab.example.org/org/fam/course/student-template.git",
        properties={"gitlab": {"reference_path": "org/fam/course/assignments"}},
        git_server=SimpleNamespace(base_url="https://gitlab.example.org"),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestBindingDeployUrls:
    def test_returns_the_template_the_binding_names(self):
        template, _ = _binding_deploy_urls(gitlab_binding())
        assert template == "https://gitlab.example.org/org/fam/course/student-template.git"

    def test_builds_the_reference_url_from_the_mapped_path(self):
        """An adopted course's reference repository is called `assignments`;
        a natively provisioned one is called `reference`. Neither name is
        assumed — both come off the binding."""
        _, reference = _binding_deploy_urls(gitlab_binding())
        assert reference == "https://gitlab.example.org/org/fam/course/assignments.git"

    def test_reads_the_forgejo_reference_ref(self):
        binding = gitlab_binding(
            template_url="https://git.example.org/itpcp-2026/template.git",
            properties={"forgejo": {"reference_repo": "itpcp-2026/reference"}},
            git_server=SimpleNamespace(base_url="https://git.example.org"),
        )
        _, reference = _binding_deploy_urls(binding)
        assert reference == "https://git.example.org/itpcp-2026/reference.git"

    def test_no_reference_configured_yields_none(self):
        _, reference = _binding_deploy_urls(gitlab_binding(properties={}))
        assert reference is None

    def test_a_binding_without_a_template_defers_to_the_caller(self):
        """Returning (None, None) is what lets the endpoint fall through to the
        legacy properties path for an un-migrated course."""
        assert _binding_deploy_urls(gitlab_binding(template_url=None)) == (None, None)

    def test_no_binding_at_all_defers_to_the_caller(self):
        assert _binding_deploy_urls(None) == (None, None)

    def test_reference_needs_a_server_to_resolve_against(self):
        _, reference = _binding_deploy_urls(gitlab_binding(git_server=None))
        assert reference is None

    def test_tolerates_a_trailing_slash_on_the_server_url(self):
        binding = gitlab_binding(git_server=SimpleNamespace(base_url="https://gitlab.example.org/"))
        _, reference = _binding_deploy_urls(binding)
        assert reference == "https://gitlab.example.org/org/fam/course/assignments.git"

    def test_tolerates_properties_being_null(self):
        _, reference = _binding_deploy_urls(gitlab_binding(properties=None))
        assert reference is None
