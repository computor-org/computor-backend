"""Synchronous facade over the Computor API.

``ComputorClient`` is async-only, which pushed the sync CLI to grow several
ad-hoc ``httpx.Client`` shims that each reached into private client attributes
to steal the base URL, headers and token. ``SyncComputorClient`` is the single
sync entry point: build it directly from a base URL + headers, or from an
existing ``ComputorClient`` via :meth:`from_client`. It raises the same typed
exceptions as the async client (via ``exceptions.raise_for_response``).
"""
from typing import Any, Dict, Optional

import httpx

from computor_client.exceptions import raise_for_response


class SyncComputorClient:
    """Blocking HTTP client for the Computor API.

    Usable as a context manager. Response bodies are returned as parsed JSON
    (or ``None`` for empty bodies); non-2xx responses raise a
    ``ComputorClientError`` subclass.
    """

    def __init__(
        self,
        base_url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
    ):
        merged = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **(headers or {}),
        }
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers=merged,
            timeout=httpx.Timeout(timeout),
        )

    @classmethod
    def from_client(cls, client) -> "SyncComputorClient":
        """Build a sync client sharing ``client``'s base URL, auth headers and timeout."""
        return cls(
            client.base_url,
            headers=client.auth_headers,
            timeout=client.timeout,
        )

    # ------------------------------------------------------------------
    # Core request
    # ------------------------------------------------------------------

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
    ) -> Any:
        response = self._client.request(method, path, params=params, json=json)
        raise_for_response(response)
        return response.json() if response.content else None

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self.request("GET", path, params=params)

    # Alias used by CLI CRUD helpers.
    def list(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self.request("GET", path, params=params)

    def create(self, path: str, data: Optional[Dict[str, Any]] = None) -> Any:
        return self.request("POST", path, json=data or {})

    def post(self, path: str, data: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Any:
        return self.request("POST", path, params=params, json=data or {})

    def update(self, path: str, data: Optional[Dict[str, Any]] = None) -> Any:
        return self.request("PATCH", path, json=data or {})

    def patch(self, path: str, data: Optional[Dict[str, Any]] = None) -> Any:
        return self.request("PATCH", path, json=data or {})

    def put(self, path: str, data: Optional[Dict[str, Any]] = None) -> Any:
        return self.request("PUT", path, json=data or {})

    def delete(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self.request("DELETE", path, params=params)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SyncComputorClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __del__(self):
        try:
            self._client.close()
        except Exception:
            pass
