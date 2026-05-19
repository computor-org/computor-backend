"""
Account-specific endpoints that extend the generic CrudRouter for /accounts.

GET /accounts/providers  — list supported provider definitions (public).
"""

from typing import List
from fastapi import APIRouter
from computor_backend.account_types import AccountProvider, ACCOUNT_PROVIDERS

accounts_router = APIRouter()


@accounts_router.get("/accounts/providers", response_model=List[AccountProvider])
async def list_account_providers() -> List[AccountProvider]:
    """
    Return the list of supported account providers.

    Public — no authentication required. The frontend uses this to render
    the correct form when linking a provider account to a user.
    """
    return ACCOUNT_PROVIDERS
