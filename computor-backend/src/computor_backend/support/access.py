"""Who may do what with support tickets (issues#520).

* ``_admin``: everything, including restricted tickets (security@).
* ``_support``: see unrestricted tickets, claim, assign, set status/priority,
  reply by mail, write internal notes.
* ``_support_agent`` (AI): see unrestricted tickets and write internal notes
  only; never send, claim, assign, close or publish.
* everyone else: no access. A Computor user who reported a ticket sees that
  ticket's public messages only (never internal notes, events or the
  published GitHub link) and may add public follow-ups to it. Problem reports
  from web and VS Code (step 2) are such tickets.

Roles are global ``user_role`` rows; both support roles are elevated
(auth/mfa.py) and can only be granted by an administrator
(permissions/roles.py ``grant_requires_admin``).
"""
from typing import Optional

from sqlalchemy.orm import Query, Session

from computor_backend.model.support import Ticket
from computor_backend.permissions.principal import Principal
from computor_backend.permissions.roles import SUPPORT_AGENT_ROLE, SUPPORT_ROLE


def is_support(principal: Principal) -> bool:
    return bool(principal.is_admin or SUPPORT_ROLE in (principal.roles or []))


def is_support_agent(principal: Principal) -> bool:
    return SUPPORT_AGENT_ROLE in (principal.roles or [])


def can_view_team_queue(principal: Principal) -> bool:
    return is_support(principal) or is_support_agent(principal)


def can_manage(principal: Principal) -> bool:
    """Claim, assign, status, priority, reply by mail."""
    return is_support(principal)


def can_write_internal(principal: Principal) -> bool:
    return is_support(principal) or is_support_agent(principal)


def sees_internal(principal: Principal) -> bool:
    return can_view_team_queue(principal)


def visible_tickets(principal: Principal, db: Session) -> Optional[Query]:
    """Tickets this principal may read, or None for no access at all."""
    query = db.query(Ticket)
    if principal.is_admin:
        return query
    if can_view_team_queue(principal):
        return query.filter(Ticket.restricted.is_(False))
    if principal.user_id:
        # Own reports only (public messages; see sees_internal).
        return query.filter(Ticket.reporter_user_id == principal.user_id)
    return None


def assignable(role_ids, restricted: bool) -> bool:
    """May a user with these global roles be assigned a ticket?"""
    roles = set(role_ids or [])
    is_admin = any(r.endswith("_admin") for r in roles)
    if restricted:
        return is_admin
    return is_admin or SUPPORT_ROLE in roles
