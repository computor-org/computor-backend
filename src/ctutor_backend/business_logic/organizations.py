"""Business logic for organization management."""
import logging
from uuid import UUID
from gitlab import Gitlab
from sqlalchemy.orm import Session

from ctutor_backend.api.exceptions import BadRequestException, NotImplementedException
from ctutor_backend.permissions.core import check_permissions
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.interface.organizations import OrganizationProperties
from ctutor_backend.interface.tokens import encrypt_api_key
from ctutor_backend.model.organization import Organization

logger = logging.getLogger(__name__)


def update_organization_token(
    organization_id: UUID | str,
    token_type: str,
    token: str,
    permissions: Principal,
    db: Session,
) -> None:
    """Update organization provider token (e.g., GitLab token)."""

    query = check_permissions(permissions, Organization, "update", db)

    try:
        organization = query.filter(Organization.id == organization_id).first()

        if not organization:
            raise BadRequestException(detail="Organization not found")

        if token_type == "gitlab":
            gitlab_url = organization.properties.get("gitlab", {}).get("url")
            if not gitlab_url:
                raise BadRequestException(detail="Organization does not have GitLab configuration")

            # Verify token by attempting to connect
            gitlab = Gitlab(url=gitlab_url, private_token=token)

            # Verify user has owner access to the organization's GitLab group
            full_path = organization.properties.get("gitlab", {}).get("full_path")
            if not full_path:
                raise BadRequestException(detail="Organization GitLab full_path not configured")

            groups = list(filter(
                lambda g: g.full_path == full_path,
                gitlab.groups.list(search=full_path, min_access_level=50)
            ))

            if len(groups) == 0:
                raise BadRequestException(
                    detail="Token does not have owner access to the organization's GitLab group"
                )

            organization_properties = OrganizationProperties(**organization.properties)
            organization_properties.gitlab.token = encrypt_api_key(token)
            organization.properties = organization_properties.model_dump()

            db.commit()
            db.refresh(organization)
        else:
            raise NotImplementedException(detail=f"Token type '{token_type}' is not supported")

    except BadRequestException:
        raise
    except NotImplementedException:
        raise
    except Exception as e:
        logger.error(f"Error updating organization token: {e}")
        raise BadRequestException(detail="Failed to update organization token")
