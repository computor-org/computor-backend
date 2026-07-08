"""Generic CRUD skeleton for user-owned entities (TASK-206).

``business_logic/profiles.py`` and ``business_logic/student_profiles.py`` were
near-identical copies of a list/get/create/update/delete skeleton with
owner-or-manager permission checks. That skeleton lives here now; the two
business-logic modules stay as thin, explicit wrappers.

The permission decision is delegated to :mod:`business_logic.ownership` and is
BIT-IDENTICAL to the originals:

* ``list`` filters to the caller's own rows unless they hold the manage
  capability;
* ``get``/``update``/``delete`` resolve to ``404`` (:class:`NotFoundException`)
  when the caller is neither owner, manager, nor admin — deliberately hiding
  existence rather than returning 403.

Everything that genuinely differs in *behaviour* between the two entities —
the student-profile 403 manager-gate, the student create owner-resolution,
and DTO mapping — is kept in the respective business-logic module, NOT here.
Object construction is executed *inside* the guarded block (via a ``factory``)
so the create/update error path matches the originals.
"""
import logging
from typing import Any, Callable, List, Tuple

from sqlalchemy.orm import Session

from computor_backend.exceptions import NotFoundException, BadRequestException
from computor_backend.permissions.principal import Principal
from computor_backend.business_logic.ownership import (
    has_manage_permission,
    require_owner_or_role,
)

logger = logging.getLogger(__name__)


def list_owned(
    *,
    db: Session,
    model: Any,
    interface: Any,
    permissions: Principal,
    params: Any,
    resource: str,
    action: str = "list",
) -> Tuple[List[Any], int]:
    """Owner-scoped list — identical to the original ``list_profiles`` skeleton.

    Returns raw ORM rows plus the total count; DTO mapping (if any) is the
    caller's responsibility.
    """
    query = db.query(model)

    # Apply permission filtering
    if not has_manage_permission(permissions, resource, action):
        query = query.filter(model.user_id == permissions.user_id)

    # Apply search filters using the interface search function
    query = interface.search(db, query, params)

    # Get total count
    total = query.count()

    # Apply pagination
    if params.limit:
        query = query.limit(params.limit)
    if params.skip:
        query = query.offset(params.skip)

    return query.all(), total


def get_owned_or_404(
    *,
    db: Session,
    model: Any,
    entity_id: Any,
    permissions: Principal,
    resource: str,
    not_found_detail: str,
    action: str = "list",
) -> Any:
    """Fetch by id or raise 404, then enforce owner-or-manager access.

    Identical to the original get/update/delete access pattern: a missing row
    and an access denial both surface as the same 404, hiding existence.
    """
    obj = db.query(model).filter(model.id == entity_id).first()

    if not obj:
        raise NotFoundException(detail=not_found_detail)

    require_owner_or_role(
        permissions,
        obj.user_id,
        resource,
        action=action,
        exception=NotFoundException,
        detail=not_found_detail,
    )
    return obj


def persist_new(
    *,
    db: Session,
    factory: Callable[[], Any],
    error_detail: str,
    log_context: str,
) -> Any:
    """Build (via ``factory``), add, commit and refresh a new row.

    On any error: rollback and raise :class:`BadRequestException` — identical
    to the original create try/except. ``factory`` runs *inside* the guarded
    block so a construction failure surfaces exactly as it did before.
    """
    try:
        obj = factory()
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj
    except Exception as e:
        db.rollback()
        logger.exception(log_context)
        raise BadRequestException(detail=error_detail) from e


def apply_update(
    *,
    db: Session,
    obj: Any,
    update_data: dict,
    error_detail: str,
    log_context: str,
) -> Any:
    """Apply ``update_data`` onto ``obj`` then commit — identical to the
    original update try/except."""
    try:
        for key, value in update_data.items():
            setattr(obj, key, value)

        db.commit()
        db.refresh(obj)
        return obj
    except Exception as e:
        db.rollback()
        logger.exception(log_context)
        raise BadRequestException(detail=error_detail) from e


def delete_owned(
    *,
    db: Session,
    obj: Any,
    error_detail: str,
    log_context: str,
) -> None:
    """Delete ``obj`` then commit — identical to the original delete
    try/except."""
    try:
        db.delete(obj)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception(log_context)
        raise BadRequestException(detail=error_detail) from e
