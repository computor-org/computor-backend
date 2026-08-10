"""Business logic for service account management."""
import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import cast, Text
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from computor_backend.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
    ForbiddenException,
)
from computor_backend.permissions.core import check_permissions
from computor_backend.permissions.principal import Principal
from computor_backend.model.service import Service, ServiceType
from computor_backend.model.auth import User
from computor_backend.model.course import CourseContent
from computor_backend.model.example import ExampleVersion
from computor_types.services import (
    ServiceCreate,
    ServiceGet,
    ServiceList,
    ServiceUpdate,
    ServiceQuery,
)

logger = logging.getLogger(__name__)


def service_to_get(service: Service) -> ServiceGet:
    """Build a ``ServiceGet`` including ``service_type_path``.

    ``ServiceGet.service_type_path`` is a projection of
    ``service.service_type.path``, not a column, so a plain
    ``model_validate(..., from_attributes=True)`` always leaves it ``None`` —
    which is why every list/get response used to hide what kind of service a
    row was. Fill it here so there is exactly one place that knows.
    """
    dto = ServiceGet.model_validate(service, from_attributes=True)
    dto.service_type_path = (
        str(service.service_type.path) if service.service_type else None
    )
    return dto


def build_service_config(
    config: Optional[dict],
    language: Optional[str],
    service_type: ServiceType,
) -> dict:
    """Fold ``language`` into ``Service.config`` and validate it.

    ``config.language`` is what ``TestingBackendFactory`` dispatches on. It
    lives inside ``config`` (rather than as its own column) because that dict
    is already shipped verbatim to the worker via ``service_config_payload``
    and ``GET /service-accounts/me``. Callers may set it either way — as the
    ``language`` field or directly inside ``config`` — and the explicit field
    wins.

    A testing service without a language is unrunnable, so reject it here
    rather than at submission time.
    """
    from computor_backend.testing import TestingBackendFactory

    merged = dict(config or {})
    if language:
        merged["language"] = language

    value = merged.get("language")
    if value is not None:
        known = TestingBackendFactory.get_available_languages()
        if value not in known:
            raise BadRequestException(
                detail=(
                    f"Unsupported testing language '{value}'. "
                    f"Supported languages: {', '.join(known)}"
                ),
                context={"language": value, "supported": known},
            )
    elif service_type.category == "testing":
        raise BadRequestException(
            detail=(
                f"Service type '{service_type.path}' is a testing service, so a "
                f"language is required. Supported languages: "
                f"{', '.join(TestingBackendFactory.get_available_languages())}"
            ),
            context={"service_type": str(service_type.path)},
        )

    return merged


def resolve_service_type(db: Session, path: str) -> ServiceType:
    """Look up a ServiceType by its Ltree path, or raise 400.

    The path is cast to text for comparison to avoid Ltree type processing
    issues. Resolution is strict on purpose: a service whose
    ``service_type_id`` is NULL looks fine until someone submits an
    assignment, which then fails deep in the test pipeline with
    ``SUBMIT_005 "Service type not found for service"``. Failing at creation
    puts the error where the typo is.
    """
    service_type = (
        db.query(ServiceType).filter(cast(ServiceType.path, Text) == path).first()
    )
    if service_type is None:
        known = [
            str(row.path)
            for row in db.query(ServiceType.path).order_by(ServiceType.path).all()
        ]
        raise BadRequestException(
            detail=(
                f"Unknown service type '{path}'. "
                f"Known service types: {', '.join(known) or '(none registered)'}"
            ),
            context={"service_type": path, "known_service_types": known},
        )
    return service_type


