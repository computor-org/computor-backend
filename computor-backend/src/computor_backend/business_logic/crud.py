"""
Business logic for generic CRUD operations.

This module contains core CRUD business logic extracted from api/crud.py,
following the business logic layer pattern. These functions handle database
operations, permission checks, and validation, wrapped in threadpool for
async/await compatibility.
"""

from uuid import UUID
from typing import Any, Optional, Callable
from datetime import datetime, timezone
from enum import Enum

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import exc
from sqlalchemy.inspection import inspect
from starlette.concurrency import run_in_threadpool

from computor_backend.api.exceptions import (
    BadRequestException,
    NotFoundException,
    InternalServerException
)
from computor_backend.permissions.core import check_permissions
from computor_backend.permissions.handlers import permission_registry
from computor_backend.permissions.principal import Principal
from computor_types.base import EntityInterface, ListQuery
from computor_backend.custom_types import Ltree, LtreeType
from computor_types.tasks import TaskStatus, map_task_status_to_int
from computor_backend.database import set_db_user


async def create_entity(
    permissions: Principal,
    db: Session,
    entity: BaseModel,
    db_type: Any,
    response_type: BaseModel,
    post_create: Optional[Callable] = None
) -> BaseModel:
    """
    Create a new database entity with permission checks and validation.

    Args:
        permissions: Current user's permission context
        db: Database session
        entity: Pydantic model with entity data
        db_type: SQLAlchemy model class
        response_type: Pydantic response model class
        post_create: Optional async callback after creation

    Returns:
        Created entity as response_type instance

    Raises:
        NotFoundException: If user lacks create permission
        BadRequestException: If validation or integrity constraints fail
    """
    # Set user context for audit tracking (created_by/updated_by)
    set_db_user(db, permissions.user_id)

    # Authorization for create
    # 1) Admin shortcut
    if not permissions.is_admin:
        # 2) Consult handler if registered; handlers are the source of truth
        handler = permission_registry.get_handler(db_type)
        # Extract context identifiers from the payload (e.g., any *_id fields)
        if isinstance(entity, BaseModel):
            model_dump = entity.model_dump(exclude_unset=True)
        else:
            model_dump = entity or {}
        # Build a simple context dict of *_id keys for handler use
        context = {k: str(v) for k, v in model_dump.items() if k.endswith("_id") and v is not None}

        if handler is None:
            # Fallback behavior per permissions.md: no handler → admin-only
            raise NotFoundException()

        # Require handler to permit creation with the provided context
        if not handler.can_perform_action(permissions, "create", resource_id=None, context=context):
            # Explicitly deny without attempting permissive fallbacks
            raise NotFoundException()

    try:
        model_dump = entity.model_dump(exclude_unset=True)

        # Wrap blocking database operations in threadpool
        def _create_entity():
            # columns of custom postgresql type Ltree needs to be treated separately
            mapper = inspect(db_type)

            for column in mapper.columns.keys():
                if isinstance(mapper.columns[column].type, LtreeType):
                    if column in model_dump.keys() and model_dump[column] is not None and isinstance(model_dump[column], str):
                        model_dump[column] = Ltree(model_dump[column])

            db_item = db_type(**model_dump)

            db.add(db_item)
            db.commit()
            db.refresh(db_item)
            return db_item

        db_item = await run_in_threadpool(_create_entity)

        response = response_type.model_validate(db_item, from_attributes=True)

        # Execute post-create hook if provided (always async)
        if post_create is not None:
            await post_create(db_item, db)

        return response
    except exc.IntegrityError as e:
        db.rollback()
        # Just provide a cleaner version of the database error without hardcoding constraint names
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        # Try to extract just the first line and clean it up a bit
        if 'DETAIL:' in error_msg:
            # Include the DETAIL part which often has useful info
            main_error = error_msg.split('\n')[0]
            detail_part = error_msg.split('DETAIL:')[1].split('\n')[0].strip()
            clean_msg = f"{main_error}. {detail_part}"
        else:
            clean_msg = error_msg.split('\n')[0] if '\n' in error_msg else error_msg
        raise BadRequestException(detail=clean_msg)

    except Exception as e:
        print(e.args)
        db.rollback()
        raise BadRequestException(detail=e.args)


