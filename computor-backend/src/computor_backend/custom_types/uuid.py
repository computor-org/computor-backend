"""UUID column type that tolerates ``uuid.UUID`` instances on INSERT.

SQLAlchemy 1.4's psycopg2 dialect ships ``_PGUUID`` whose
``bind_processor`` unconditionally wraps every value with
``uuid.UUID(value)``. The stdlib constructor does
``hex.replace('urn:', '')`` on its first positional argument, so when
the value is already a ``uuid.UUID`` instance — as it is whenever a
FastAPI ``UUID`` path parameter reaches the ORM as a foreign key on
INSERT — the call raises ``AttributeError: 'UUID' object has no
attribute 'replace'`` (psycopg2 surfaces it as
``sqlalchemy.exc.StatementError``).

Wrapping the dialect type in a ``TypeDecorator`` and pre-stringifying
``uuid.UUID`` instances in ``process_bind_param`` keeps the underlying
processor seeing only strings, which it handles correctly. Loaded
values still come back as strings because the inherited
``_PGUUID.result_processor`` (with ``as_uuid=False``) stringifies
them, matching the project's existing convention.
"""

from __future__ import annotations

from uuid import UUID as _StdlibUUID

from sqlalchemy.dialects.postgresql import UUID as _PGUUID
from sqlalchemy.types import TypeDecorator


class UUID(TypeDecorator):
    """Drop-in replacement for ``postgresql.UUID``.

    Use exactly like the stock postgres ``UUID`` column type. Accepts
    ``uuid.UUID`` instances, plain strings, or ``None`` as bind
    parameters.
    """

    impl = _PGUUID
    cache_ok = True

    def __init__(self, as_uuid: bool = False) -> None:
        super().__init__()
        self.as_uuid = as_uuid

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(_PGUUID(as_uuid=self.as_uuid))

    def process_bind_param(self, value, dialect):
        if isinstance(value, _StdlibUUID):
            return str(value)
        return value
