"""Pure file content-type guessing and text/binary encoding helpers.

Extracted verbatim from api/examples.py (TASK-214): no FastAPI or DB
dependency, so they live in the service layer and can be unit-tested and
reused by the examples upload/download paths.
"""
import base64
import binascii
import io
import mimetypes
import re
from typing import Optional, Tuple


def _guess_content_type(filename: str, is_binary: bool) -> str:
    """Return a reasonable content-type for a given filename.

    Preference order:
    1) Known multi-part extensions (e.g. .tar.gz/.tgz)
    2) Explicit overrides for common types
    3) Python's mimetypes.guess_type
    4) Fallback to application/octet-stream for binary, text/plain for text
    """
    name = filename.lower()

    # Multi-part extensions first
    if name.endswith('.tar.gz') or name.endswith('.tgz'):
        return 'application/x-tar'

    # Explicit overrides to keep behavior consistent across platforms
    overrides = {
        '.yaml': 'text/yaml',
        '.yml': 'text/yaml',
        '.json': 'application/json',
        '.xml': 'application/xml',
        '.html': 'text/html',
        '.htm': 'text/html',
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.py': 'text/x-python',
        '.java': 'text/x-java',
        '.c': 'text/x-c',
        '.h': 'text/x-c',
        '.cpp': 'text/x-c++',
        '.hpp': 'text/x-c++',
        '.cc': 'text/x-c++',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.pdf': 'application/pdf',
        '.zip': 'application/zip',
        '.tar': 'application/x-tar',
        '.md': 'text/markdown',
        '.txt': 'text/plain',
    }

    for ext, ctype in overrides.items():
        if name.endswith(ext):
            return ctype

    # Fall back to mimetypes
    guessed, _ = mimetypes.guess_type(filename)
    if guessed:
        return guessed

    # Final fallback based on binary/text
    return 'application/octet-stream' if is_binary else 'text/plain'

_BINARY_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip', '.tar', '.tgz', '.tar.gz',
}

def _is_binary_by_extension(filename: str) -> bool:
    name = filename.lower()
    return any(name.endswith(ext) for ext in _BINARY_EXTENSIONS)

def _extract_file_bytes(filename: str, content: object) -> Tuple[io.BytesIO, bool]:
    """Convert provided content to bytes and determine binary/text.

    - bytes -> passthrough (binary)
    - str with data URI -> base64 decode (binary)
    - str and binary-suspect extension -> try base64 decode; else encode as UTF-8 (text)
    - str generic -> attempt safe base64 decode (validate), else encode UTF-8 (text)
    """
    # Raw bytes
    if isinstance(content, (bytes, bytearray)):
        return io.BytesIO(bytes(content)), True

    if not isinstance(content, str):
        # Unknown type: coerce to string and store as text
        data = io.BytesIO(str(content).encode('utf-8'))
        return data, False

    # Strings
    text = content

    # Handle data URI
    if text.startswith('data:'):
        try:
            base64_marker = ';base64,'
            idx = text.find(base64_marker)
            if idx != -1:
                b64 = text[idx + len(base64_marker):]
                return io.BytesIO(base64.b64decode(b64, validate=False)), True
        except (ValueError, binascii.Error):
            pass  # malformed data URI — fall back to other handling

    # Normalize whitespace
    clean = text.replace('\n', '').replace('\r', '').replace(' ', '').replace('\t', '')

    # If extension suggests binary, aggressively try base64 decode first
    if _is_binary_by_extension(filename):
        try:
            return io.BytesIO(base64.b64decode(clean, validate=True)), True
        except Exception:
            # Fall back to raw text bytes; still store something
            return io.BytesIO(text.encode('utf-8')), False

    # For non-binary extensions, attempt a safe base64 decode only if characters match
    base64_pattern = re.compile(r'^[A-Za-z0-9+/]*={0,2}$')
    if len(clean) % 4 == 0 and base64_pattern.match(clean):
        try:
            decoded = base64.b64decode(clean, validate=True)
            return io.BytesIO(decoded), True
        except (ValueError, binascii.Error):
            pass  # not valid base64 — treat as text below

    # Default: treat as UTF-8 text
    return io.BytesIO(text.encode('utf-8')), False

_TEXT_CONTENT_TYPES = {
    'application/json',
    'application/xml',
    'application/javascript',
    'application/x-javascript',
    'text/plain',
    'text/html',
    'text/css',
    'text/csv',
    'text/markdown',
    'text/yaml',
    'text/x-python',
    'text/x-java',
    'text/x-c',
    'text/x-c++',
    'image/svg+xml',
}

def _is_text_content_type(content_type: Optional[str]) -> bool:
    if not content_type:
        return False
    if content_type.startswith('text/'):
        return True
    return content_type in _TEXT_CONTENT_TYPES

def _encode_for_response(filename: str, data: bytes, content_type: Optional[str]) -> str:
    """Return a string payload suitable for ExampleDownloadResponse.files.

    - Text types: UTF-8 decoded string
    - Binary types: Data URI with base64
    """
    if _is_text_content_type(content_type):
        try:
            return data.decode('utf-8')
        except UnicodeDecodeError:
            # Fall back to base64 data URI if decoding fails
            b64 = base64.b64encode(data).decode('ascii')
            ctype = content_type or _guess_content_type(filename, True)
            return f"data:{ctype};base64,{b64}"

    # If content-type unknown, attempt to decode as UTF-8 text
    if not content_type:
        try:
            return data.decode('utf-8')
        except UnicodeDecodeError:
            pass

    # Binary: base64 data URI
    b64 = base64.b64encode(data).decode('ascii')
    ctype = content_type or _guess_content_type(filename, True)
    return f"data:{ctype};base64,{b64}"
