"""
FastAPI exception handlers for structured error responses.

This module provides exception handlers that convert ComputorException instances
into properly formatted ErrorResponse objects.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import traceback
import logging

from computor_backend.exceptions.exceptions import ComputorException, BadRequestException, InternalServerException
from computor_backend.settings import settings


logger = logging.getLogger(__name__)


async def computor_exception_handler(request: Request, exc: ComputorException) -> JSONResponse:
    """
    Handle ComputorException instances.

    Converts exception to structured ErrorResponse and returns as JSON.

    SECURITY NOTE: Debug information (file paths, function names, line numbers)
    is ONLY included when DEBUG_MODE is 'dev', 'development', or 'local'.
    In production, this sensitive information is hidden from API responses.
    """
    # Determine if we should include debug info (only in development/local mode)
    # Can be force-disabled via DISABLE_API_DEBUG_INFO env var for security
    include_debug = (
        settings.DEBUG_MODE.lower() in ['dev', 'development', 'local']
        and not settings.DISABLE_API_DEBUG_INFO
    )

    # Convert to ErrorResponse
    error_response = exc.to_error_response(include_debug=include_debug)

    # Log error for monitoring (includes all details)
    log_error(request, exc, error_response.model_dump())

    # Return minimal response to client (only error_code and message for security)
    # Additional fields like severity, category, documentation_url expose internal details
    response_data = {
        "error_code": error_response.error_code,
        "message": error_response.message,
    }

    # Only include debug info in development mode
    if include_debug and error_response.debug:
        response_data["debug"] = error_response.debug.model_dump(exclude_none=True)

    return JSONResponse(
        status_code=exc.status_code,
        content=response_data,
        headers=exc.headers or {},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Converts validation errors to BadRequestException with structured details.

    SECURITY NOTE: Debug information is only included in development mode.
    """
    # Extract validation errors
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(x) for x in error["loc"][1:])  # Skip 'body' prefix
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"],
        })

    # Create BadRequestException
    exception = BadRequestException(
        error_code="VAL_001",
        detail="Request validation failed",
        context={"validation_errors": errors}
    )

    # Convert to ErrorResponse
    include_debug = (
        settings.DEBUG_MODE.lower() in ['dev', 'development', 'local']
        and not settings.DISABLE_API_DEBUG_INFO
    )
    error_response = exception.to_error_response(include_debug=include_debug)

    # Log validation error
    logger.warning(
        f"Validation error on {request.method} {request.url.path}",
        extra={
            "validation_errors": errors,
            "request_id": getattr(request.state, "request_id", None),
        }
    )

    # Return minimal response (only error_code and message)
    response_data = {
        "error_code": error_response.error_code,
        "message": error_response.message,
    }

    # Include validation errors in details for client to fix
    if errors:
        response_data["details"] = {"validation_errors": errors}

    # Only include debug info in development mode
    if include_debug and error_response.debug:
        response_data["debug"] = error_response.debug.model_dump(exclude_none=True)

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=response_data,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle standard HTTPException from Starlette/FastAPI.

    Converts to appropriate ComputorException type based on status code.
    """
    from computor_backend.exceptions.exceptions import (
        UnauthorizedException,
        ForbiddenException,
        NotFoundException,
        BadRequestException,
        InternalServerException,
        NotImplementedException,
    )

    # Map status codes to exception types
    exception_map = {
        status.HTTP_400_BAD_REQUEST: BadRequestException,
        status.HTTP_401_UNAUTHORIZED: UnauthorizedException,
        status.HTTP_403_FORBIDDEN: ForbiddenException,
        status.HTTP_404_NOT_FOUND: NotFoundException,
        status.HTTP_500_INTERNAL_SERVER_ERROR: InternalServerException,
        status.HTTP_501_NOT_IMPLEMENTED: NotImplementedException,
    }

    exception_class = exception_map.get(exc.status_code, InternalServerException)

    # Create exception instance
    computor_exc = exception_class(
        detail=exc.detail,
        headers=getattr(exc, "headers", None),
    )

    # Use the computor exception handler
    return await computor_exception_handler(request, computor_exc)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions.

    Logs the full traceback and returns a generic internal server error.

    SECURITY NOTE: Exception details and tracebacks are only included in
    development mode. In production, only a generic error is returned.
    """
    # Log the full exception with traceback
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}",
        exc_info=exc,
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "user_id": getattr(request.state, "user_id", None),
        }
    )

    # Create internal server error
    exception = InternalServerException(
        error_code="INT_001",
        detail="An unexpected error occurred",
        context={
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
        }
    )

    # Include traceback in debug mode
    include_debug = (
        settings.DEBUG_MODE.lower() in ['dev', 'development', 'local']
        and not settings.DISABLE_API_DEBUG_INFO
    )
    if include_debug:
        exception.context["traceback"] = traceback.format_exc()

    error_response = exception.to_error_response(include_debug=include_debug)

    # Return minimal response (only error_code and message)
    response_data = {
        "error_code": error_response.error_code,
        "message": error_response.message,
    }

    # Only include debug info in development mode
    if include_debug and error_response.debug:
        response_data["debug"] = error_response.debug.model_dump(exclude_none=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response_data,
    )


def log_error(request: Request, exception: ComputorException, error_response_dict: dict) -> None:
    """
    Log error with structured information.

    Args:
        request: FastAPI request object
        exception: The exception that was raised
        error_response_dict: Serialized error response
    """
    log_data = {
        "error_code": exception.error_code,
        "status_code": exception.status_code,
        "method": request.method,
        "path": request.url.path,
        "request_id": getattr(request.state, "request_id", None),
        "user_id": exception.user_id or getattr(request.state, "user_id", None),
        "function": exception.function_name,
        "context": exception.context,
    }

    # Log with appropriate level based on status code
    if exception.status_code >= 500:
        logger.error(
            f"Server error: {exception.error_code}",
            extra=log_data,
            exc_info=True,
        )
    elif exception.status_code >= 400:
        logger.warning(
            f"Client error: {exception.error_code}",
            extra=log_data,
        )
    else:
        logger.info(
            f"Error: {exception.error_code}",
            extra=log_data,
        )


def register_exception_handlers(app) -> None:
    """
    Register all exception handlers with the FastAPI app.

    Args:
        app: FastAPI application instance
    """
    # ComputorException handler
    app.add_exception_handler(ComputorException, computor_exception_handler)

    # Validation error handler
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # Standard HTTP exception handler
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # Generic exception handler (catch-all)
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Registered custom exception handlers")
