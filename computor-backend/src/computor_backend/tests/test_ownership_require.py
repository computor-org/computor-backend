"""Characterization tests for business_logic.ownership.require_owner_or_role.

No DB required. These pin the EXACT allow/deny decision that the profile and
student-profile business logic relied on before the TASK-206 dedup:

    allowed iff  caller is the owner
             OR  caller is admin
             OR  caller holds the general "<resource>:list" claim
                 (the "_user_manager" capability)

A denied caller gets a NotFoundException (404) -- the originals deliberately
raised 404, not 403, on the owner/manager access check so that existence is
not leaked. There is no literal "_user_manager" *role* test anywhere in the
real code: the capability is a general claim, so it is modelled here as one.
"""
import pytest

from computor_backend.exceptions import NotFoundException, ForbiddenException
from computor_backend.permissions.principal import Principal, Claims
from computor_backend.business_logic.ownership import (
    require_owner_or_role,
    is_owner_or_manager,
    has_manage_permission,
)

OWNER = "11111111-1111-1111-1111-111111111111"
OTHER = "22222222-2222-2222-2222-222222222222"
RESOURCE = "profile"


def _owner_principal() -> Principal:
    return Principal(user_id=OWNER)


def _manager_principal() -> Principal:
    # A "_user_manager" is represented by the general claim it grants,
    # "<resource>:list" -- Principal has no literal role check for this.
    return Principal(user_id=OTHER, claims=Claims(general={RESOURCE: {"list"}}))


def _admin_principal() -> Principal:
    # Any role ending in "_admin" flips is_admin on via the model validator.
    return Principal(user_id=OTHER, roles=["_admin"])


def _stranger_principal() -> Principal:
    return Principal(user_id=OTHER)


# --- (a) owner is allowed ---------------------------------------------------
def test_owner_is_allowed():
    # Must not raise.
    require_owner_or_role(_owner_principal(), OWNER, RESOURCE)


# --- (b) _user_manager (holder of the general claim) is allowed -------------
def test_manager_is_allowed():
    require_owner_or_role(_manager_principal(), OWNER, RESOURCE)


# --- (c) admin is allowed ---------------------------------------------------
def test_admin_is_allowed():
    require_owner_or_role(_admin_principal(), OWNER, RESOURCE)


# --- (d) a different, non-privileged user is denied with 404 ----------------
def test_stranger_is_denied_with_notfound():
    with pytest.raises(NotFoundException) as exc:
        require_owner_or_role(
            _stranger_principal(), OWNER, RESOURCE, detail="Profile not found"
        )
    # Same 404 surface the originals raised: status + verbatim detail.
    assert exc.value.status_code == 404
    assert exc.value.detail == "Profile not found"


def test_default_denied_exception_is_notfound():
    # The default (no explicit exception) matches the get/update/delete flows.
    with pytest.raises(NotFoundException):
        require_owner_or_role(_stranger_principal(), OWNER, RESOURCE)


def test_exception_type_is_configurable():
    # Callers may opt into a 403 surface without re-implementing the predicate.
    with pytest.raises(ForbiddenException) as exc:
        require_owner_or_role(
            _stranger_principal(), OWNER, RESOURCE, exception=ForbiddenException
        )
    assert exc.value.status_code == 403


def test_manager_claim_is_resource_scoped():
    # The exact divergence between the two modules: a "student_profile:list"
    # manager must NOT pass the "profile" check...
    sp_manager = Principal(
        user_id=OTHER, claims=Claims(general={"student_profile": {"list"}})
    )
    with pytest.raises(NotFoundException):
        require_owner_or_role(sp_manager, OWNER, "profile")
    # ...but DOES pass for its own resource.
    require_owner_or_role(sp_manager, OWNER, "student_profile")


def test_owner_comparison_is_string_based():
    # Owner match is by str() of the ids (uuid-or-str), matching the originals.
    from uuid import UUID

    p = Principal(user_id=OWNER)
    require_owner_or_role(p, UUID(OWNER), RESOURCE)  # UUID owner vs str user_id


def test_underlying_predicates():
    assert has_manage_permission(_manager_principal(), RESOURCE) is True
    assert has_manage_permission(_admin_principal(), RESOURCE) is True
    assert has_manage_permission(_stranger_principal(), RESOURCE) is False
    assert is_owner_or_manager(_owner_principal(), OWNER, RESOURCE) is True
    assert is_owner_or_manager(_stranger_principal(), OWNER, RESOURCE) is False
