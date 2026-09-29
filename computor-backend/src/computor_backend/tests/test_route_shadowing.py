"""No static route may be shadowed by an earlier parametrized sibling.

FastAPI/Starlette match routes in registration order, so registering
``GET /tasks/{task_id}`` before ``GET /tasks/types`` makes the latter dead code:
the request resolves to ``get_task(task_id="types")`` and the caller gets a
bogus lookup error instead of the endpoint.

This walked in three times at once (`/tasks/types`, `/tasks/workers/status`,
`DELETE /sessions/me/all`), so it is checked over the whole app.
"""

import asyncio
from types import SimpleNamespace

import pytest
from starlette.routing import compile_path

from computor_backend.server import app


def _flatten(routes, prefix=""):
    """Yield method-bearing routes in dispatch order with their full path.

    FastAPI >= 0.13x keeps each ``include_router`` as a nested entry of
    ``app.routes`` instead of copying the routes up, so walk into those
    (``original_router`` + ``include_context.prefix``); older versions are flat.
    """
    for r in routes:
        inner = getattr(r, "original_router", None)
        if inner is not None:
            yield from _flatten(inner.routes, prefix + r.include_context.prefix)
        elif getattr(r, "methods", None) and getattr(r, "path", None) is not None:
            path = prefix + r.path
            yield SimpleNamespace(
                methods=set(r.methods), path=path, path_regex=compile_path(path)[0]
            )


def _matchable_routes():
    """App routes that carry an HTTP method and a compiled path regex."""
    return list(_flatten(app.routes))


def _dispatched_route_path(method, path):
    """Send a bare request through the real router; return the chosen route.

    The three paths below are auth-protected, so dispatch stops at the auth
    dependency (the exception is expected) after the router picked the route.
    """
    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": method, "scheme": "http", "path": path,
        "raw_path": path.encode(), "root_path": "", "headers": [],
        "query_string": b"", "server": ("test", 80),
        "client": ("127.0.0.1", 1), "app": app,
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        pass

    try:
        asyncio.run(asyncio.wait_for(app.router(scope, receive, send), 10))
    except Exception:
        pass
    return getattr(scope.get("route"), "path", None)


@pytest.mark.unit
def test_no_static_route_is_shadowed_by_an_earlier_parametrized_route():
    routes = _matchable_routes()
    shadowed = []

    for index, route in enumerate(routes):
        if "{" in route.path:
            continue  # only static routes can be swallowed whole
        for earlier in routes[:index]:
            if "{" not in earlier.path:
                continue
            if not (earlier.methods & route.methods):
                continue
            if earlier.path_regex.match(route.path):
                methods = ",".join(sorted(earlier.methods & route.methods))
                shadowed.append(
                    f"{methods} {route.path} is unreachable - "
                    f"{earlier.path} is registered earlier and matches it"
                )
                break

    assert not shadowed, (
        "static routes shadowed by parametrized ones (register the static path "
        "first):\n  " + "\n  ".join(shadowed)
    )


@pytest.mark.unit
@pytest.mark.parametrize("method,path", [
    ("GET", "/tasks/types"),
    ("GET", "/tasks/workers/status"),
    ("DELETE", "/sessions/me/all"),
])
def test_previously_dead_routes_resolve_to_themselves(method, path):
    """The three regressions: each must win its own path when dispatched."""
    assert _dispatched_route_path(method, path) == path
