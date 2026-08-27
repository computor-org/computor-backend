"""Cookie names shared by auth dependencies and ASGI middleware.

Production keeps the historical names. A preview may set
``AUTH_COOKIE_PREFIX`` so its cookies cannot collide with a production session
on the shared ``code.tugraz.at`` host, even when both cookies are sent for a
path-routed request.
"""

from __future__ import annotations

import os
import re


_prefix = os.environ.get("AUTH_COOKIE_PREFIX", "").strip()
if not re.fullmatch(r"[A-Za-z0-9_-]*", _prefix):
    _prefix = ""

ACCESS_COOKIE_NAME = f"{_prefix}ct_access_token"
REFRESH_COOKIE_NAME = f"{_prefix}ct_refresh_token"

