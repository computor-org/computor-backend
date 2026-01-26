"""
Storage configuration and security settings for MinIO integration.
"""
import os
from typing import Set, Dict

# Size limits
MAX_UPLOAD_SIZE = int(os.environ.get('MINIO_MAX_UPLOAD_SIZE', 10 * 1024 * 1024))  # 10MB default
MAX_STORAGE_PER_USER = int(os.environ.get('MAX_STORAGE_PER_USER', 1024 * 1024 * 1024))  # 1GB default
MAX_STORAGE_PER_COURSE = int(os.environ.get('MAX_STORAGE_PER_COURSE', 10 * 1024 * 1024 * 1024))  # 10GB default

# File type restrictions - Blacklist approach
# Block dangerous executable and system file extensions
BLOCKED_EXTENSIONS: Set[str] = {
    # Executables
    '.exe', '.dll', '.so', '.dylib', '.bin', '.com', '.scr', '.pif',
    # Scripts that could be dangerous when executed directly
    '.vbs', '.vbe', '.wsf', '.wsh', '.msi', '.msp', '.mst',
    # Office files with macros
    '.docm', '.xlsm', '.pptm', '.potm', '.xlam', '.ppsm', '.sldm',
    # Other potentially dangerous
    '.hta', '.cpl', '.msc', '.jar', '.jnlp',
    '.cmd',  # Windows command scripts
    '.reg',  # Windows registry files
    '.lnk',  # Windows shortcuts
    '.inf',  # Windows setup information
    '.sys', '.drv',  # System/driver files
    # Disk images
    '.iso', '.img', '.dmg', '.vhd', '.vmdk',
}

# MIME types to block
BLOCKED_MIME_TYPES: Set[str] = {
    'application/x-msdownload',
    'application/x-executable',
    'application/x-dosexec',
    'application/x-msdos-program',
    'application/x-msi',
    'application/x-ms-shortcut',
    'application/vnd.ms-excel.sheet.macroEnabled.12',
    'application/vnd.ms-word.document.macroEnabled.12',
    'application/vnd.ms-powerpoint.presentation.macroEnabled.12',
    'application/java-archive',
    'application/x-java-archive',
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

# Special handling for archives and ZIP-based formats
ARCHIVE_EXTENSIONS = {'.zip', '.tar', '.gz', '.7z', '.rar', '.tgz', '.tar.gz'}

# Office Open XML formats (these are ZIP-based but not archives)
# These formats use ZIP container but are documents, not archives
OFFICE_XML_EXTENSIONS = {
    '.xlsx',  # Excel 2007+ spreadsheet
    '.xls',   # Excel 97-2003 (not ZIP but often confused)
    '.docx',  # Word 2007+ document
    '.pptx',  # PowerPoint 2007+ presentation
    '.odt',   # OpenDocument text
    '.ods',   # OpenDocument spreadsheet
    '.odp',   # OpenDocument presentation
}

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
