"""Paginated list results.

Computor list endpoints return a plain JSON array and report the *total* row
count out-of-band, in the ``X-Total-Count`` response header (see
``computor_backend/api/_pagination.py``). A caller that only reads the body
therefore cannot tell a complete result from a truncated first page — the usual
symptom being someone raising ``limit`` until things stop disappearing.

``Page`` carries the total alongside the items so pagination can be driven
correctly.
"""

from typing import Any, Generic, Iterator, List, Optional, Sequence, Type, TypeVar

import httpx
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

TOTAL_COUNT_HEADER = "X-Total-Count"


class Page(Sequence[T], Generic[T]):
    """One page of a list endpoint's results, plus the total row count.

    Behaves as a read-only sequence of ``items``, so it can be iterated,
    indexed and ``len()``-ed directly.

    Attributes:
        items: The rows in this page.
        total: Total number of rows matching the query, across all pages.
            Falls back to ``len(items)`` when the server sent no
            ``X-Total-Count`` header.
        skip: The offset this page was requested with.
        limit: The page size this page was requested with.
    """

    __slots__ = ("items", "total", "skip", "limit")

    def __init__(self, items: List[T], total: int, skip: int = 0, limit: int = 0):
        self.items = items
        self.total = total
        self.skip = skip
        self.limit = limit

    @property
    def has_more(self) -> bool:
        """True when rows remain beyond this page."""
        return self.skip + len(self.items) < self.total

    @property
    def next_skip(self) -> int:
        """The ``skip`` value that fetches the following page."""
        return self.skip + len(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index):  # type: ignore[override]
        return self.items[index]

    def __iter__(self) -> Iterator[T]:
        return iter(self.items)

    def __repr__(self) -> str:
        return (
            f"Page(items={len(self.items)}, total={self.total}, "
            f"skip={self.skip}, limit={self.limit})"
        )

    @classmethod
    def from_response(
        cls,
        response: httpx.Response,
        model: Optional[Type[T]] = None,
        *,
        skip: int = 0,
        limit: int = 0,
    ) -> "Page[T]":
        """Build a page from a list response.

        Args:
            response: The httpx response for a list request.
            model: DTO to validate each row into. ``None`` leaves rows as
                the raw decoded JSON.
            skip: The offset the request was made with.
            limit: The page size the request was made with.

        Raises:
            TypeError: If the body is not a JSON array. Silently returning an
                empty page here would turn a response-shape change into "no
                results", which is how it used to fail.
        """
        data: Any = response.json()
        if not isinstance(data, list):
            raise TypeError(
                f"Expected a JSON array from {response.request.method} "
                f"{response.request.url.path}, got {type(data).__name__}"
            )

        items: List[Any] = [model.model_validate(row) for row in data] if model else data

        raw_total = response.headers.get(TOTAL_COUNT_HEADER)
        try:
            total = int(raw_total) if raw_total is not None else len(items)
        except ValueError:
            total = len(items)

        return cls(items, total, skip=skip, limit=limit)
