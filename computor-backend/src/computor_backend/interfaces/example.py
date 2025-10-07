"""Backend Example interfaces with SQLAlchemy models."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.example import (
    ExampleInterface as ExampleInterfaceBase,
    ExampleRepositoryInterface as ExampleRepositoryInterfaceBase,
    ExampleQuery,
    ExampleRepositoryQuery,
)
from computor_types.custom_types import Ltree
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
        if params is None:
            return query

        if params.id is not None:
            query = query.filter(ExampleRepository.id == params.id)
        if params.name is not None:
            query = query.filter(ExampleRepository.name.ilike(f"%{params.name}%"))
        if params.source_type is not None:
            query = query.filter(ExampleRepository.source_type == params.source_type)
        if params.organization_id is not None:
            query = query.filter(ExampleRepository.organization_id == params.organization_id)

        return query


class ExampleInterface(ExampleInterfaceBase, BackendEntityInterface):
    """Backend-specific Example interface with model and API configuration."""

    model = Example
    endpoint = "examples"
    cache_ttl = 300

    @staticmethod
    def search(db: Session, query, params: Optional[ExampleQuery]):
        """Apply search filters to example query."""
        if params is None:
            return query

        if params.id is not None:
            query = query.filter(Example.id == params.id)
        if params.repository_id is not None:
            query = query.filter(Example.example_repository_id == params.repository_id)
        if params.identifier is not None:
            # Support Ltree pattern matching with *
            if '*' in params.identifier:
                query = query.filter(Example.identifier.op('~')(params.identifier))
            else:
                # Convert string to Ltree for proper comparison
                query = query.filter(Example.identifier == Ltree(params.identifier))
        if params.title is not None:
            query = query.filter(Example.title.ilike(f"%{params.title}%"))
        if params.category is not None:
            query = query.filter(Example.category == params.category)
        if params.tags is not None and len(params.tags) > 0:
            # Filter by tags (array contains all specified tags)
            query = query.filter(Example.tags.contains(params.tags))
        if params.search is not None:
            # Full-text search in title and description
            search_term = f"%{params.search}%"
            query = query.filter(
                (Example.title.ilike(search_term)) |
                (Example.description.ilike(search_term))
            )

        return query
