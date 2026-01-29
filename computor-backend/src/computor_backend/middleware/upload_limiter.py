"""
Middleware to limit request body size and add timeouts for upload endpoints.
"""
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from computor_backend.storage_config import MAX_UPLOAD_SIZE, format_bytes

logger = logging.getLogger(__name__)


class UploadSizeLimiterMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce maximum request body size.

    This prevents DOS attacks where attackers send extremely large requests
    that consume server resources.
    """

    def __init__(self, app, max_size: int = MAX_UPLOAD_SIZE):
        super().__init__(app)
        self.max_size = max_size
        # Add buffer for form metadata (1MB)
        self.max_total_size = max_size + (1 * 1024 * 1024)

    async def dispatch(self, request: Request, call_next):
        """Check Content-Length header before processing request."""

        # Only check POST/PUT/PATCH requests (uploads)
        if request.method in ("POST", "PUT", "PATCH"):
            content_length = request.headers.get("content-length")

            if content_length:
                content_length = int(content_length)

                # Check if request exceeds maximum size
                if content_length > self.max_total_size:
                    logger.warning(
                        f"Request rejected: size {format_bytes(content_length)} "
                        f"exceeds limit {format_bytes(self.max_total_size)} "
                        f"from {request.client.host}"
                    )
                    return JSONResponse(
                        status_code=413,  # Payload Too Large
                        content={
                            "detail": {
                                "error": f"Request body too large. Maximum allowed size is {format_bytes(self.max_size)} "
                                        f"(received {format_bytes(content_length)})"
                            }
                        }
                    )

        # Process request normally
        response = await call_next(request)
        return response
