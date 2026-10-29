"""Lena drafts of a unit description (computor-org/issues#559).

A lecturer asks for a draft and polls it; Lena's worker, authenticated as the
configured tutor agent (``TUTOR_AGENT_USER_ID``), claims the job and posts one
draft per language. Nothing here writes to the unit: the lecturer saves the
draft they want through the ordinary course content update.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from computor_backend.business_logic.course_content_description_draft import (
    build_draft_input,
    get_unit_for_draft,
)
from computor_backend.database import get_db
from computor_backend.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
    RateLimitException,
    ServiceUnavailableException,
)
from computor_backend.model.auth import User
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.redis_cache import get_redis_client
from computor_backend.services import description_draft_queue as queue
from computor_backend.services.storage_service import get_storage_service
from computor_backend.settings import settings
from computor_types.course_content_description_drafts import (
    DescriptionDraftAvailability,
    DescriptionDraftClaim,
    DescriptionDraftCompletion,
    DescriptionDraftJob,
    DescriptionDraftRequest,
    DescriptionDraftStatus,
)

router = APIRouter()

_UNAVAILABLE = "Lena cannot write description drafts at the moment"


def _tutor_agent_active(db: Session) -> bool:
    if not settings.TUTOR_AGENT_USER_ID:
        return False
    return (
        db.query(User.id)
        .filter(
            User.id == settings.TUTOR_AGENT_USER_ID,
            User.archived_at.is_(None),
            User.banned_at.is_(None),
        )
        .first()
        is not None
    )


async def _available(db: Session, redis: Redis) -> bool:
    if not _tutor_agent_active(db):
        return False
    try:
        return await queue.worker_alive(redis)
    except RedisError:
        return False


def _require_worker(principal: Principal) -> None:
    if not settings.TUTOR_AGENT_USER_ID or principal.user_id != settings.TUTOR_AGENT_USER_ID:
        raise ForbiddenException(detail="Only Lena's worker can claim description drafts")


# Registered before /description-drafts/{job_id} so "availability" is not
# parsed as a job id.
@router.get(
    "/description-drafts/availability",
    response_model=DescriptionDraftAvailability,
)
async def get_description_draft_availability(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Annotated[Session, Depends(get_db, scope="function")],
    redis: Annotated[Redis, Depends(get_redis_client)],
):
    return DescriptionDraftAvailability(enabled=await _available(db, redis))


@router.post(
    "/{content_id}/description-draft",
    response_model=DescriptionDraftJob,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_description_draft(
    content_id: UUID,
    body: DescriptionDraftRequest,
    principal: Annotated[Principal, Depends(get_current_principal)],
    response: Response,
    db: Annotated[Session, Depends(get_db, scope="function")],
    redis: Annotated[Redis, Depends(get_redis_client)],
    storage_service=Depends(get_storage_service),
):
    if not principal.user_id:
        raise ForbiddenException(detail="A user account is required")
    unit = get_unit_for_draft(str(content_id), principal, db)
    if not await _available(db, redis):
        raise ServiceUnavailableException(detail=_UNAVAILABLE)
    draft_input = await build_draft_input(unit, body, db, storage_service)
    try:
        outcome, job_id = await queue.admit(
            redis,
            principal.user_id,
            {"course_content_id": str(unit.id), "request": draft_input.model_dump()},
        )
    except RedisError:
        raise ServiceUnavailableException(detail=_UNAVAILABLE) from None
    if outcome == "pending":
        raise RateLimitException(detail="Lena is still writing your previous draft")
    if outcome == "full":
        raise RateLimitException(detail="Lena is busy; try again in a few minutes")
    if outcome == "quota":
        raise RateLimitException(detail="You have asked for many drafts recently; try again later")
    if outcome != "accepted":
        raise ServiceUnavailableException(detail=_UNAVAILABLE)
    response.headers["Cache-Control"] = "no-store"
    return DescriptionDraftJob(id=job_id, state="queued")


@router.get(
    "/description-drafts/{job_id}",
    response_model=DescriptionDraftStatus,
)
async def get_description_draft(
    job_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    response: Response,
    redis: Annotated[Redis, Depends(get_redis_client)],
):
    try:
        result = await queue.status(redis, principal.user_id or "", str(job_id))
    except (RedisError, ValueError):
        raise ServiceUnavailableException(detail=_UNAVAILABLE) from None
    if result is None:
        raise NotFoundException(detail="Description draft not found")
    response.headers["Cache-Control"] = "no-store"
    return DescriptionDraftStatus(
        id=str(job_id),
        state=result["state"],
        drafts=result.get("drafts") or None,
        error=result.get("error"),
    )


@router.post(
    "/description-drafts/worker/claim",
    response_model=DescriptionDraftClaim,
)
async def claim_description_draft(
    principal: Annotated[Principal, Depends(get_current_principal)],
    response: Response,
    redis: Annotated[Redis, Depends(get_redis_client)],
):
    _require_worker(principal)
    response.headers["Cache-Control"] = "no-store"
    try:
        item = await queue.claim(redis)
    except (RedisError, ValueError):
        raise ServiceUnavailableException(detail="Description draft queue unavailable") from None
    if item is None:
        return DescriptionDraftClaim(state="idle")
    job_id, lease, payload = item
    return DescriptionDraftClaim(
        state="claimed", id=job_id, lease=lease, request=payload["request"]
    )


@router.post("/description-drafts/worker/complete/{job_id}")
async def complete_description_draft(
    job_id: UUID,
    body: DescriptionDraftCompletion,
    principal: Annotated[Principal, Depends(get_current_principal)],
    response: Response,
    redis: Annotated[Redis, Depends(get_redis_client)],
):
    _require_worker(principal)
    if body.state == "failed":
        if body.drafts:
            raise BadRequestException(detail="A failed draft cannot include drafts")
        result = {"state": "failed", "error": body.error or "model_error"}
    else:
        if body.error or not body.drafts:
            raise BadRequestException(detail="A finished draft needs drafts and no error")
        languages = [draft.language for draft in body.drafts]
        try:
            job = await queue.requested(redis, str(job_id))
        except (RedisError, ValueError):
            raise ServiceUnavailableException(detail="Description draft queue unavailable") from None
        if job is not None and sorted(languages) != sorted(job["request"]["languages"]):
            raise BadRequestException(detail="Drafts must be in exactly the requested languages")
        result = {"state": "done", "drafts": [draft.model_dump() for draft in body.drafts]}
    try:
        outcome = await queue.finish(redis, str(job_id), body.lease, result)
    except RedisError:
        raise ServiceUnavailableException(detail="Description draft queue unavailable") from None
    if outcome != "finished":
        raise ConflictException(detail="Description draft lease is stale or expired")
    response.headers["Cache-Control"] = "no-store"
    return {"state": "finished"}
