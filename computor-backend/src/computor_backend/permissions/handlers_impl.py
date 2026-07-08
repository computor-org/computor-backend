"""Backwards-compatible re-export shim for the permission handlers.

The handlers formerly lived in this single ~1300-line module. TASK-109
split them by domain into ``handlers_user``, ``handlers_course``,
``handlers_scoped`` and ``handlers_misc``, and merged the near-verbatim
``Organization`` / ``CourseFamily`` clones behind
``_ScopedEntityPermissionHandler`` (in ``handlers_scoped``).

This module re-exports every public name from those modules so existing
imports — notably ``permissions/core.py`` and the ``interfaces/*`` /
test call sites that do ``from ...handlers_impl import <Handler>`` /
``make_scope_member_custom_permissions`` — keep working unchanged.

Prefer importing directly from the domain modules in new code.
"""

from computor_backend.permissions.handlers_user import *  # noqa: F401,F403
from computor_backend.permissions.handlers_course import *  # noqa: F401,F403
from computor_backend.permissions.handlers_scoped import *  # noqa: F401,F403
from computor_backend.permissions.handlers_misc import *  # noqa: F401,F403

from computor_backend.permissions.handlers_user import __all__ as _user_all
from computor_backend.permissions.handlers_course import __all__ as _course_all
from computor_backend.permissions.handlers_scoped import __all__ as _scoped_all
from computor_backend.permissions.handlers_misc import __all__ as _misc_all

__all__ = [*_user_all, *_course_all, *_scoped_all, *_misc_all]
