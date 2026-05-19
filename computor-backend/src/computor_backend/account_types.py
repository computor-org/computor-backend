"""
Supported account providers.

Defines which external providers the system can link to a user account.
Currently a static list — replace ACCOUNT_PROVIDERS with a DB query later
without changing the endpoint URL or response shape.
"""

from typing import List
from pydantic import BaseModel


class AccountProvider(BaseModel):
    """A supported external provider that can be linked to a user account."""
    id: str           # short key, e.g. "gitlab"
    display_name: str
    description: str
    provider: str     # value written to account.provider, e.g. "gitlab.com"
    type: str         # value written to account.type, e.g. "gitlab"
    field_label: str  # label for the provider_account_id input
    placeholder: str  # placeholder for the provider_account_id input


ACCOUNT_PROVIDERS: List[AccountProvider] = [
    AccountProvider(
        id="gitlab",
        display_name="GitLab",
        description="GitLab account used for repository access and submission validation",
        provider="gitlab.com",
        type="gitlab",
        field_label="GitLab Username",
        placeholder="johndoe",
    ),
]
