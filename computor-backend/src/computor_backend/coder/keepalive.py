"""Best-effort workspace keepalive driven by Traefik ForwardAuth activity.

In this deployment browsers reach code-server/ttyd directly through Traefik, so
Coder never observes user activity and would stop every workspace at its
template TTL regardless of how actively it is being used (issue #269). The
ForwardAuth hook (``/auth/verify-coder-access``) is called on every proxied
request, so we use it as the activity signal: on each authorized request we push
the workspace's auto-stop deadline forward.

The bump is fire-and-forget and throttled so the ForwardAuth hot path stays
fast and we touch the Coder API at most once per window per workspace.
"""

import asyncio
import logging
import time

from .client import get_coder_client
from .config import get_coder_settings

logger = logging.getLogger(__name__)

# (owner, workspace_name) -> monotonic time of the last bump attempt.
_last_bump: dict[tuple[str, str], float] = {}
# (owner, workspace_name) -> resolved Coder workspace id, cached across bumps so
# the throttled path avoids a lookup call. Evicted when a bump fails.
_workspace_ids: dict[tuple[str, str], str] = {}
# Strong references to in-flight fire-and-forget tasks. The event loop only
# holds weak references, so without this a task may be garbage-collected before
# it finishes. Tasks remove themselves on completion.
_pending: set[asyncio.Task] = set()


def bump_workspace_activity(owner: str, workspace_name: str) -> None:
    """Schedule a throttled, fire-and-forget deadline extension.

    Safe to call on the ForwardAuth hot path: it returns immediately, never
    raises, and hits the Coder API at most once per throttle window per
    workspace regardless of request volume.
    """
    settings = get_coder_settings()
    if not settings.enabled:
        return

    key = (owner, workspace_name)
    now = time.monotonic()
    last = _last_bump.get(key)
    if last is not None and (now - last) < settings.workspace_activity_bump_throttle_s:
        return

    # Record the attempt up front so concurrent requests inside the window don't
    # stampede the Coder API even before the async task runs.
    _last_bump[key] = now

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop (not expected on the async request path) — skip.
        return
    task = loop.create_task(_extend(owner, workspace_name, settings.workspace_activity_bump_ms))
    _pending.add(task)
    task.add_done_callback(_pending.discard)


async def _extend(owner: str, workspace_name: str, extend_ms: int) -> None:
    key = (owner, workspace_name)
    try:
        client = get_coder_client()
        workspace_id = _workspace_ids.get(key)
        if workspace_id is None:
            details = await client.get_workspace(owner, workspace_name)
            workspace_id = details.workspace.id
            _workspace_ids[key] = workspace_id

        extended = await client.extend_workspace_deadline(workspace_id, extend_ms=extend_ms)
        if not extended:
            # A stopped workspace or a stale cached id both land here; drop the
            # id so the next bump re-resolves it against Coder.
            _workspace_ids.pop(key, None)
    except Exception as exc:  # best-effort: never disturb request handling
        _workspace_ids.pop(key, None)
        logger.debug("workspace keepalive skipped for %s/%s: %s", owner, workspace_name, exc)
