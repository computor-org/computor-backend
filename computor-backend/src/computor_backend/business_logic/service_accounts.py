"""Business logic for service account management."""
import logging
from datetime import datetime, timezone
from typing import List
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from computor_backend.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
    ForbiddenException,
)
from computor_backend.permissions.core import check_permissions
from computor_backend.permissions.principal import Principal
from computor_backend.model.service import Service
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
from computor_types.password_utils import create_password_hash

logger = logging.getLogger(__name__)


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
        BadRequestException: If service slug or username already exists
        ForbiddenException: If user lacks admin permissions
    """
    # Check permissions (admin only)
    check_permissions(permissions, Service, "create", db)

    # Check if service slug already exists
    existing_service = db.query(Service).filter(Service.slug == service_data.slug).first()
    if existing_service:
        raise BadRequestException(detail=f"Service with slug '{service_data.slug}' already exists")

    # Generate username from slug if not provided
    username = service_data.username or service_data.slug

    # Check if username already exists
    existing_user = db.query(User).filter(User.username == username).first()

    if existing_user:
        # If user exists and is a service user, link to it
        if not existing_user.is_service:
            raise BadRequestException(detail=f"User with username '{username}' already exists and is not a service account")

        # Check if user is already linked to another service
        existing_service_for_user = db.query(Service).filter(Service.user_id == existing_user.id, Service.archived_at.is_(None)).first()
        if existing_service_for_user:
            raise BadRequestException(detail=f"User '{username}' is already linked to service '{existing_service_for_user.slug}'")

        user = existing_user
        logger.info(f"Linking service to existing user: {username}")
    else:
        # Create new service user
        try:
            # Use explicit given_name/family_name if provided, otherwise derive from service name
            given_name = service_data.given_name
            if given_name is None:
                given_name = service_data.name.split()[0] if service_data.name else service_data.slug

            family_name = service_data.family_name
            if family_name is None:
                family_name = " ".join(service_data.name.split()[1:]) if len(service_data.name.split()) > 1 else ""

            user = User(
                username=username,
                email=service_data.email,
                given_name=given_name,
                family_name=family_name,
                is_service=True,
                password=create_password_hash(service_data.password) if service_data.password else None,
                created_by=permissions.user_id,
                properties={"service_type": service_data.service_type, "auto_created": False},
            )

            db.add(user)
            db.flush()  # Get user ID
            logger.info(f"Created new service user: {username}")
        except Exception as e:
            raise BadRequestException(detail=f"Failed to create user: {str(e)}") from e

    # Look up ServiceType by path to get UUID
    service_type_id = None
    if service_data.service_type:
        from computor_backend.model.service import ServiceType
        from sqlalchemy import cast, Text
        # Cast Ltree to text for comparison to avoid Ltree type processing issues
        service_type = db.query(ServiceType).filter(
            cast(ServiceType.path, Text) == service_data.service_type
        ).first()
        if service_type:
            service_type_id = service_type.id
        else:
            logger.warning(f"ServiceType not found for path: {service_data.service_type}")

    # Create service record
    try:
        service = Service(
            slug=service_data.slug,
            name=service_data.name,
            description=service_data.description,
            service_type_id=service_type_id,
            user_id=user.id,
            config=service_data.config or {},
            enabled=service_data.enabled if service_data.enabled is not None else True,
            created_by=permissions.user_id,
        )

        db.add(service)
        db.commit()
        db.refresh(service)

        logger.info(f"Created service account: {service.slug} (user_id: {user.id})")

        return ServiceGet.model_validate(service, from_attributes=True)

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
    """Get service account by ID."""
    query = check_permissions(permissions, Service, "read", db)

    service = query.filter(Service.id == service_id).first()
    if not service:
        raise NotFoundException(detail="Service not found")

    return ServiceGet.model_validate(service, from_attributes=True)


def list_service_accounts(
    permissions: Principal,
    db: Session,
    query_params: ServiceQuery = None,
) -> List[ServiceGet]:
    """List all service accounts with optional filtering."""
    from computor_backend.interfaces.service import ServiceInterface

    query = check_permissions(permissions, Service, "read", db)
    query = query.filter(Service.archived_at.is_(None))

    # Apply filters if provided
    if query_params:
        query = ServiceInterface.search(db, query, query_params)

    services = query.all()

    return [ServiceGet.model_validate(s, from_attributes=True) for s in services]


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

    service = query.filter(Service.id == service_id).first()
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

        for field, value in update_data.items():
            if hasattr(service, field):
                setattr(service, field, value)

        service.updated_by = permissions.user_id

        db.commit()
        db.refresh(service)

        logger.info(f"Updated service account: {service.slug}")

        return ServiceGet.model_validate(service, from_attributes=True)

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
    # Service can update its own heartbeat
    service = db.query(Service).filter(Service.id == service_id).first()
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