def create_service_account(
    service_data: ServiceCreate,
    permissions: Principal,
    db: Session,
) -> ServiceGet:
    """
    Create a new service account with associated user.

    Args:
        service_data: Service creation data
        permissions: Current user permissions
        db: Database session

    Returns:
        Created service account

    Raises:
        BadRequestException: If service slug or service user already exists
        ForbiddenException: If user lacks admin permissions
    """
    # Check permissions (admin only)
    check_permissions(permissions, Service, "create", db)

    # Check if service slug already exists
    existing_service = db.query(Service).filter(Service.slug == service_data.slug).first()
    if existing_service:
        raise BadRequestException(detail=f"Service with slug '{service_data.slug}' already exists")

    # Resolve the ServiceType and validate the config BEFORE touching the user
    # table — a bad path or a testing service with no language must not leave a
    # stray service user behind.
    service_type = resolve_service_type(db, service_data.service_type)
    config = build_service_config(
        service_data.config, service_data.language, service_type
    )

    # Look up existing service user by email (if provided)
    user = None
    if service_data.email:
        existing_user = db.query(User).filter(User.email == service_data.email).first()
        if existing_user:
            if not existing_user.is_service:
                raise BadRequestException(detail=f"User with email '{service_data.email}' exists and is not a service account")
            existing_service_for_user = db.query(Service).filter(
                Service.user_id == existing_user.id, Service.archived_at.is_(None)
            ).first()
            if existing_service_for_user:
                raise BadRequestException(
                    detail=f"User '{service_data.email}' is already linked to service '{existing_service_for_user.slug}'"
                )
            user = existing_user
            logger.info(f"Linking service to existing user: {service_data.email}")

    if user is None:
        # Create new service user
        try:
            given_name = service_data.given_name
            if given_name is None:
                given_name = service_data.name.split()[0] if service_data.name else service_data.slug

            family_name = service_data.family_name
            if family_name is None:
                family_name = " ".join(service_data.name.split()[1:]) if len(service_data.name.split()) > 1 else ""

            user = User(
                email=service_data.email,
                given_name=given_name,
                family_name=family_name,
                is_service=True,
                created_by=permissions.user_id,
                properties={"service_type": service_data.service_type, "auto_created": False},
            )

            db.add(user)
            db.flush()
            logger.info(f"Created new service user: {service_data.email or service_data.slug}")
        except Exception as e:
            raise BadRequestException(detail=f"Failed to create user: {str(e)}") from e

    # Create service record
    try:
        service = Service(
            slug=service_data.slug,
            name=service_data.name,
            description=service_data.description,
            service_type_id=service_type.id,
            user_id=user.id,
            config=config,
            enabled=service_data.enabled if service_data.enabled is not None else True,
            created_by=permissions.user_id,
        )

        db.add(service)
        db.commit()
        db.refresh(service)

        logger.info(f"Created service account: {service.slug} (user_id: {user.id})")

        return service_to_get(service)

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error creating service: {e}")
        raise BadRequestException(detail="Failed to create service - database constraint violated") from e
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating service account: {e}")
        raise