async def get_entity_by_id(
    permissions: Principal,
    db: Session,
    id: UUID | str,
    interface: EntityInterface,
    scope: str = "get"
) -> BaseModel:
    """
    Retrieve a single entity by ID with permission filtering.

    Args:
        permissions: Current user's permission context
        db: Database session
        id: Entity ID (UUID or string)
        interface: EntityInterface defining model and response schema
        scope: Permission scope (default: "get")

    Returns:
        Entity as interface.get model instance

    Raises:
        NotFoundException: If entity not found or user lacks permission
        BadRequestException: If query parameters are invalid
    """
    db_type = interface.model

    query = check_permissions(permissions, db_type, scope, db)

    if query is None:
        raise NotFoundException()

    try:
        # Wrap blocking query in threadpool
        def _get_entity():
            return query.filter(db_type.id == id).first()

        item = await run_in_threadpool(_get_entity)

        if item is None:
            raise NotFoundException(detail=f"{db_type.__name__} with id [{id}] not found")

        return interface.get.model_validate(item, from_attributes=True)

    except HTTPException as e:
        raise e

    except exc.StatementError as e:
        raise BadRequestException(detail=e.args)

    except Exception as e:
        raise NotFoundException(detail=e.args)


async def list_entities(
    permissions: Principal,
    db: Session,
    params: ListQuery,
    interface: EntityInterface
) -> tuple[list[BaseModel], int]:
    """
    List entities with pagination and permission filtering.

    Args:
        permissions: Current user's permission context
        db: Database session
        params: Query parameters (limit, skip, filters)
        interface: EntityInterface defining model and search logic

    Returns:
        Tuple of (list of entities, total count)

    Raises:
        None - Returns empty list if no permission
    """
    db_type = interface.model
    query_func = interface.search

    query = check_permissions(permissions, db_type, "list", db)

    if query is None:
        return [], 0

    query = query_func(db, query, params)

    # Wrap blocking pagination queries in threadpool
    def _get_paginated_results():
        total = query.order_by(None).count()

        paginated_query = query
        if params.limit is not None:
            paginated_query = paginated_query.limit(params.limit)
        if params.skip is not None:
            paginated_query = paginated_query.offset(params.skip)

        results = paginated_query.all()
        return results, total

    results, total = await run_in_threadpool(_get_paginated_results)

    query_result = [interface.list.model_validate(entity, from_attributes=True) for entity in results]

    return query_result, total


async def update_entity(
    permissions: Principal,
    db: Session,
    id: UUID | str | None,
    entity: Any,
    db_type: Any,
    response_type: BaseModel,
    post_update: Optional[Callable] = None
) -> BaseModel:
    """
    Update an existing entity with permission checks.

    Args:
        permissions: Current user's permission context
        db: Database session
        id: Entity ID to update
        entity: Update data (BaseModel or dict)
        db_type: SQLAlchemy model class
        response_type: Pydantic response model class
        post_update: Optional async callback after update

    Returns:
        Updated entity as response_type instance

    Raises:
        NotFoundException: If entity not found or user lacks permission
        BadRequestException: If update fails validation
    """
    # Set user context for audit tracking (updated_by)
    set_db_user(db, permissions.user_id)

    # Wrap blocking database operations in threadpool
    def _update_entity():
        if id is not None:
            query = check_permissions(permissions, db_type, "update", db)

            if query is None:
                raise NotFoundException()

            db_item = query.filter(db_type.id == id).first()

            if db_item is None:
                raise NotFoundException()

        if isinstance(entity, BaseModel):
            entity_dict = entity.model_dump(exclude_unset=True)
        else:
            entity_dict = entity

        old_db_item = response_type(**db_item.__dict__)

        # Handle Ltree columns specially
        mapper = inspect(db_type)
        for column in mapper.columns.keys():
            if isinstance(mapper.columns[column].type, LtreeType):
                if column in entity_dict.keys() and entity_dict[column] is not None and isinstance(entity_dict[column], str):
                    entity_dict[column] = Ltree(entity_dict[column])

        try:
            for key in entity_dict.keys():
                attr = entity_dict.get(key)
                if isinstance(attr, TaskStatus):
                    attr = map_task_status_to_int(attr)
                elif isinstance(attr, Enum):
                    attr = attr.value
                setattr(db_item, key, attr)

            db.commit()
            db.refresh(db_item)

            return db_item, old_db_item

        except Exception as e:
            db.rollback()
            print(f"Exception in update_entity: {e}")
            print(f"Exception type: {type(e)}")
            print(f"Exception args: {e.args}")
            import traceback
            traceback.print_exc()
            raise BadRequestException(detail=str(e))

    db_item, old_db_item = await run_in_threadpool(_update_entity)

    # Execute post-update hook if provided (always async, outside threadpool)
    if post_update is not None:
        await post_update(db_item, old_db_item, db)

    return response_type(**db_item.__dict__)


