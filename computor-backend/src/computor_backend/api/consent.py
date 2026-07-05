"""GDPR consent endpoints.

All endpoints require authentication but are WHITELISTED in the consent-gate
middleware (an unconsented user must be able to read the policy, check their
status, and give/withdraw consent).

The current policy version is always resolved via
business_logic.consent.resolve_current_policy_version — the same Redis-cached
helper the middleware uses — so the version these endpoints report and accept
is exactly the version the gate enforces (no cache-coherence window around
scheduled effective_from boundaries).

Legal note: whether this records consent-as-legal-basis (GDPR Art. 6(1)(a)) or
an informed acknowledgment of processing based on contract/public task depends
on the privacy policy text itself — the mechanism is identical. Strictly
necessary authentication cookies (Keycloak SSO) do not require opt-in and are
presented as information only in the UI.
"""

import ipaddress
import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from computor_backend.business_logic.consent import (
    ConsentService,
    cache_consent_status,
    invalidate_consent_cache,
    resolve_current_policy_version,
)
from computor_backend.database import get_db
from computor_backend.exceptions import ForbiddenException
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.utils.client_info import get_client_ip, get_user_agent
from computor_types.consent import (
    ConsentCreate,
    ConsentStatusGet,
    PolicyTextGet,
    PolicyVersionCreate,
    PolicyVersionGet,
)

logger = logging.getLogger(__name__)

consent_router = APIRouter()


@consent_router.get("/status", response_model=ConsentStatusGet)
async def get_consent_status(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> ConsentStatusGet:
    """Current policy version and whether the caller has consented to it."""
    required_version = await resolve_current_policy_version()
    service = ConsentService(db)
    return ConsentStatusGet(**service.get_status(principal.user_id, required_version))


@consent_router.post("", response_model=ConsentStatusGet, status_code=201)
async def give_consent(
    payload: ConsentCreate,
    request: Request,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> ConsentStatusGet:
    """Record the caller's consent for the current policy version.

    Captures ip/user-agent as proof of consent. Idempotent (partial unique
    index on active consents). Refreshes the middleware's Redis gate cache so
    the user can access the API immediately without re-login.
    """
    required_version = await resolve_current_policy_version()
    service = ConsentService(db)
    consent = service.record_consent(
        user_id=principal.user_id,
        policy_version=payload.policy_version,
        required_version=required_version,
        ip_address=_valid_ip_or_none(get_client_ip(request)),
        user_agent=get_user_agent(request),
        purposes=payload.purposes,
    )
    await cache_consent_status(principal.user_id, consent.policy_version, True)
    logger.info(f"User {principal.user_id} consented to policy version '{consent.policy_version}'")
    return ConsentStatusGet(
        required_version=consent.policy_version,
        has_consented=True,
        granted_at=consent.granted_at,
    )


@consent_router.post("/withdraw", response_model=ConsentStatusGet)
async def withdraw_consent(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> ConsentStatusGet:
    """Withdraw consent (GDPR Art. 7(3)). The caller is gated again afterwards."""
    required_version = await resolve_current_policy_version()
    service = ConsentService(db)
    withdrawn = service.withdraw_consent(principal.user_id)
    if required_version is not None:
        await invalidate_consent_cache(principal.user_id, required_version)
    logger.info(f"User {principal.user_id} withdrew consent ({withdrawn} record(s))")
    return ConsentStatusGet(
        required_version=required_version,
        has_consented=required_version is None,
        granted_at=None,
    )


@consent_router.get("/policy", response_model=PolicyTextGet)
async def get_policy_text(
    principal: Annotated[Principal, Depends(get_current_principal)],
    lang: Optional[str] = Query(None, description="Preferred language code, e.g. 'de'"),
    db: Session = Depends(get_db),
) -> PolicyTextGet:
    """Current policy version + Markdown notice text, with language fallback."""
    required_version = await resolve_current_policy_version()
    service = ConsentService(db)
    return PolicyTextGet(**await service.get_policy_text(required_version, lang))


# ---------------------------------------------------------------------------
# Admin: publish policy versions (append-only)
# ---------------------------------------------------------------------------

@consent_router.get("/policy-versions", response_model=List[PolicyVersionGet])
async def list_policy_versions(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> List[PolicyVersionGet]:
    """List all policy versions (admin)."""
    if not principal.is_admin:
        raise ForbiddenException("Requires _admin role")
    service = ConsentService(db)
    return [_policy_to_get(p) for p in service.policy_versions.list_versions()]


@consent_router.post("/policy-versions", response_model=PolicyVersionGet, status_code=201)
async def publish_policy_version(
    payload: PolicyVersionCreate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> PolicyVersionGet:
    """Publish a new policy version (admin).

    Uploads the Markdown texts to MinIO, inserts the append-only
    policy_versions row, and invalidates the current-version cache. If
    effective_from <= now, every user without consent for the new version is
    re-gated on their next request.
    """
    if not principal.is_admin:
        raise ForbiddenException("Requires _admin role")
    service = ConsentService(db)
    policy = await service.publish_policy_version(
        version=payload.version,
        texts=payload.texts,
        effective_from=payload.effective_from,
    )
    return _policy_to_get(policy)


def _policy_to_get(policy) -> PolicyVersionGet:
    return PolicyVersionGet(
        id=str(policy.id),
        version=policy.version,
        languages=list(policy.languages or []),
        effective_from=policy.effective_from,
        content_hashes=policy.content_hashes,
        created_at=policy.created_at,
    )


def _valid_ip_or_none(value: Optional[str]) -> Optional[str]:
    """get_client_ip returns client-controlled header text (Forwarded/XFF),
    which need not be a valid address ('unknown', obfuscated identifiers).
    The column is INET, so anything unparsable is stored as NULL instead of
    failing the whole consent INSERT."""
    if not value:
        return None
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return None
