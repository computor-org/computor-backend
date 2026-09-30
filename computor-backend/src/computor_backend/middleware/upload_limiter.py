"""
Middleware to limit request body size and add timeouts for upload endpoints.

Uses pure ASGI instead of BaseHTTPMiddleware to properly support WebSocket connections.
"""
import logging
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.responses import JSONResponse
from computor_backend.storage_config import MAX_UPLOAD_SIZE, format_bytes

logger = logging.getLogger(__name__)


class UploadSizeLimiterMiddleware:
    """
    Pure ASGI middleware to enforce maximum request body size.

    This prevents DOS attacks where attackers send extremely large requests
    that consume server resources.

    Note: Uses pure ASGI instead of BaseHTTPMiddleware to properly support
    WebSocket connections (BaseHTTPMiddleware breaks WebSocket upgrades).
    """

    def __init__(self, app: ASGIApp, max_size: int = MAX_UPLOAD_SIZE):
        self.app = app
        self.max_size = max_size
        # Add buffer for form metadata (1MB)
        self.max_total_size = max_size + (1 * 1024 * 1024)

    def _too_large(self, received: int) -> JSONResponse:
        return JSONResponse(
            status_code=413,  # Payload Too Large
            content={
                "detail": {
                    "error": f"Request body too large. Maximum allowed size is {format_bytes(self.max_size)} "
                            f"(received {format_bytes(received)})"
                }
            }
        )

    def _log(self, scope: Scope, size: int) -> None:
        client = scope.get("client") or ("unknown", 0)
        logger.warning(
            f"Request rejected: size {format_bytes(size)} "
            f"exceeds limit {format_bytes(self.max_total_size)} "
            f"from {client[0]}"
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        # Pass through non-HTTP requests (WebSocket, lifespan, etc.)
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Fast path: a declared Content-Length over the limit is refused
        # before any body byte is read.
        content_length = dict(scope.get("headers", [])).get(b"content-length")
        if content_length and content_length.isdigit():
            if int(content_length) > self.max_total_size:
                self._log(scope, int(content_length))
                await self._too_large(int(content_length))(scope, receive, send)
                return

        # The header can be absent (chunked transfer) or wrong, so also count
        # the body bytes actually delivered. Past the limit the 413 is sent
        # right here and the app sees a disconnect, so nothing beyond the limit
        # is read or spooled by multipart parsing — and the status does not
        # depend on how the app wraps errors raised from receive().
        received = 0
        response_started = False
        rejected = False

        async def counting_receive():
            nonlocal received, rejected
            if rejected:
                return {"type": "http.disconnect"}
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_total_size:
                    self._log(scope, received)
                    rejected = True
                    if not response_started:
                        await self._too_large(received)(scope, receive, send)
                    return {"type": "http.disconnect"}
            return message

        async def tracking_send(message):
            nonlocal response_started
            if rejected:
                return  # the 413 already went out
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, counting_receive, tracking_send)
        except Exception:
            if not rejected:
                raise
            # The app gave up on the truncated body (ClientDisconnect etc.).
            logger.debug("request aborted after body limit", exc_info=True)
