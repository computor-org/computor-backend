from typing import Any
from fastapi import HTTPException, status
from typing import Any, Dict, Optional

class NotFoundException(HTTPException):
    def __init__(self,detail: Any = None, headers: Optional[Dict[str, str]] = None):
        self.headers = headers
        self.status_code = status.HTTP_404_NOT_FOUND
        self.detail = detail or "Not found"

class ForbiddenException(HTTPException):
    def __init__(self,detail: Any = None, headers: Optional[Dict[str, str]] = None):
        self.headers = headers
        self.status_code = status.HTTP_403_FORBIDDEN
        self.detail = detail or "Forbidden"

class BadRequestException(HTTPException):
    def __init__(self,detail: Any = None, headers: Optional[Dict[str, str]] = None):
        self.headers = headers
        self.status_code = status.HTTP_400_BAD_REQUEST
        self.detail = detail or "Bad request"

class UnauthorizedException(HTTPException):
    def __init__(self,detail: Any = None, headers: Optional[Dict[str, str]] = None):
        self.headers = headers
        self.status_code = status.HTTP_401_UNAUTHORIZED
        self.detail = detail or "Unauthorized"

class BasicAuthException(HTTPException):
    def __init__(self,detail: Any = None, headers: Optional[Dict[str, str]] = None):
        self.headers = {"WWW-Authenticate": "Basic"}
        self.status_code = status.HTTP_401_UNAUTHORIZED
        self.detail = "Incorrect username or password"

class NotImplementedException(HTTPException):
    def __init__(self,detail: Any = None, headers: Optional[Dict[str, str]] = None):
        self.status_code = status.HTTP_501_NOT_IMPLEMENTED
        self.detail = "Not Implemented"

class InternalServerException(HTTPException):
    def __init__(self,detail: Any = None, headers: Optional[Dict[str, str]] = None):
        self.headers = headers
        self.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        self.detail = detail or "Internal server error"

class ServiceUnavailableException(HTTPException):
    def __init__(self,detail: Any = None, headers: Optional[Dict[str, str]] = None):
        self.headers = headers
        self.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        self.detail = detail or "Service unavailable error"

def response_to_http_exception(status_code: int, details: dict):
    if status_code == status.HTTP_404_NOT_FOUND:
        return NotFoundException(detail=details)
    elif status_code == status.HTTP_403_FORBIDDEN:
        return ForbiddenException(detail=details)
    elif status_code == status.HTTP_400_BAD_REQUEST:
        return BadRequestException(detail=details)
    elif status_code == status.HTTP_403_FORBIDDEN:
        return UnauthorizedException(detail=details)
    elif status_code == status.HTTP_501_NOT_IMPLEMENTED:
        return NotImplementedException(detail=details)
    elif status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
        return InternalServerException(detail=details)
    elif status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
        return ServiceUnavailableException(detail=details)
    else:
        return None