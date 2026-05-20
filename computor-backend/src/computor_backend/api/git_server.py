import logging
from fastapi import APIRouter, Depends

from computor_backend.exceptions import (
    BadRequestException,
    ComputorException,
    ForbiddenException,
    InternalServerException,
    NotFoundException,
    ServiceUnavailableException,
)
from computor_backend.git_server import (
    get_git_client,
    GitServerError,
    GitServerDisabledError,
    GitServerConnectionError,
    GitServerAuthError,
    GitUserNotFoundError,
    GitUserAlreadyExistsError,
    CreateGitUserRequest,
    UpdateGitUserRequest,
    GitUser,
    GitServerHealthResponse,
)
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/git", tags=["git-server"])


def _require_git_manager(principal: Principal = Depends(get_current_principal)) -> Principal:
    if principal.is_admin:
        return principal
    if not principal.permitted("git_server", "manage"):
        raise ForbiddenException(detail="Git manager permission required.")
    return principal


def _handle_git_error(e: Exception) -> ComputorException:
    if isinstance(e, GitServerDisabledError):
        return ServiceUnavailableException(detail="No git server is configured.")
    if isinstance(e, GitServerConnectionError):
        return ServiceUnavailableException(detail=f"Cannot reach git server: {e}")
    if isinstance(e, GitServerAuthError):
        return InternalServerException(detail="Git server authentication failed — check FORGEJO_ADMIN_TOKEN.")
    if isinstance(e, GitUserNotFoundError):
        return NotFoundException(detail=str(e))
    if isinstance(e, GitUserAlreadyExistsError):
        return BadRequestException(detail=str(e))
    return InternalServerException(detail=f"Git server error: {e}")


@router.get("/health", response_model=GitServerHealthResponse)
async def git_health(_: Principal = Depends(_require_git_manager)):
    try:
        return await get_git_client().health()
    except Exception as e:
        raise _handle_git_error(e) from e


@router.post("/users", response_model=GitUser, status_code=201)
async def create_git_user(
    req: CreateGitUserRequest,
    _: Principal = Depends(_require_git_manager),
):
    try:
        return await get_git_client().create_user(req)
    except Exception as e:
        raise _handle_git_error(e) from e


@router.get("/users/{username}", response_model=GitUser)
async def get_git_user(
    username: str,
    _: Principal = Depends(_require_git_manager),
):
    try:
        return await get_git_client().get_user(username)
    except Exception as e:
        raise _handle_git_error(e) from e


@router.patch("/users/{username}", response_model=GitUser)
async def update_git_user(
    username: str,
    req: UpdateGitUserRequest,
    _: Principal = Depends(_require_git_manager),
):
    try:
        return await get_git_client().update_user(username, req)
    except Exception as e:
        raise _handle_git_error(e) from e


@router.delete("/users/{username}", status_code=204)
async def delete_git_user(
    username: str,
    _: Principal = Depends(_require_git_manager),
):
    try:
        await get_git_client().delete_user(username)
    except Exception as e:
        raise _handle_git_error(e) from e


@router.post("/users/{username}/suspend", status_code=204)
async def suspend_git_user(
    username: str,
    _: Principal = Depends(_require_git_manager),
):
    try:
        await get_git_client().suspend_user(username)
    except Exception as e:
        raise _handle_git_error(e) from e


@router.post("/users/{username}/activate", status_code=204)
async def activate_git_user(
    username: str,
    _: Principal = Depends(_require_git_manager),
):
    try:
        await get_git_client().activate_user(username)
    except Exception as e:
        raise _handle_git_error(e) from e
