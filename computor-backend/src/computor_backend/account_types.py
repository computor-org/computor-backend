"""
Supported account providers.

Defines which external providers the system can link to a user account.
Currently a static list — replace ACCOUNT_PROVIDERS with a DB query later
without changing the endpoint URL or response shape.
"""

from typing import List

# AccountProvider lives in computor_types so the codegen emits its TypeScript type.
# This module keeps the runtime data (ACCOUNT_PROVIDERS) and re-exports the model.
from computor_types.accounts import AccountProvider

__all__ = ["AccountProvider", "ACCOUNT_PROVIDERS"]


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
