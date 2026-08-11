"""Structural invariants for the generated endpoint clients.

The generated package used to be the least-tested part of the library despite
being the part that broke: every one of the properties below corresponds to a
bug that shipped — request bodies with no parameter, return annotations for
values that were never returned, helper calls with no matching import, and
method names that shifted with route-registration order.

These checks read the committed output, so they fail on a bad *generator*
without needing the backend importable. `scripts/check_client_drift.py` is the
complementary check: that the committed output still matches the spec.
"""

import ast
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

ENDPOINTS_DIR = Path(__file__).resolve().parent.parent / "src" / "computor_client" / "endpoints"

MODULES = sorted(p for p in ENDPOINTS_DIR.glob("*.py") if p.name != "__init__.py")

HELPER_IMPORTS = {
    "quote_path": "from computor_client.urls import quote_path",
    "Page": "from computor_client.pagination import Page",
}


def _client_classes(tree: ast.Module):
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name.endswith("Client"):
            yield node


def _methods(cls: ast.ClassDef):
    for node in cls.body:
        if isinstance(node, ast.AsyncFunctionDef):
            yield node


def _ids(paths):
    return [p.name for p in paths]


@pytest.fixture(scope="module")
def parsed():
    return {p.name: (p.read_text(), ast.parse(p.read_text())) for p in MODULES}


def test_there_are_generated_modules():
    assert MODULES, f"no generated endpoint modules under {ENDPOINTS_DIR}"


@pytest.mark.parametrize("module", MODULES, ids=_ids(MODULES))
def test_method_names_are_unique_within_a_class(module):
    tree = ast.parse(module.read_text())
    for cls in _client_classes(tree):
        names = [m.name for m in _methods(cls)]
        duplicates = [name for name, count in Counter(names).items() if count > 1]
        assert not duplicates, f"{cls.name} defines {duplicates} more than once"


@pytest.mark.parametrize("module", MODULES, ids=_ids(MODULES))
def test_every_method_returning_a_value_actually_returns_one(module):
    """DELETE methods used to be annotated `-> List[...]` and return None."""
    tree = ast.parse(module.read_text())
    for cls in _client_classes(tree):
        for method in _methods(cls):
            annotation = ast.unparse(method.returns) if method.returns else None
            if annotation in (None, "None"):
                continue
            returns_value = any(
                isinstance(node, ast.Return) and node.value is not None
                for node in ast.walk(method)
            )
            assert returns_value, (
                f"{cls.name}.{method.name} is annotated -> {annotation} "
                "but never returns a value"
            )


@pytest.mark.parametrize("module", MODULES, ids=_ids(MODULES))
def test_helpers_are_imported_where_they_are_used(module):
    """A missing helper import fails at call time, not at import time."""
    source = module.read_text()
    for helper, import_line in HELPER_IMPORTS.items():
        used = f"{helper}(" in source or f"{helper}[" in source
        if used and import_line not in source:
            pytest.fail(f"{module.name} uses {helper} without importing it")


@pytest.mark.parametrize("module", MODULES, ids=_ids(MODULES))
def test_write_methods_can_send_their_body(module):
    """A POST/PUT/PATCH that passes json_data must accept something to send."""
    source_lines = module.read_text().splitlines()
    tree = ast.parse(module.read_text())
    for cls in _client_classes(tree):
        for method in _methods(cls):
            body = "\n".join(source_lines[method.lineno - 1 : method.end_lineno])
            if "json_data=data" not in body:
                continue
            arg_names = {a.arg for a in method.args.args}
            assert "data" in arg_names, (
                f"{cls.name}.{method.name} sends json_data=data "
                "but has no `data` parameter"
            )


@pytest.mark.parametrize("module", MODULES, ids=_ids(MODULES))
def test_paginated_list_has_a_page_companion(module):
    tree = ast.parse(module.read_text())
    for cls in _client_classes(tree):
        names = {m.name for m in _methods(cls)}
        for name in names:
            if name.endswith("_page"):
                assert name[: -len("_page")] in names, (
                    f"{cls.name}.{name} has no plain counterpart"
                )


def test_generated_output_passes_ruff_correctness_rules():
    """F = pyflakes (undefined names, unused imports), E9 = syntax errors.

    Style rules are deliberately excluded: the package has a pending
    PEP-585/604 modernization that is not this check's business.
    """
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--select", "F,E9,I", str(ENDPOINTS_DIR)],
        capture_output=True,
        text=True,
    )
    if result.returncode == 1:
        pytest.fail(f"ruff found problems in generated code:\n{result.stdout}")
    if result.returncode not in (0, 1):
        pytest.skip(f"ruff unavailable: {result.stderr.strip()[:200]}")