def get_service_account(
    service_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> ServiceGet:
    """Get service account by ID.

    Archived services are excluded, exactly as in ``list_service_accounts``.
    Without this filter a soft-deleted service was invisible in the list yet
    fully readable — and writable — by id.
    """
    query = check_permissions(permissions, Service, "get", db)

    service = query.filter(
        Service.id == service_id,
        Service.archived_at.is_(None),
    ).first()
    if not service:
        raise NotFoundException(detail="Service not found")

    return service_to_get(service)


def list_service_accounts(
    permissions: Principal,
    db: Session,
    query_params: ServiceQuery = None,
) -> List[ServiceGet]:
    """List all service accounts with optional filtering."""
    from computor_backend.interfaces.service import ServiceInterface

    query = check_permissions(permissions, Service, "list", db)
    query = query.filter(Service.archived_at.is_(None))

    # Apply filters if provided
    if query_params:
        query = ServiceInterface.search(db, query, query_params)

    # service_to_get reads service.service_type.path — eager-load it so a list
    # of N services stays one query instead of N+1.
    services = query.options(joinedload(Service.service_type)).all()

    return [service_to_get(s) for s in services]


def _get_service_dependents(db: Session, service_id) -> dict:
    """Return a snapshot of resources that depend on a given service.

    A service is considered "in use" if either:
      - any course_content currently caches it as ``testing_service_id``
        (i.e. the lecturer has assigned an example whose backend is this
        service), or
      - any example_version was uploaded with this service as its
        resolved testing backend.

    We cap the sampled lists at 10 IDs so the 409 response stays small;
    the totals are accurate.
    """
    cc_total = (
        db.query(CourseContent)
        .filter(CourseContent.testing_service_id == service_id)
        .count()
    )
    cc_sample = [
        str(row.id)
        for row in db.query(CourseContent.id)
        .filter(CourseContent.testing_service_id == service_id)
        .limit(10)
        .all()
    ]
    ev_total = (
        db.query(ExampleVersion)
        .filter(ExampleVersion.testing_service_id == service_id)
        .count()
    )
    ev_sample = [
        str(row.id)
        for row in db.query(ExampleVersion.id)
        .filter(ExampleVersion.testing_service_id == service_id)
        .limit(10)
        .all()
    ]
    return {
        "course_content_count": cc_total,
        "course_content_sample": cc_sample,
        "example_version_count": ev_total,
        "example_version_sample": ev_sample,
        "in_use": cc_total > 0 or ev_total > 0,
    }


def update_service_account(
    service_id: UUID | str,
    service_data: ServiceUpdate,
    permissions: Principal,
    db: Session,
    *,
    force: bool = False,
) -> ServiceGet:
    """Update service account details.

    Refuses to disable (``enabled`` from True→False) a service that
    course contents or example versions currently depend on, unless the
    caller explicitly passes ``force=True``. Other field updates pass
    through unchanged.
    """
    query = check_permissions(permissions, Service, "update", db)

    # An archived service is deleted as far as the API is concerned; it must
    # not be silently resurrected (e.g. by PATCHing enabled=true) through a
    # direct id reference that the list endpoint would never have surfaced.
    service = query.filter(
        Service.id == service_id,
        Service.archived_at.is_(None),
    ).first()
    if not service:
        raise NotFoundException(detail="Service not found")

    try:
        update_data = service_data.model_dump(exclude_unset=True)

        # Guard: disabling a service in use breaks every course content
        # and example version that points at it. Surface dependents so
        # the admin can clean them up first (or pass force=true to
        # override after acknowledging the impact).
        will_disable = (
            "enabled" in update_data
            and update_data["enabled"] is False
            and service.enabled is True
        )
        if will_disable and not force:
            dependents = _get_service_dependents(db, service.id)
            if dependents["in_use"]:
                raise ConflictException(
                    error_code="SERVICE_HAS_DEPENDENTS",
                    detail=(
                        f"Cannot disable service '{service.slug}': "
                        f"{dependents['course_content_count']} course "
                        "content(s) and "
                        f"{dependents['example_version_count']} example "
                        "version(s) depend on it. Reassign or unassign "
                        "those before disabling, or retry with "
                        "force=true to override."
                    ),
                    context={
                        "service_id": str(service.id),
                        "service_slug": service.slug,
                        **dependents,
                    },
                )

        # `language` is not a column — it folds into config.language, and the
        # merge has to start from the CURRENT config when only `language` was
        # sent, otherwise setting a language would wipe temporal.task_queue.
        if "language" in update_data or "config" in update_data:
            base = (
                update_data.get("config")
                if "config" in update_data
                else (service.config or {})
            )
            update_data["config"] = build_service_config(
                base, update_data.pop("language", None), service.service_type
            )
        update_data.pop("language", None)

        for field, value in update_data.items():
            if hasattr(service, field):
                setattr(service, field, value)

        service.updated_by = permissions.user_id

        db.commit()
        db.refresh(service)

        logger.info(f"Updated service account: {service.slug}")

        return service_to_get(service)

    except ConflictException:
        # ConflictException is intentional — don't swallow it as a 500.
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating service account: {e}")
        raise


def update_service_heartbeat(
    service_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> None:
    """Update service last_seen_at timestamp (heartbeat)."""
    # Service can update its own heartbeat. Archived services are gone as far
    # as the API is concerned and must not report liveness.
    service = db.query(Service).filter(
        Service.id == service_id,
        Service.archived_at.is_(None),
    ).first()
    if not service:
        raise NotFoundException(detail="Service not found")

    # Check if current user is the service user or has admin permissions
    if permissions.user_id != service.user_id:
        check_permissions(permissions, Service, "update", db)

    try:
        service.last_seen_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating service heartbeat: {e}")
        raise


def delete_service_account(
    service_id: UUID | str,
    permissions: Principal,
    db: Session,
    *,
    force: bool = False,
) -> None:
    """
    Delete (archive) a service account.

    This soft-deletes the service by setting archived_at. The user
    account is not deleted.

    Refuses if any course_content or example_version currently depends
    on the service (would render their assignments untestable). Pass
    ``force=True`` to archive anyway after acknowledging the impact.
    """
    query = check_permissions(permissions, Service, "delete", db)

    service = query.filter(Service.id == service_id).first()
    if not service:
        raise NotFoundException(detail="Service not found")

    if not force:
        dependents = _get_service_dependents(db, service.id)
        if dependents["in_use"]:
            raise ConflictException(
                error_code="SERVICE_HAS_DEPENDENTS",
                detail=(
                    f"Cannot archive service '{service.slug}': "
                    f"{dependents['course_content_count']} course "
                    "content(s) and "
                    f"{dependents['example_version_count']} example "
                    "version(s) depend on it. Reassign or unassign "
                    "those before archiving, or retry with force=true "
                    "to override."
                ),
                context={
                    "service_id": str(service.id),
                    "service_slug": service.slug,
                    **dependents,
                },
            )

    try:
        service.archived_at = datetime.now(timezone.utc)
        service.updated_by = permissions.user_id

        db.commit()

        logger.info(f"Deleted (archived) service account: {service.slug}")

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting service account: {e}")
        raise