def _validate_course_content_deletion(entity, db: Session):
    """
    Validate that a course content can be safely deleted.

    Rules:
    1. Cannot delete if this course content or any descendant has submission artifacts
    2. Deleting a parent will cascade delete all descendants via Ltree path

    Args:
        entity: CourseContent entity to delete
        db: Database session

    Raises:
        BadRequestException: If deletion would violate business rules
    """
    from computor_backend.model.course import CourseContent, SubmissionGroup
    from computor_backend.model.artifact import SubmissionArtifact
    from sqlalchemy import and_

    # Find all descendants (including this course content)
    # Ltree path matching: descendant.path <@ parent.path means "descendant is under parent"
    # We use path @> entity.path to find "paths that contain entity.path"
    descendants = db.query(CourseContent).filter(
        CourseContent.path.op('<@')(entity.path)  # Ltree descendant-of operator
    ).all()

    descendant_ids = [d.id for d in descendants]

    if not descendant_ids:
        return  # No descendants, safe to delete

    # Check if any descendant has submission artifacts
    has_submissions = db.query(SubmissionArtifact).join(
        SubmissionGroup,
        SubmissionArtifact.submission_group_id == SubmissionGroup.id
    ).filter(
        SubmissionGroup.course_content_id.in_(descendant_ids)
    ).first()

    if has_submissions:
        if len(descendant_ids) == 1:
            # Only this course content
            raise BadRequestException(
                detail="Cannot delete this course content because students have already submitted work. "
                       "Deletion would result in data loss."
            )
        else:
            # Parent with descendants that have submissions
            raise BadRequestException(
                detail=f"Cannot delete this course content because it contains {len(descendant_ids)-1} "
                       f"descendant item(s) with student submissions. Deletion would result in data loss."
            )


async def delete_entity(
    permissions: Principal,
    db: Session,
    id: UUID | str,
    db_type: Any
) -> dict:
    """
    Delete an entity with permission checks and cascade handling.

    Args:
        permissions: Current user's permission context
        db: Database session
        id: Entity ID to delete
        db_type: SQLAlchemy model class

    Returns:
        Dict with {"ok": True} on success

    Raises:
        NotFoundException: If entity not found or user lacks permission
        BadRequestException: If delete violates integrity constraints
        InternalServerException: If unexpected database error occurs
    """
    # Wrap blocking database operations in threadpool
    def _delete_entity():
        from computor_backend.model.course import CourseContent

        query = check_permissions(permissions, db_type, "delete", db)

        entity = query.filter(db_type.id == id).first()

        if not entity:
            raise NotFoundException(detail=f"{db_type.__name__} not found")

        # Special validation for CourseContent deletion
        if db_type.__tablename__ == 'course_content':
            _validate_course_content_deletion(entity, db)

            # Delete all descendants via Ltree path
            # This will cascade delete submission_groups, which cascade delete submission_artifacts
            descendants = db.query(CourseContent).filter(
                CourseContent.path.op('<@')(entity.path),
                CourseContent.id != entity.id  # Exclude self, will be deleted below
            ).all()

            for descendant in descendants:
                db.delete(descendant)
            # Note: self (entity) will be deleted below

        try:
            db.delete(entity)
            db.commit()
        except exc.IntegrityError as e:
            db.rollback()
            # Handle foreign key constraint violations
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)

            # Parse the error message to provide user-friendly feedback
            if 'NotNullViolation' in error_msg:
                # This happens when deleting would cause NULL in a required foreign key
                if 'course_content_type_id' in error_msg and 'course_content' in error_msg:
                    raise BadRequestException(
                        detail="Cannot delete this course content type because it is still being used by course content items. Please remove or reassign all course content using this type first."
                    )
                else:
                    # Generic not null violation message
                    raise BadRequestException(
                        detail="Cannot delete this item because it would violate data integrity constraints. Other records depend on this item."
                    )
            elif 'ForeignKeyViolation' in error_msg or 'violates foreign key constraint' in error_msg:
                # Extract table name if possible for better error message
                if 'table' in error_msg:
                    # Try to extract table name from error
                    import re
                    table_match = re.search(r'table "(\w+)"', error_msg)
                    if table_match:
                        table_name = table_match.group(1)
                        raise BadRequestException(
                            detail=f"Cannot delete this {db_type.__tablename__.replace('_', ' ')} because it is referenced by records in {table_name.replace('_', ' ')}. Please remove those references first."
                        )

                # Generic foreign key violation message
                raise BadRequestException(
                    detail=f"Cannot delete this {db_type.__tablename__.replace('_', ' ')} because other records depend on it. Please remove all references to this item first."
                )
            elif 'UniqueViolation' in error_msg:
                # This shouldn't happen on delete, but handle it just in case
                raise BadRequestException(detail="A unique constraint violation occurred while deleting.")
            else:
                # Generic integrity error
                raise BadRequestException(
                    detail=f"Cannot delete this item due to data integrity constraints. Error: {error_msg.split('DETAIL:')[0] if 'DETAIL:' in error_msg else error_msg}"
                )
        except exc.SQLAlchemyError as e:
            db.rollback()
            # Handle other SQLAlchemy errors
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            print(f"SQLAlchemyError in delete_entity: {error_msg}")
            raise InternalServerException(detail="An unexpected database error occurred while deleting.")
        except Exception as e:
            db.rollback()
            print(f"Unexpected error in delete_entity: {e}")
            raise InternalServerException(detail="An unexpected error occurred while deleting.")

        return {"ok": True}

    return await run_in_threadpool(_delete_entity)


