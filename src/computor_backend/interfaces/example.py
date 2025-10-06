"""Backend Example interfaces with SQLAlchemy models."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.example import (
    ExampleInterface as ExampleInterfaceBase,
    ExampleRepositoryInterface as ExampleRepositoryInterfaceBase,
    ExampleQuery,
    ExampleRepositoryQuery,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.example import Example, ExampleRepository


class ExampleRepositoryInterface(ExampleRepositoryInterfaceBase, BackendEntityInterface):
    """Backend-specific ExampleRepository interface with model and API configuration."""

    model = ExampleRepository
    endpoint = "example-repositories"
    cache_ttl = 600

    @staticmethod
    def search(db: Session, query, params: Optional[ExampleRepositoryQuery]):
        """Apply search filters to example repository query."""
        if params.id is not None:
            query = query.filter(ExampleRepository.id == params.id)
        if params.title is not None:
            query = query.filter(ExampleRepository.title == params.title)
        if params.url is not None:
            query = query.filter(ExampleRepository.url == params.url)
        if params.archived is not None and params.archived:
            query = query.filter(ExampleRepository.archived_at.isnot(None))
        else:
            query = query.filter(ExampleRepository.archived_at.is_(None))

        return query


class ExampleInterface(ExampleInterfaceBase, BackendEntityInterface):
    """Backend-specific Example interface with model and API configuration."""

    model = Example
    endpoint = "examples"
    cache_ttl = 300

    @staticmethod
    def search(db: Session, query, params: Optional[ExampleQuery]):
        """Apply search filters to example query."""
        if params.id is not None:
            query = query.filter(Example.id == params.id)
        if params.title is not None:
            query = query.filter(Example.title == params.title)
        if params.example_repository_id is not None:
            query = query.filter(Example.example_repository_id == params.example_repository_id)
        if params.archived is not None and params.archived:
            query = query.filter(Example.archived_at.isnot(None))
        else:
            query = query.filter(Example.archived_at.is_(None))

        return query
