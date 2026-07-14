"""Assertion helpers for payload / exception contract tests.

`assert_error` pins the (status, error_code) contract from the backend error
registry (`computor_backend/exceptions/error_registry.py`); `assert_shape`
validates a success payload against its `computor_types` DTO.
"""

from __future__ import annotations

from typing import Any

import httpx


def error_code(resp: httpx.Response) -> str | None:
    try:
        return resp.json().get("error_code")
    except Exception:
        return None


def assert_error(resp: httpx.Response, status: int, code: str | None = None) -> None:
    assert resp.status_code == status, (
        f"expected {status}, got {resp.status_code}: {resp.text[:300]}"
    )
    if code is not None:
        assert error_code(resp) == code, (
            f"expected error_code {code!r}, got {error_code(resp)!r}: {resp.text[:300]}"
        )


def assert_shape(resp: httpx.Response, model: Any) -> Any:
    """Validate a 2xx response body against a pydantic DTO; return the model."""
    assert resp.status_code in (200, 201), f"{resp.status_code}: {resp.text[:300]}"
    return model.model_validate(resp.json())
