"""Keep learner text out of framework validation and uncaught-error logs."""
import logging

from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


def is_public_luna_scope(scope: dict) -> bool:
    path = scope.get("path", "")
    root = scope.get("root_path", "")
    if root and path.startswith(root + "/"):
        path = path[len(root):]
    return path == "/public-luna" or path.startswith("/public-luna/")


class PublicLunaPrivacyMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or not is_public_luna_scope(scope):
            await self.app(scope, receive, send)
            return
        started = finished = False

        async def guarded_send(message):
            nonlocal started, finished
            if message["type"] == "http.response.start":
                started = True
            elif message["type"] == "http.response.body" and not message.get("more_body", False):
                finished = True
            await send(message)

        try:
            await self.app(scope, receive, guarded_send)
        except Exception as exc:  # noqa: BLE001 - this is the final privacy boundary
            # ServerErrorMiddleware re-raises uncaught exceptions for the ASGI
            # server to log. Contain them here, without their text or traceback.
            logger.error("Public Luna request failed", extra={
                "status_code": 500, "exception_type": type(exc).__name__,
            })
            if not started:
                await JSONResponse({"message": "Luna is temporarily unavailable"},
                                   status_code=500)(scope, receive, send)
            elif not finished:
                await send({"type": "http.response.body", "body": b"", "more_body": False})
