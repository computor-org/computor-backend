"""configure_coder_settings() must actually configure something.

Both it and ``get_coder_settings`` are exported from ``computor_backend.coder``,
but the getter never consulted the module global the setter assigned — it always
rebuilt from the environment. A test or embedder calling
``configure_coder_settings(url=...)`` therefore got no error and no effect.
"""

import pytest

from computor_backend.coder.config import (
    configure_coder_settings,
    get_coder_settings,
    reset_coder_settings,
)


@pytest.fixture(autouse=True)
def _restore_settings():
    """Never leak an override into the rest of the suite."""
    yield
    reset_coder_settings()


@pytest.mark.unit
class TestConfigureCoderSettings:
    def test_the_override_is_what_the_getter_returns(self):
        configure_coder_settings(url="https://coder.test.invalid")

        assert get_coder_settings().url == "https://coder.test.invalid"

    def test_the_returned_object_is_the_installed_one(self):
        configured = configure_coder_settings(url="https://coder.test.invalid")

        assert get_coder_settings() is configured

    def test_extra_settings_come_through_too(self):
        configure_coder_settings(
            url="https://coder.test.invalid", admin_email="admin@test.invalid"
        )
        settings = get_coder_settings()

        assert settings.admin_email == "admin@test.invalid"

    def test_reset_goes_back_to_the_environment(self):
        configure_coder_settings(url="https://coder.test.invalid")
        assert get_coder_settings().url == "https://coder.test.invalid"

        reset_coder_settings()

        assert get_coder_settings().url != "https://coder.test.invalid"

    def test_reconfiguring_replaces_the_previous_override(self):
        configure_coder_settings(url="https://first.test.invalid")
        configure_coder_settings(url="https://second.test.invalid")

        assert get_coder_settings().url == "https://second.test.invalid"
