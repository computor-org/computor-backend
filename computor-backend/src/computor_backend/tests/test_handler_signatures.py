"""
Signature parity across all registered permission handlers.

``business_logic/crud.py::create_entity`` always calls

    handler.can_perform_action(principal, "create", resource_id=None, context=context)

and does so *outside* the try/except, so a handler whose override drops the
``context`` kwarg turns every non-admin create into an HTTP 500 TypeError
instead of a handled authorization decision.

This has now bitten twice (``ReadOnlyPermissionHandler``, then
``ResultPermissionHandler``), so it is checked for every handler at once.
"""

import inspect

import pytest

from computor_backend.permissions.core import initialize_permission_handlers
from computor_backend.permissions.handlers import PermissionHandler, permission_registry
from computor_backend.permissions.principal import Principal


def _registered_handlers():
    initialize_permission_handlers()
    return dict(permission_registry._handlers)


@pytest.mark.unit
class TestHandlerSignatures:
    def test_every_handler_accepts_the_context_kwarg(self):
        offenders = []
        for entity, handler in _registered_handlers().items():
            params = inspect.signature(handler.can_perform_action).parameters
            takes_kwargs = any(
                p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()
            )
            if "context" not in params and not takes_kwargs:
                offenders.append(
                    f"{type(handler).__name__} (registered for {entity.__name__})"
                )

        assert not offenders, (
            "can_perform_action() must accept the `context` kwarg - the create path "
            "always passes it, and a TypeError there surfaces as HTTP 500:\n  "
            + "\n  ".join(offenders)
        )

    def test_every_handler_is_callable_the_way_crud_calls_it(self):
        """Exercise the actual create call signature, not just introspection."""
        principal = Principal(user_id="u1", roles=["user"])
        failures = []
        for entity, handler in _registered_handlers().items():
            try:
                handler.can_perform_action(
                    principal, "create", resource_id=None, context={"course_id": "c1"}
                )
            except TypeError as exc:
                failures.append(f"{type(handler).__name__}: {exc}")

        assert not failures, "handlers rejected the crud.py create call:\n  " + "\n  ".join(failures)

    def test_base_class_declares_context(self):
        params = inspect.signature(PermissionHandler.can_perform_action).parameters
        assert "context" in params
