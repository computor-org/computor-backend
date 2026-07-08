"""Shared ownership / access-control primitives for user-owned entities.

Extracted (TASK-206) from the duplicated permission logic that lived in
``business_logic/profiles.py`` and ``business_logic/student_profiles.py``.
The decision encoded here is **bit-identical** to the original
``has_profile_permission`` / ``can_access_profile`` pair:

    manager  := is_admin OR has_general_permission(resource, action)
    access   := manager  OR  caller is the entity's owner

A note on the "role" wording used elsewhere (e.g. docstrings that mention
``_user_manager``): there is **no literal role-membership test** in the real
code. The privileged ("manager") capability is a *general claim*
``<resource>:<action>`` (``action`` defaults to ``"list"``), evaluated via
``Principal.has_general_permission`` — which itself already short-circuits
True for admins. The two profile modules differ ONLY in that ``resource``
string: ``"profile"`` vs ``"student_profile"``. That difference is preserved
by passing ``resource`` explicitly; collapsing it into a single hard-coded
role/claim would NOT be bit-identical.
"""
from typing import Type
from uuid import UUID

from computor_backend.exceptions import NotFoundException
from computor_backend.permissions.principal import Principal


def has_manage_permission(
    permissions: Principal,
    resource: str,
    action: str = "list",
) -> bool:
    """Whether the principal may manage ALL entities of ``resource``.

    Bit-identical to the original ``has_profile_permission``:
    ``is_admin or has_general_permission(resource, action)``. The explicit
    ``is_admin`` is redundant (``has_general_permission`` already returns True
    for admins) but is kept verbatim to mirror the originals exactly.
    """
    return permissions.is_admin or permissions.has_general_permission(resource, action)


def is_owner_or_manager(
    permissions: Principal,
    owner_user_id: UUID | str | None,
    resource: str,
    action: str = "list",
) -> bool:
    """Whether the principal may access one specific owned entity.

    Bit-identical to the original ``can_access_profile``: manager
    (see :func:`has_manage_permission`) OR the entity's owner.
    """
    if has_manage_permission(permissions, resource, action):
        return True
    return str(owner_user_id) == str(permissions.user_id)


def require_owner_or_role(
    permissions: Principal,
    owner_user_id: UUID | str | None,
    resource: str,
    *,
    action: str = "list",
    exception: Type[Exception] = NotFoundException,
    detail: str = "Not found",
) -> None:
    """Raise unless the principal is the owner, a manager, or an admin.

    Encodes the exact original access decision used by the profile
    get/update/delete flows: allowed iff :func:`is_owner_or_manager` is True;
    otherwise raise ``exception(detail=detail)``.

    The originals raised :class:`NotFoundException` (a 404, deliberately hiding
    existence) when the owner-or-manager access check failed, so that is the
    default. ``exception`` is a knob only so callers can opt into a different
    surface (e.g. 403) without re-implementing the predicate; the profile
    routers keep the 404 default.

    Args:
        permissions: the caller's :class:`Principal`.
        owner_user_id: the ``user_id`` that owns the entity.
        resource: general-claim resource string (``"profile"`` /
            ``"student_profile"``). NOT normalized across modules on purpose.
        action: general-claim action; the originals used ``"list"``.
        exception: exception class raised on denial (default 404).
        detail: user-facing message forwarded verbatim to the exception.
    """
    if not is_owner_or_manager(permissions, owner_user_id, resource, action):
        raise exception(detail=detail)
