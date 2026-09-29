"""Every template push must carry explicit, positive memory/CPU caps.

Coder carries a template variable's previous value forward when a push omits
it (including the old "0" = unlimited default), so a missing or zero cap in the
push arguments would leave existing fleets unlimited. These tests run the real
argument builder against the checked-in templates.
"""

import os

import pytest

from computor_backend.tasks.temporal_coder_setup import _optional_push_variable_args

TEMPLATES = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "ops", "coder", "templates")
)


def _vars(template, variables=None):
    args = _optional_push_variable_args(os.path.join(TEMPLATES, template), variables)
    pairs = [args[i + 1] for i in range(0, len(args), 2)]
    assert all(args[i] == "--variable" for i in range(0, len(args), 2))
    return dict(p.split("=", 1) for p in pairs)


@pytest.mark.parametrize(
    "template", ["vscode", "bash", "jupyter", "ubuntu-desktop", "matlab-ui", "matlab-vscode"]
)
@pytest.mark.parametrize("given", [None, {}, {"memory_mb": "0", "cpus": "0"}, {"cpus": ""}])
def test_push_always_carries_positive_caps(template, given):
    pushed = _vars(template, given)
    assert float(pushed["memory_mb"]) > 0
    assert float(pushed["cpus"]) > 0


def test_defaults_come_from_template_file():
    assert _vars("vscode")["memory_mb"] == "3072"
    assert _vars("vscode")["cpus"] == "2"
    assert _vars("matlab-vscode")["memory_mb"] == "6144"


def test_explicit_positive_overrides_win():
    pushed = _vars("vscode", {"memory_mb": "4096", "cpus": "1.5"})
    assert pushed["memory_mb"] == "4096"
    assert pushed["cpus"] == "1.5"


def test_invalid_values_never_mean_unlimited():
    pushed = _vars("vscode", {"memory_mb": "-1", "cpus": "nan"})
    assert pushed["memory_mb"] == "3072"
    assert pushed["cpus"] == "2"


def test_deployment_default_when_template_default_is_unlimited(tmp_path, monkeypatch):
    (tmp_path / "variables.tf").write_text(
        'variable "memory_mb" {\n  default = 0\n  type = number\n}\n'
        'variable "cpus" {\n  default = ""\n  type = string\n}\n'
    )
    monkeypatch.setenv("CODER_WORKSPACE_DEFAULT_MEMORY_MB", "2048")
    args = _optional_push_variable_args(str(tmp_path), {"memory_mb": "0"})
    assert "memory_mb=2048" in args
    assert "cpus=2" in args


def test_undeclared_caps_are_not_pushed(tmp_path):
    (tmp_path / "main.tf").write_text('variable "other" {\n  default = "x"\n}\n')
    assert _optional_push_variable_args(str(tmp_path), {"other": "y"}) == [
        "--variable",
        "other=y",
    ]
