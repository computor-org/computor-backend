"""No static route may be shadowed by an earlier parametrized sibling.

FastAPI/Starlette match routes in registration order, so registering
``GET /tasks/{task_id}`` before ``GET /tasks/types`` makes the latter dead code:
the request resolves to ``get_task(task_id="types")`` and the caller gets a
bogus lookup error instead of the endpoint.

This walked in three times at once (`/tasks/types`, `/tasks/workers/status`,
`DELETE /sessions/me/all`), so it is checked over the whole app.
"""

import pytest

from computor_backend.server import app


def _matchable_routes():
    """App routes that carry an HTTP method and a compiled path regex."""
    return [
        r for r in app.routes
        if getattr(r, "methods", None) and getattr(r, "path_regex", None) is not None
    ]


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
    """The three regressions: each must win its own path."""
    for route in _matchable_routes():
        if method in route.methods and route.path_regex.match(path):
            assert route.path == path, (
                f"{method} {path} resolves to {route.path} instead of itself"
            )
            return
    pytest.fail(f"no route matches {method} {path}")
