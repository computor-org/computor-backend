"""
Storage configuration and security settings for MinIO integration.
"""
import os
from typing import Set, Dict

# Size limits
MAX_UPLOAD_SIZE = int(os.environ.get('MINIO_MAX_UPLOAD_SIZE', 20 * 1024 * 1024))  # 20MB default
MAX_STORAGE_PER_USER = int(os.environ.get('MAX_STORAGE_PER_USER', 1024 * 1024 * 1024))  # 1GB default
MAX_STORAGE_PER_COURSE = int(os.environ.get('MAX_STORAGE_PER_COURSE', 10 * 1024 * 1024 * 1024))  # 10GB default

# File type restrictions - Whitelist approach
ALLOWED_EXTENSIONS: Set[str] = {
    # Documents
    '.pdf', '.doc', '.docx', '.odt', '.txt', '.md', '.tex', '.rtf',
    # Spreadsheets
    '.xls', '.xlsx', '.csv', '.ods',
    # Presentations
    '.ppt', '.pptx', '.odp',
    # Images
    '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.bmp',
    # Code files
    '.py', '.java', '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.js', '.ts', 
    '.html', '.css', '.jsx', '.tsx', '.vue', '.go', '.rs', '.swift', '.kt',
    '.m', '.mat',  # MATLAB files
    '.r', '.rmd',  # R files
    '.ipynb',  # Jupyter notebooks
    # Data files
    '.json', '.xml', '.yaml', '.yml', '.toml',
    # Archives (carefully allowed for assignments)
    '.zip', '.tar', '.gz', '.7z',
    # Other educational
    '.sql', '.sh', '.bat', '.ps1',  # Scripts (text-based)
}

# MIME type whitelist
ALLOWED_MIME_TYPES: Set[str] = {
    # Documents
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.oasis.opendocument.text',
    'text/plain',
    'text/markdown',
    'text/x-tex',
    'application/rtf',
    # Spreadsheets
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/csv',
    'application/vnd.oasis.opendocument.spreadsheet',
    # Presentations
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.oasis.opendocument.presentation',
    # Images
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/svg+xml',
    'image/webp',
    'image/bmp',
    # Code/Text
    'text/x-python',
    'text/x-java',
    'text/x-c',
    'text/x-c++',
    'text/javascript',
    'application/javascript',
    'text/html',
    'text/css',
    'application/json',
    'application/xml',
    'text/xml',
    'application/x-yaml',
    'text/yaml',
    # Archives
    'application/zip',
    'application/x-zip-compressed',
    'application/x-tar',
    'application/gzip',
    'application/x-7z-compressed',
    # Generic
    'application/octet-stream',  # For binary files where MIME is uncertain
}

# Dangerous file signatures to block
DANGEROUS_SIGNATURES: Dict[bytes, str] = {
    b'MZ': 'Windows executable',
    b'\x7fELF': 'Linux executable',
    b'\xfe\xed\xfa\xce': 'Mach-O executable (32-bit)',
    b'\xfe\xed\xfa\xcf': 'Mach-O executable (64-bit)',
    b'\xce\xfa\xed\xfe': 'Mach-O executable (reverse)',
    b'\xcf\xfa\xed\xfe': 'Mach-O executable (reverse 64-bit)',
    b'\xca\xfe\xba\xbe': 'Java class file',
    b'PK\x03\x04': 'ZIP archive (check further)',  # Could be legitimate
}

# Special handling for archives
ARCHIVE_EXTENSIONS = {'.zip', '.tar', '.gz', '.7z'}

# Rate limiting settings (TODO: Implement with slowapi)
# UPLOAD_RATE_LIMIT = os.environ.get('UPLOAD_RATE_LIMIT', '10/minute')
# DOWNLOAD_RATE_LIMIT = os.environ.get('DOWNLOAD_RATE_LIMIT', '100/minute')

# Storage path patterns
STORAGE_PATH_PATTERNS = {
    'submission': 'courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}/{filename}',
    'course_material': 'courses/{course_id}/materials/{filename}',
    'user_profile': 'users/{user_id}/profile/{filename}',
    'user_files': 'users/{user_id}/files/{filename}',
    'organization': 'organizations/{org_id}/documents/{filename}',
    'temp': 'temp/{session_id}/{filename}',
}

def format_bytes(bytes_size: int) -> str:
    """Format bytes to human readable string"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"