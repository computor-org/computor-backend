"""
Security validation for storage operations.
"""
import os
import re
import logging
from pathlib import Path
from typing import BinaryIO, Optional, Tuple

from .storage_config import (
    MAX_UPLOAD_SIZE,
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    DANGEROUS_SIGNATURES,
    ARCHIVE_EXTENSIONS,
    format_bytes
)
from .api.exceptions import BadRequestException

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and other security issues.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Handle empty or whitespace-only filenames
    if not filename or not filename.strip():
        return "unnamed_file"
    
    # Handle both Windows and Unix path separators
    # Split on both / and \ to get the final component
    filename = filename.replace('\\', '/').split('/')[-1]
    
    # If no filename after path processing, use default
    if not filename:
        return "unnamed_file"
    
    # Prevent hidden files first (before any stripping)
    # Remove leading dots and replace with underscore
    if filename.startswith('.'):
        filename = '_' + filename.lstrip('.')
    
    # Remove dangerous characters but keep unicode support for international names
    # Allow: alphanumeric, spaces, dots, hyphens, underscores
    filename = re.sub(r'[^\w\s.-]', '', filename, flags=re.UNICODE)
    
    # Replace multiple spaces with single underscore
    filename = re.sub(r'\s+', '_', filename)
    
    # Remove leading/trailing dots and spaces (but not the underscore we just added)
    filename = filename.strip('. ')
    
    # Limit filename length
    name_parts = filename.rsplit('.', 1)
    if len(name_parts) == 2:
        name, ext = name_parts
        if len(name) > 100:
            name = name[:100]
        filename = f"{name}.{ext}"
    else:
        if len(filename) > 100:
            filename = filename[:100]
    
    # Ensure filename is not empty or just underscores
    if not filename or filename.strip('_') == '':
        filename = "unnamed_file"
    
    return filename


def validate_file_extension(filename: str) -> Tuple[bool, Optional[str]]:
    """
    Validate file extension against whitelist.
    
    Args:
        filename: Filename to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    ext = os.path.splitext(filename)[1].lower()
    
    if not ext:
        return False, "File must have an extension"
    
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File type '{ext}' is not allowed. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
    
    return True, None


def validate_content_type(content_type: str, filename: str) -> Tuple[bool, Optional[str]]:
    """
    Validate MIME type against whitelist.
    
    Args:
        content_type: MIME type to validate
        filename: Filename for additional context
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Normalize content type (remove parameters like charset)
    content_type = content_type.split(';')[0].strip().lower()
    
    # Special case for archives - allow if extension is valid
    ext = os.path.splitext(filename)[1].lower()
    if ext in ARCHIVE_EXTENSIONS and content_type == 'application/octet-stream':
        return True, None
    
    if content_type not in ALLOWED_MIME_TYPES:
        return False, f"Content type '{content_type}' is not allowed"
    
    return True, None


def validate_file_size(file_size: int) -> Tuple[bool, Optional[str]]:
    """
    Validate file size against maximum limit.
    
    Args:
        file_size: Size of file in bytes
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if file_size > MAX_UPLOAD_SIZE:
        return False, f"File size {format_bytes(file_size)} exceeds maximum allowed size of {format_bytes(MAX_UPLOAD_SIZE)}"
    
    if file_size == 0:
        return False, "Empty files are not allowed"
    
    return True, None


def check_file_content_security(file_data: BinaryIO, filename: str) -> Tuple[bool, Optional[str]]:
    """
    Perform security checks on file content.
    
    Args:
        file_data: File binary data
        filename: Filename for context
        
    Returns:
        Tuple of (is_safe, error_message)
    """
    # Read file header for signature checking
    file_data.seek(0)
    header = file_data.read(256)  # Read more bytes for better detection
    file_data.seek(0)  # Reset position
    
    # Check for dangerous file signatures
    for signature, description in DANGEROUS_SIGNATURES.items():
        if header.startswith(signature):
            # Special handling for ZIP files
            if signature == b'PK\x03\x04':
                ext = os.path.splitext(filename)[1].lower()
                if ext in ARCHIVE_EXTENSIONS:
                    # Allow legitimate archives
                    logger.info(f"Allowing ZIP archive: {filename}")
                    return True, None
                else:
                    # Block disguised executables
                    return False, f"File appears to be a {description} disguised as {ext}"
            else:
                return False, f"File type not allowed: {description}"
    
    # Check for script shebangs (but allow for legitimate script files)
    if header.startswith(b'#!'):
        ext = os.path.splitext(filename)[1].lower()
        if ext not in {'.sh', '.py', '.pl', '.rb', '.ps1', '.bat'}:
            return False, "Executable scripts are not allowed"
    
    # Check for Office files with macros
    ext = os.path.splitext(filename)[1].lower()
    if ext in {'.docm', '.xlsm', '.pptm', '.potm', '.xlam', '.ppsm'}:
        return False, "Office files with macros are not allowed for security reasons"
    
    return True, None


def validate_storage_path(path: str) -> Tuple[bool, Optional[str]]:
    """
    Validate storage path to prevent directory traversal.
    
    Args:
        path: Storage path to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check for path traversal attempts
    if '..' in path or path.startswith('/'):
        return False, "Invalid storage path"
    
    # Check for suspicious patterns
    suspicious_patterns = [
        r'\.\./|/\.\.', # Path traversal
        r'^/', # Absolute paths
        r'\\', # Windows path separators
        r'^\.',  # Hidden files at root
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, path):
            return False, "Storage path contains invalid characters"
    
    return True, None


def perform_full_file_validation(
    filename: str,
    content_type: str,
    file_size: int,
    file_data: BinaryIO
) -> None:
    """
    Perform all file validations. Raises BadRequestException if validation fails.
    
    Args:
        filename: Original filename
        content_type: MIME type
        file_size: File size in bytes
        file_data: File binary data
    """
    # Validate file size
    valid, error = validate_file_size(file_size)
    if not valid:
        raise BadRequestException(error)
    
    # Validate file extension
    valid, error = validate_file_extension(filename)
    if not valid:
        raise BadRequestException(error)
    
    # Validate content type
    valid, error = validate_content_type(content_type, filename)
    if not valid:
        raise BadRequestException(error)
    
    # Check file content security
    valid, error = check_file_content_security(file_data, filename)
    if not valid:
        raise BadRequestException(error)
    
    logger.info(f"File validation passed for: {filename} ({format_bytes(file_size)})")