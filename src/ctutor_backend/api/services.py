from typing import Annotated
from fastapi import APIRouter, Depends, Request, Response
import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session
import starlette
from ctutor_backend.permissions.auth import get_current_principal
from ctutor_backend.api.exceptions import NotFoundException, ServiceUnavailableException
from ctutor_backend.database import get_db
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.model.course import CourseMember

SERVICES = {
}

services_router = APIRouter()

@services_router.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def service_proxy(permissions: Annotated[Principal, Depends(get_current_principal)], service: str, path: str, request: Request, db: Session = Depends(get_db)):

    target_roles = ["_maintainer", "_owner", "_tutor"]
    result = db.query(func.count(CourseMember.course_role_id)) \
        .filter(CourseMember.user_id == permissions.user_id, CourseMember.course_role_id.in_(target_roles)) \
        .scalar()

    if result < 1:
        raise NotFoundException()

    service_name = SERVICES.get(service,None)

    if service_name == None:
        raise NotFoundException()

    target_url = f"{service_name}/{path}"
    method = request.method.lower()
    data = await request.body()

    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(method, target_url, content=data)

        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get("content-type")
        )

    except httpx.ConnectError:
        raise ServiceUnavailableException()
    
    except starlette.requests.ClientDisconnect:
        raise ServiceUnavailableException()
