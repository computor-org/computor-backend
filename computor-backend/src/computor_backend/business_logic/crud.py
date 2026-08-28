"""
Business logic for generic CRUD operations.

This module contains core CRUD business logic extracted from api/crud.py,
following the business logic layer pattern. These functions handle database
operations, permission checks, and validation, wrapped in threadpool for
async/await compatibility.
"""

import logging
from functools import lru_cache
from uuid import UUID
from typing import Any, Optional, Callable
from datetime import datetime, timezone
from enum import Enum

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import exc
from sqlalchemy.inspection import inspect
from starlette.concurrency import run_in_threadpool

from computor_backend.exceptions import (
    BadRequestException,
    NotFoundException,
    InternalServerException,
    ForbiddenException
)
from computor_backend.permissions.core import check_permissions
from computor_backend.permissions.handlers import permission_registry
from computor_backend.permissions.principal import Principal
from computor_types.base import EntityInterface, ListQuery
from computor_backend.custom_types import Ltree, LtreeType
from computor_types.tasks import TaskStatus, map_task_status_to_int
from computor_backend.database import set_db_user

logger = logging.getLogger(__name__)


async def create_entity(
    permissions: Principal,
    db: Session,
    entity: BaseModel,
    db_type: Any,
    response_type: BaseModel,
    post_create: Optional[Callable] = None,
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
        raise BadRequestException(detail=clean_msg) from e

    except Exception as e:
        db.rollback()
        logger.exception("Unhandled error in create_entity")
        raise BadRequestException(detail="Failed to create entity") from e


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
            raise NotFoundException(
                detail=f"{db_type.__name__} not found",
                context={"id": str(id), "entity": db_type.__name__},
            )

        return interface.get.model_validate(item, from_attributes=True)

    except HTTPException as e:
        raise e

    except exc.StatementError as e:
        # Malformed input (e.g. bad UUID) — a client error, not a 404.
        raise BadRequestException(detail=e.args) from e

    except Exception:
        # Do NOT mask unexpected errors as 404 — let them surface as 500 so
        # real failures are visible instead of looking like a missing row.
        logger.exception("Unhandled exception in get_entity_by_id")
        raise


@lru_cache(maxsize=None)
def _pagination_tiebreaker(model: Any) -> tuple:
    """Primary key columns, appended to a paginated list's ORDER BY.

    LIMIT/OFFSET over an unordered query is not pagination — SQL guarantees no
    row order without an ORDER BY, so Postgres is free to return the same rows
    in a different order for page 1 and page 2. Most of the list interfaces
    define no ordering at all, which meant paging a roster could show one
    member twice and never show another.

    Appended rather than substituted: it goes after whatever ordering the
    interface already asked for, so it cannot reorder rows that differ on those
    columns — it only decides ties, which the interfaces that order by
    ``position`` or ``path`` also have.
    """
    try:
        return tuple(inspect(model).primary_key)
    except Exception:
        # Not a mapped class (test doubles reach here). Ordering is a
        # correctness improvement we can only make when we know the key.
        return ()


@lru_cache(maxsize=None)
def _list_eager_relationships(model: Any, list_dto: Any) -> tuple[str, ...]:
    """Relationship names a ``list`` DTO reads off its model.

    ``list_entities`` serializes each row with ``model_validate(entity,
    from_attributes=True)``, which touches every field the DTO declares. Where
    a field names a relationship, that read is a lazy load — one round trip per
    row. A roster page of 100 course members issued 100 extra queries for
    ``CourseMember.user`` alone.

    Answering this from the DTO rather than a hand-maintained per-interface
    list means an interface cannot grow a nested field and quietly reintroduce
    the N+1.

    ``selectinload``, not ``joinedload``: this query is about to have LIMIT and
    OFFSET applied, and a joined eager load of a collection makes LIMIT count
    joined rows instead of entities. selectinload issues one extra statement per
    relationship no matter how many rows come back.
    """
    try:
        relationships = {r.key: r for r in inspect(model).relationships}
        names = []
        for field in list_dto.model_fields:
            relationship = relationships.get(field)
            # A dynamic relationship is a query, not a loadable attribute.
            if relationship is not None and relationship.lazy != "dynamic":
                names.append(field)
        return tuple(names)
    except Exception:
        # Not a mapped class, or not a real pydantic model (test doubles reach
        # here). Eager loading is an optimization: if we cannot work out what to
        # load, load nothing and let the lazy path run.
        return ()


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

    eager = _list_eager_relationships(db_type, interface.list)
    tiebreaker = _pagination_tiebreaker(db_type)

    # Wrap blocking pagination queries in threadpool
    def _get_paginated_results():
        # order_by(None) because Query.count() wraps this in a subquery and an
        # ORDER BY inside it makes Postgres sort a result set it only counts.
        total = query.order_by(None).count()

        paginated_query = query
        if eager:
            paginated_query = paginated_query.options(
                *(selectinload(getattr(db_type, name)) for name in eager)
            )
        if tiebreaker:
            paginated_query = paginated_query.order_by(*tiebreaker)
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
    id: UUID | str,
    entity: Any,
    db_type: Any,
    response_type: BaseModel,
    post_update: Optional[Callable] = None,
    custom_permissions: Optional[Callable] = None
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
        custom_permissions: Optional custom permission check that replaces generic check_permissions.
                           Signature: (permissions, db, id, entity) -> Query
                           Should raise ForbiddenException if denied.

    Returns:
        Updated entity as response_type instance

    Raises:
        NotFoundException: If entity not found or user lacks permission
        BadRequestException: If update fails validation
        ForbiddenException: If custom_permissions denies permission
    """
    # Set user context for audit tracking (updated_by)
    set_db_user(db, permissions.user_id)

    # Wrap blocking database operations in threadpool
    def _update_entity():
        # id is always provided; the lookup below binds db_item unconditionally
        # (a former `if id is not None` guard left db_item unbound for id=None,
        # which raised UnboundLocalError further down).
        if custom_permissions is not None:
            query = custom_permissions(permissions, db, id, entity)
        else:
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

        # Special validation for CourseContent type changes. Raised before the
        # try block so it surfaces as itself, not as "Failed to update entity".
        if db_type.__tablename__ == 'course_content':
            if 'course_content_type_id' in entity_dict:
                _validate_course_content_type_change(db_item, entity_dict['course_content_type_id'], db)
            # A path written here would not cascade to the descendants and would
            # orphan every child (computor-org/issues#323). The DTO no longer
            # carries path; this catches internal callers passing plain dicts.
            if 'path' in entity_dict and str(entity_dict['path']) != str(db_item.path):
                raise BadRequestException(
                    detail=(
                        "Course content path cannot be changed here; "
                        "use PATCH /course-contents/{content_id}/move so descendants move along"
                    ),
                    context={"course_content_id": str(db_item.id), "path": str(entity_dict['path'])},
                )

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

        except (ForbiddenException, NotFoundException):
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.exception("Unhandled exception in update_entity")
            raise BadRequestException(detail="Failed to update entity") from e

    db_item, old_db_item = await run_in_threadpool(_update_entity)

    # Execute post-update hook if provided (always async, outside threadpool)
    if post_update is not None:
        await post_update(db_item, old_db_item, db)

    return response_type(**db_item.__dict__)


def _validate_course_content_type_change(db_item, new_type_id, db: Session):
    """
    Validate a PATCH that moves a course content onto another content type.

    Rules (computor-org/issues#320):
    1. The new type must exist in the content's own course.
    2. A change across kinds (assignment ↔ unit) flips ``is_submittable`` via
       the ORM listener and strands everything hanging off the content: a unit
       turned assignment hides its children from every tree, an assignment
       turned unit drops its deployment and submissions from all release and
       grading views while the rows live on. So cross-kind changes are only
       allowed while the content is empty: no descendants, no assigned
       example, no submissions. Same-kind changes stay unrestricted.

    Args:
        db_item: CourseContent entity being updated
        new_type_id: The requested course_content_type_id
        db: Database session

    Raises:
        BadRequestException: If the type does not exist in the course, or the
                             kind would change on a non-empty content
    """
    from computor_backend.model.course import (
        CourseContent,
        CourseContentKind,
        CourseContentType,
        SubmissionGroup,
    )
    from computor_backend.model.deployment import CourseContentDeployment

    if new_type_id is None or str(new_type_id) == str(db_item.course_content_type_id):
        return

    new_type = db.query(CourseContentType).filter(
        CourseContentType.id == str(new_type_id),
        CourseContentType.course_id == str(db_item.course_id),
    ).first()

    if new_type is None:
        raise BadRequestException(
            detail="Content type does not exist in this course",
            context={
                "course_content_id": str(db_item.id),
                "course_content_type_id": str(new_type_id),
            },
        )

    if new_type.course_content_kind_id == db_item.course_content_kind_id:
        return

    new_kind = db.query(CourseContentKind).filter(
        CourseContentKind.id == new_type.course_content_kind_id,
    ).first()

    # Direction-aware: only what the NEW kind cannot carry blocks the change.
    # A content stranded on the wrong kind (the #320 damage) keeps its old
    # cargo — e.g. a unit-kind row still holding a deployed deployment — and
    # moving it back to the kind that cargo belongs to must stay possible.
    blockers = []

    if new_kind is not None and not new_kind.has_descendants:
        has_children = db.query(CourseContent.id).filter(
            CourseContent.course_id == db_item.course_id,
            CourseContent.path.op('<@')(db_item.path),
            CourseContent.id != db_item.id,
        ).first() is not None
        if has_children:
            blockers.append("descendants")

    if new_kind is not None and not new_kind.submittable:
        has_deployment = db.query(CourseContentDeployment.id).filter(
            CourseContentDeployment.course_content_id == db_item.id,
            CourseContentDeployment.deployment_status != 'unassigned',
        ).first() is not None
        if has_deployment:
            blockers.append("example deployment")

        has_submissions = db.query(SubmissionGroup.id).filter(
            SubmissionGroup.course_content_id == db_item.id,
        ).first() is not None
        if has_submissions:
            blockers.append("submissions")

    if blockers:
        raise BadRequestException(
            error_code="CONTENT_008",
            context={
                "course_content_id": str(db_item.id),
                "current_kind": str(db_item.course_content_kind_id),
                "new_kind": str(new_type.course_content_kind_id),
                "blocked_by": blockers,
            },
        )


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

    # Find all descendants (including this course content) within the same course.
    # Ltree path matching: descendant.path <@ parent.path means "descendant is under parent"
    descendants = db.query(CourseContent).filter(
        CourseContent.course_id == entity.course_id,
        CourseContent.path.op('<@')(entity.path)
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
            # Only this course content has submissions
            raise BadRequestException(
                error_code="CONTENT_006",
                context={
                    "course_content_id": str(entity.id),
                    "course_id": str(entity.course_id),
                }
            )
        else:
            # Parent with descendants that have submissions
            raise BadRequestException(
                error_code="CONTENT_007",
                context={
                    "course_content_id": str(entity.id),
                    "course_id": str(entity.course_id),
                    "descendant_count": len(descendant_ids) - 1,
                }
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
        None — the route responds 204 No Content on success

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
            # Handle foreign key constraint violations.
            #
            # Dispatch on the DBAPI exception *class*, not on the message text:
            # str(psycopg2.errors.NotNullViolation) is the SQL message alone, so
            # the old `'NotNullViolation' in error_msg` test never matched and
            # every not-null violation fell through to the generic branch, which
            # echoed the raw SQL (column names included) back to the client —
            # computor-org/issues#387. The message checks stay as a fallback for
            # drivers that wrap the error differently.
            orig = getattr(e, 'orig', None)
            error_msg = str(orig) if orig is not None else str(e)
            violation = type(orig).__name__ if orig is not None else ''
            logger.warning(
                "IntegrityError deleting %s: %s: %s",
                db_type.__tablename__, violation, error_msg,
            )

            if violation == 'NotNullViolation' or 'violates not-null constraint' in error_msg:
                # This happens when deleting would cause NULL in a required foreign key
                if 'course_content_type_id' in error_msg and 'course_content' in error_msg:
                    raise BadRequestException(
                        error_code="CONTENT_010",
                        detail="Cannot delete this course content type because it is still being used by course content items. Please remove or reassign all course content using this type first."
                    ) from e
                else:
                    # Generic not null violation message
                    raise BadRequestException(
                        detail="Cannot delete this item because it would violate data integrity constraints. Other records depend on this item."
                    ) from e
            elif violation == 'ForeignKeyViolation' or 'violates foreign key constraint' in error_msg:
                # Extract table name if possible for better error message
                if 'table' in error_msg:
                    # Try to extract table name from error
                    import re
                    table_match = re.search(r'table "(\w+)"', error_msg)
                    if table_match:
                        table_name = table_match.group(1)
                        raise BadRequestException(
                            detail=f"Cannot delete this {db_type.__tablename__.replace('_', ' ')} because it is referenced by records in {table_name.replace('_', ' ')}. Please remove those references first."
                        ) from e

                # Generic foreign key violation message
                raise BadRequestException(
                    detail=f"Cannot delete this {db_type.__tablename__.replace('_', ' ')} because other records depend on it. Please remove all references to this item first."
                ) from e
            elif violation == 'UniqueViolation' or 'violates unique constraint' in error_msg:
                # This shouldn't happen on delete, but handle it just in case
                raise BadRequestException(detail="A unique constraint violation occurred while deleting") from e
            else:
                # Generic integrity error. The driver's text is logged above, not
                # returned: it names internal columns and tables.
                raise BadRequestException(
                    detail=f"Cannot delete this {db_type.__tablename__.replace('_', ' ')} because other records depend on it."
                ) from e
        except exc.SQLAlchemyError as e:
            db.rollback()
            # Handle other SQLAlchemy errors
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            logger.error("SQLAlchemyError in delete_entity: %s", error_msg)
            raise InternalServerException(detail="An unexpected database error occurred while deleting") from e
        except Exception as e:
            db.rollback()
            logger.exception("Unexpected error in delete_entity")
            raise InternalServerException(detail="An unexpected error occurred while deleting") from e

        return None  # delete/archive/unarchive routes are 204 No Content

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
        None — the route responds 204 No Content on success

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
            raise BadRequestException(detail="Cannot archive this item due to data integrity constraints") from e
        except exc.SQLAlchemyError as e:
            db.rollback()
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            logger.error("SQLAlchemyError in archive_entity: %s", error_msg)
            raise InternalServerException(detail="An unexpected database error occurred while archiving") from e
        except Exception as e:
            db.rollback()
            logger.exception("Unexpected error in archive_entity")
            raise InternalServerException(detail="An unexpected error occurred while archiving") from e

        return None  # delete/archive/unarchive routes are 204 No Content

    return await run_in_threadpool(_archive_entity)


async def unarchive_entity(
    permissions: Principal,
    db: Session,
    id: UUID | str | None,
    db_type: Any,
) -> dict:
    """
    Unarchive an entity by clearing the archived_at timestamp.

    Args:
        permissions: Current user's permission context
        db: Database session
        id: Entity ID to unarchive
        db_type: SQLAlchemy model class

    Returns:
        None — the route responds 204 No Content on success

    Raises:
        NotFoundException: If entity not found or user lacks permission
        BadRequestException: If unarchiving violates constraints
        InternalServerException: If unexpected database error occurs
    """
    def _unarchive_entity():
        query = check_permissions(permissions, db_type, "archive", db)

        try:
            db_item = query.filter(db_type.id == id).first()

            if not db_item:
                raise NotFoundException(detail=f"{db_type.__name__} not found")

            setattr(db_item, "archived_at", None)

            db.commit()
            db.refresh(db_item)
        except NotFoundException:
            raise
        except exc.IntegrityError:
            db.rollback()
            raise BadRequestException(detail="Cannot unarchive this item due to data integrity constraints")
        except exc.SQLAlchemyError as e:
            db.rollback()
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            logger.error("SQLAlchemyError in unarchive_entity: %s", error_msg)
            raise InternalServerException(detail="An unexpected database error occurred while unarchiving") from e
        except Exception as e:
            db.rollback()
            logger.exception("Unexpected error in unarchive_entity")
            raise InternalServerException(detail="An unexpected error occurred while unarchiving") from e

        return None  # delete/archive/unarchive routes are 204 No Content

    return await run_in_threadpool(_unarchive_entity)


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
