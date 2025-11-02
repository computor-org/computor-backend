"""
Service Type API endpoints.

Provides CRUD operations for service type definitions.
Service types use UUID + Ltree hybrid approach for stable references
and hierarchical organization.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, Response, HTTPException
from sqlalchemy.orm import Session

from computor_backend.business_logic.crud import (
    create_entity as create_db,
    get_entity_by_id as get_id_db,
    list_entities as list_db,
    update_entity as update_db,
)
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.database import get_db
from computor_backend.model.service import ServiceType
from computor_types.service_type import (
    ServiceTypeCreate,
    ServiceTypeGet,
    ServiceTypeList,
    ServiceTypeUpdate,
    ServiceTypeQuery,
)
from computor_backend.interfaces.service_type import ServiceTypeInterface


service_type_router = APIRouter()


@service_type_router.post("", response_model=ServiceTypeGet)
async def create_service_type(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    entity: ServiceTypeCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new service type.

    Requires: service_type:create permission

    Example:
        POST /service-types
        {
            "path": "testing.rust",
            "name": "Rust Testing System",
            "description": "Rust code compilation and testing",
            "category": "testing",
            "plugin_module": "computor_backend.plugins.testing.rust",
            "enabled": true
        }
    """
    return await create_db(permissions, db, entity, ServiceType, ServiceTypeGet)


@service_type_router.get("/{entity_id}", response_model=ServiceTypeGet)
async def get_service_type(
    entity_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
):
    """
    Get a single service type by UUID.

    Requires: service_type:get permission

    Example:
        GET /service-types/123e4567-e89b-12d3-a456-426614174000
    """
    return await get_id_db(permissions, db, entity_id, ServiceType, ServiceTypeGet)


@service_type_router.get("", response_model=list[ServiceTypeList])
async def list_service_types(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    response: Response,
    params: ServiceTypeQuery = Depends(),
    db: Session = Depends(get_db)
):
    """
    List service types with filtering.

    Requires: service_type:list permission

    Query parameters:
        - path: Exact path match
        - path_descendant: Get all descendants (e.g., 'testing' returns all testing.*)
        - path_pattern: Ltree lquery pattern
        - category: Filter by category
        - enabled: Filter by enabled status
        - skip: Pagination offset
        - limit: Pagination limit

    Examples:
        GET /service-types
        GET /service-types?category=testing
        GET /service-types?path_descendant=testing
        GET /service-types?enabled=true
    """
    data, total = await list_db(permissions, db, params, ServiceTypeInterface)
    response.headers["X-Total-Count"] = str(total)
    return data


@service_type_router.patch("/{entity_id}", response_model=ServiceTypeGet)
async def update_service_type(
    entity_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    entity: ServiceTypeUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing service type.

    Requires: service_type:update permission

    Note: The 'path' field cannot be updated (use id for stable references).

    Example:
        PATCH /service-types/123e4567-e89b-12d3-a456-426614174000
        {
            "name": "Updated Name",
            "description": "Updated description",
            "enabled": false
        }
    """
    return await update_db(permissions, db, entity_id, entity, ServiceType, ServiceTypeGet)