async def archive_entity(
    permissions: Principal,
    db: Session,
    id: UUID | str | None,
    db_type: Any,
    db_item: Any = None
) -> dict:
    """
    Archive (soft delete) an entity by setting archived_at timestamp.

    Args:
        permissions: Current user's permission context
        db: Database session
        id: Entity ID to archive (if db_item not provided)
        db_type: SQLAlchemy model class
        db_item: Optional pre-fetched entity instance

    Returns:
        Dict with {"ok": True} on success

    Raises:
        NotFoundException: If entity not found or user lacks permission
        BadRequestException: If archiving violates constraints
        InternalServerException: If unexpected database error occurs
    """
    # Wrap blocking database operations in threadpool
    def _archive_entity():
        nonlocal db_item

        query = check_permissions(permissions, db_type, "archive", db)

        try:
            if db_item is None and id is not None:
                db_item = query.filter(db_type.id == id).first()

            if not db_item:
                raise NotFoundException(detail=f"{db_type.__name__} not found")

            setattr(db_item, "archived_at", datetime.now(timezone.utc))

            db.commit()
            db.refresh(db_item)
        except NotFoundException:
            raise
        except exc.IntegrityError as e:
            db.rollback()
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            raise BadRequestException(detail=f"Cannot archive this item due to data integrity constraints.")
        except exc.SQLAlchemyError as e:
            db.rollback()
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            print(f"SQLAlchemyError in archive_entity: {error_msg}")
            raise InternalServerException(detail="An unexpected database error occurred while archiving.")
        except Exception as e:
            db.rollback()
            print(f"Unexpected error in archive_entity: {e}")
            raise InternalServerException(detail="An unexpected error occurred while archiving.")

        return {"ok": True}

    return await run_in_threadpool(_archive_entity)


async def filter_entities(
    permissions: Principal,
    db: Session,
    db_type: Any,
    params: ListQuery,
    query_func: Callable,
    filter: Optional[dict] = None
):
    """
    Filter entities with custom query function and optional filters.

    Args:
        permissions: Current user's permission context
        db: Database session
        db_type: SQLAlchemy model class
        params: Query parameters (limit, skip, filters)
        query_func: Function to build query
        filter: Optional filter dictionary

    Returns:
        SQLAlchemy Query object (executed in threadpool when needed)

    Note:
        Returns empty list if user lacks permission
    """
    query = check_permissions(permissions, db_type, "filter", db)

    if query is None:
        return []

    query = query_func(db, query, params)

    if filter is not None and filter != {}:
        from computor_types.filter import apply_filters
        query = query.filter(apply_filters(query, db_type, filter))

    # Wrap the final query execution in threadpool
    def _execute_query():
        paginated_query = query
        if params.limit is not None:
            paginated_query = paginated_query.limit(params.limit)
        if params.skip is not None:
            paginated_query = paginated_query.offset(params.skip)

        return paginated_query.all()

    return await run_in_threadpool(_execute_query)
