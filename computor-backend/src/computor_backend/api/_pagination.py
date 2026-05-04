"""Pagination helpers for list endpoints.

Centralises the repeated pattern of stamping ``X-Total-Count`` and
optionally serialising rows into a list-DTO. Web clients read the
total from the response header (it's exposed via CORS in
``server.py``).
"""
from typing import Iterable, List, Optional, Type, TypeVar

from fastapi import Response
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


_TOTAL_COUNT_HEADER = "X-Total-Count"


def paginated_list(
    items: Iterable,
    total: int,
    *,
    response: Response,
    schema: Optional[Type[T]] = None,
) -> List:
    """Stamp ``X-Total-Count`` and return the list payload.

    Args:
        items: Rows to return — either ORM instances (with ``schema=``)
            or already-validated DTOs (``schema=None``).
        total: Total row count for pagination metadata; not necessarily
            ``len(items)`` when the caller is paginating.
        response: FastAPI's per-request ``Response`` (inject via the
            endpoint signature).
        schema: Optional list-DTO class. When provided, each item is
            run through ``schema.model_validate(item, from_attributes=True)``.
            Skip when items are already validated.

    Returns:
        The list payload, suitable for direct return from the endpoint.
    """
    response.headers[_TOTAL_COUNT_HEADER] = str(total)
    if schema is None:
        return list(items)
    return [schema.model_validate(item, from_attributes=True) for item in items]
