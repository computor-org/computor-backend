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

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        # Pass through non-HTTP requests (WebSocket, lifespan, etc.)
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Only check POST/PUT/PATCH requests (uploads)
        method = scope.get("method", "")
        if method in ("POST", "PUT", "PATCH"):
            # Get Content-Length from headers
            headers = dict(scope.get("headers", []))
            content_length = headers.get(b"content-length")

            if content_length:
                content_length = int(content_length)

                # Check if request exceeds maximum size
                if content_length > self.max_total_size:
                    # Get client info for logging
                    client = scope.get("client", ("unknown", 0))
                    client_host = client[0] if client else "unknown"

                    logger.warning(
                        f"Request rejected: size {format_bytes(content_length)} "
                        f"exceeds limit {format_bytes(self.max_total_size)} "
                        f"from {client_host}"
                    )

                    response = JSONResponse(
                        status_code=413,  # Payload Too Large
                        content={
                            "detail": {
                                "error": f"Request body too large. Maximum allowed size is {format_bytes(self.max_size)} "
                                        f"(received {format_bytes(content_length)})"
                            }
                        }
                    )
                    await response(scope, receive, send)
                    return

        # Process request normally
        await self.app(scope, receive, send)
