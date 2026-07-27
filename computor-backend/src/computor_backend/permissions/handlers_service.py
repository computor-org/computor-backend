"""Permission handlers for service accounts and API tokens.

Both entities were previously registered with ``UserPermissionHandler``
(``permissions/core.py``), which is written against the ``User`` model: its
``build_query`` dereferences ``self.entity.is_service`` and delegates to
``UserPermissionQueryBuilder.filter_visible_users``. Neither exists on
``Service`` or ``ApiToken``, so every non-admin path either raised
``AttributeError`` (→ 500) or returned a query over the wrong table. It only
ever appeared to work because ``check_admin`` short-circuits first.

These handlers replace it. They live in their own module rather than in
``handlers_misc`` because the token rules are security-critical and need the
reasoning kept next to them.

**Read this before touching ``ApiTokenPermissionHandler``.**
``PrincipalBuilder.build`` (``permissions/auth.py``) appends every token scope
to the principal as a ``("permissions", scope)`` claim. Scopes are purely
*additive* — they grant, they never restrict. Consequences:

* A service user holds no ``UserRole`` rows at all, so its token's scopes are
  its entire authority. That is the intended design.
* A token minted on a *human* account carries that human's full role set no
  matter what scopes are listed on it. Letting a non-admin mint, read, or
  revoke tokens on human accounts is therefore privilege escalation (mint) or
  denial of service (revoke), which is why the claim-holder query below is
  narrowed to service-owned tokens plus the holder's own.
"""

from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from computor_backend.exceptions import ForbiddenException
from computor_backend.permissions.handlers import PermissionHandler
from computor_backend.permissions.principal import Principal

__all__ = [
    "ServicePermissionHandler",
    "ApiTokenPermissionHandler",
]


# ``computor_types.base.ACTIONS`` is {create, get, list, update} — there is no
# "read", so no ``<entity>:read`` claim is ever seeded. Business logic used to
# call ``check_permissions(..., "read", ...)`` anyway, which meant a claim
# holder was silently refused. Those call sites now pass "get"/"list", but map
# "read" defensively so an external caller can't reintroduce the hole.
def _claim_action(action: str) -> str:
    return "get" if action == "read" else action


class ServicePermissionHandler(PermissionHandler):
    """Service accounts.

    Admin, or the ``service:<action>`` claim (held by ``_service_manager``).
    A service account may additionally read its own row — workers hit
    ``GET /service-accounts/me``, which resolves through the same path.

    Raises for anyone else: unlike API tokens, there is no "everyone owns
    some" fallback, so a caller with no claim has no business here and the
    403 is the honest answer.
    """

    def can_perform_action(
        self,
        principal: Principal,
        action: str,
        resource_id: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> bool:
        if self.check_admin(principal):
            return True
        if self.check_general_permission(principal, _claim_action(action)):
            return True
        return bool(principal.is_service) and _claim_action(action) in ("get", "list")

    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        if self.check_admin(principal):
            return db.query(self.entity)

        if self.check_general_permission(principal, _claim_action(action)):
            return db.query(self.entity)

        # A service reading its own record (GET /service-accounts/me).
        if principal.is_service and _claim_action(action) in ("get", "list"):
            return db.query(self.entity).filter(
                self.entity.user_id == principal.user_id
            )

        raise ForbiddenException(
            detail=f"Insufficient permissions to {action} {self.resource_name}"
        )


class ApiTokenPermissionHandler(PermissionHandler):
    """API tokens.

    * **Admin** — every token.
    * **``api_token:<action>`` claim** (``_service_manager``) — tokens owned by
      *service* users, plus the holder's own. Never another human's; see the
      module docstring for why.
    * **Everyone else** — their own tokens only.

    Note the last branch does **not** raise: every authenticated user
    legitimately owns tokens (``/settings`` lists and mints them), so the query
    narrows to self instead of 403-ing.

    That makes a successful ``check_permissions`` call NOT an authorisation
    decision on its own — callers **must** filter through the returned query
    rather than re-fetching the row by id from a repository. ``get_api_token``,
    ``list_api_tokens`` and ``revoke_api_token`` in
    ``business_logic/api_tokens.py`` do exactly that. Creating a token for
    another user cannot be expressed as a query over ``api_token`` at all
    (the constraint is on the *target user*), so it is gated separately by
    ``_assert_may_mint_token_for``.
    """

    def can_perform_action(
        self,
        principal: Principal,
        action: str,
        resource_id: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> bool:
        # Anyone may act on their own tokens; per-row scoping is in build_query.
        return True

    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        from computor_backend.model.auth import User

        if self.check_admin(principal):
            return db.query(self.entity)

        if self.check_general_permission(principal, _claim_action(action)):
            return (
                db.query(self.entity)
                .join(User, User.id == self.entity.user_id)
                .filter(
                    or_(
                        User.is_service.is_(True),
                        self.entity.user_id == principal.user_id,
                    )
                )
            )

        return db.query(self.entity).filter(
            self.entity.user_id == principal.user_id
        )
