"""Narrow public Luna ingress and outbound worker API.

The worker credential has no Principal and cannot reach tutor, grading,
reference, submission or general message APIs. The browser submits only the
selected text it wants Luna to see; the backend adds visible assignment text.
"""

import hmac
import os
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from computor_backend.business_logic.content_visibility import is_student_visible
from computor_backend.database import get_db
from computor_backend.model.course import Course, CourseContent, CourseMember
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.redis_cache import get_redis_client
from computor_backend.services import public_luna_queue as queue

router = APIRouter()


def _enabled() -> bool:
    return (
        os.environ.get("PUBLIC_LUNA_ENABLED", "").lower() in {"1", "true"}
        and len(os.environ.get("PUBLIC_LUNA_WORKER_KEY", "")) >= 32
    )


class LunaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    course_content_id: UUID
    question: str = Field(min_length=1, max_length=6000)
    submitted_text: str = Field(default="", max_length=16000)


class LunaCompletion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lease: str = Field(pattern=r"^[0-9]{1,20}$")
    state: Literal["done", "failed"]
    answer: str = Field(default="", max_length=8192)


def _worker_key(value: str | None) -> None:
    expected = os.environ.get("PUBLIC_LUNA_WORKER_KEY", "")
    if len(expected) < 32 or not value or not hmac.compare_digest(value, expected):
        raise HTTPException(status_code=401, detail="Worker authentication required")


@router.get("/availability")
async def availability():
    return {"enabled": _enabled()}


def _visible_assignment(db: Session, user_id: str, content_id: UUID) -> CourseContent:
    row = (
        db.query(CourseContent, Course)
        .join(Course, Course.id == CourseContent.course_id)
        .join(CourseMember, CourseMember.course_id == Course.id)
        .filter(
            CourseContent.id == str(content_id),
            CourseMember.user_id == user_id,
            CourseMember.course_role_id == "_student",
            Course.public.is_(True),
            Course.archived_at.is_(None),
            CourseContent.archived_at.is_(None),
        )
        .first()
    )
    if not row or not is_student_visible(db, row[0], row[1]):
        raise HTTPException(status_code=404, detail="Assignment unavailable")
    return row[0]


def _assignment_text(content: CourseContent) -> str:
    deployed = content.deployment.example_version if content.deployment else None
    description = content.description or (deployed.description if deployed else "")
    text = f"{content.title or ''}\n{description or ''}".strip()
    return text if len(text) <= 5000 else text[:4987] + "\n[truncated]"


@router.post("/requests", status_code=status.HTTP_202_ACCEPTED)
async def submit_request(
    body: LunaRequest,
    principal: Annotated[Principal, Depends(get_current_principal)],
    response: Response,
    db: Annotated[Session, Depends(get_db, scope="function")],
    redis: Annotated[Redis, Depends(get_redis_client)],
):
    if principal.is_service or not principal.user_id:
        raise HTTPException(status_code=403, detail="Learner account required")
    if not _enabled():
        raise HTTPException(status_code=503, detail="Luna is unavailable")
    content = _visible_assignment(db, principal.user_id, body.course_content_id)
    assignment = _assignment_text(content)
    if len(body.question) + len(body.submitted_text) + len(assignment) > 24000:
        raise HTTPException(status_code=413, detail="Luna request is too large")
    try:
        outcome, job_id = await queue.admit(
            redis,
            principal.user_id,
            {
                "course_content_id": str(body.course_content_id),
                "assignment": assignment,
                "question": body.question,
                "submitted_text": body.submitted_text,
            },
        )
    except RedisError:
        raise HTTPException(
            status_code=503, detail="Luna admission unavailable"
        ) from None
    if outcome != "accepted":
        code = 429 if outcome in {"pending", "full", "quota"} else 503
        raise HTTPException(
            status_code=code,
            detail={
                "pending": "A Luna request is already pending",
                "full": "Luna is busy; try again later",
                "quota": "Luna request limit reached",
            }.get(outcome, "Luna admission unavailable"),
        )
    response.headers["Cache-Control"] = "no-store"
    return {"id": job_id, "state": "queued"}


@router.get("/requests/{job_id}")
async def request_status(
    job_id: UUID,
    principal: Annotated[Principal, Depends(get_current_principal)],
    response: Response,
    redis: Annotated[Redis, Depends(get_redis_client)],
):
    if not principal.user_id or principal.is_service:
        raise HTTPException(status_code=404, detail="Luna request unavailable")
    try:
        result = await queue.status(redis, principal.user_id, str(job_id))
    except (RedisError, ValueError):
        raise HTTPException(status_code=503, detail="Luna status unavailable") from None
    if result is None:
        raise HTTPException(status_code=404, detail="Luna request unavailable")
    response.headers["Cache-Control"] = "no-store"
    return {key: value for key, value in result.items() if key != "user_id"}


@router.post("/worker/claim")
async def claim_request(
    response: Response,
    redis: Annotated[Redis, Depends(get_redis_client)],
    worker_key: Annotated[str | None, Header(alias="X-Public-Luna-Worker-Key")] = None,
):
    _worker_key(worker_key)
    response.headers["Cache-Control"] = "no-store"
    if not _enabled():
        return {"state": "idle"}
    try:
        item = await queue.claim(redis)
    except (RedisError, ValueError):
        raise HTTPException(status_code=503, detail="Luna queue unavailable") from None
    if item is None:
        return {"state": "idle"}
    job_id, lease, payload = item
    payload.pop("user_id", None)
    return {"state": "claimed", "id": job_id, "lease": lease, "request": payload}


@router.post("/worker/complete/{job_id}")
async def complete_request(
    job_id: UUID,
    body: LunaCompletion,
    response: Response,
    redis: Annotated[Redis, Depends(get_redis_client)],
    worker_key: Annotated[str | None, Header(alias="X-Public-Luna-Worker-Key")] = None,
):
    _worker_key(worker_key)
    if body.state == "failed" and body.answer:
        raise HTTPException(
            status_code=400, detail="Failed requests cannot include output"
        )
    if body.state == "done" and not body.answer:
        raise HTTPException(status_code=400, detail="An answer is required")
    try:
        outcome = await queue.finish(
            redis,
            str(job_id),
            body.lease,
            {
                "state": body.state,
                "answer": body.answer,
            },
        )
    except RedisError:
        raise HTTPException(
            status_code=503, detail="Luna completion unavailable"
        ) from None
    if outcome != "finished":
        raise HTTPException(status_code=409, detail="Luna lease is stale or expired")
    response.headers["Cache-Control"] = "no-store"
    return {"state": "finished"}
