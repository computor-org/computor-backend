"""The workspace startup templates must not interpolate a secret into double quotes.

An argon2 hash is ``$argon2id$v=19$m=...$salt$digest``. Terraform substitutes it
verbatim into the rendered startup script, and inside double quotes the shell then
expands every ``$``-segment as an undefined variable — so code-server received a
mangled HASHED_PASSWORD, never matched the cookie the ingress injects, and showed
its login page to every user.

Nothing in the suite could see that: the templates are rendered by Terraform inside
Coder, and the value only breaks for secrets that happen to contain ``$``. This test
reads the templates as text and enforces the rule that makes the bug impossible.
"""

import re
from pathlib import Path

import pytest

def _templates_dir() -> Path:
    # Walk up rather than counting parents, so moving the test file cannot
    # silently turn this into a no-op.
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "ops" / "coder" / "templates"
        if candidate.is_dir():
            return candidate
    raise AssertionError("could not locate ops/coder/templates from the test file")


TEMPLATES = _templates_dir()

# The interpolations that carry a credential into the rendered shell script.
SECRET_VARS = ("app_hash", "app_secret")


def _startup_templates():
    found = sorted(TEMPLATES.glob("*/startup.sh.tftpl"))
    assert found, f"no startup templates under {TEMPLATES}"
    return found


@pytest.mark.parametrize("template", _startup_templates(), ids=lambda p: p.parent.name)
def test_secrets_are_not_interpolated_inside_double_quotes(template):
    text = template.read_text()
    offenders = []
    for var in SECRET_VARS:
        # Any double-quoted run containing ${var} is unsafe: the shell expands
        # $-sequences in the substituted value. Single quotes do not.
        for quoted in re.findall(r'"[^"\n]*"', text):
            if "${%s}" % var in quoted:
                offenders.append((var, quoted))
    assert not offenders, (
        f"{template.parent.name}/startup.sh.tftpl interpolates a secret inside double "
        f"quotes, so the shell will expand any $ in it: {offenders}. Use single quotes."
    )


def test_the_code_server_templates_still_export_a_hashed_password():
    # Guards the fix itself: if the export is renamed or dropped, the cookie the
    # ingress injects has nothing to match and the login page comes back.
    for name in ("vscode", "matlab-vscode"):
        text = (TEMPLATES / name / "startup.sh.tftpl").read_text()
        assert "export HASHED_PASSWORD='${app_hash}'" in text, name
