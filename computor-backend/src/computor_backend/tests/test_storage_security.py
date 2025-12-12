import pytest
import io
from unittest.mock import Mock, patch

from computor_backend.storage_security import (
    sanitize_filename,
    validate_file_extension,
    validate_content_type,
    validate_file_size,
    check_file_content_security,
    validate_storage_path,
    perform_full_file_validation
)
from computor_backend.storage_config import MAX_UPLOAD_SIZE
from computor_backend.api.exceptions import BadRequestException


class TestFilenameSanitization:
    """Test filename sanitization"""

    def test_normal_filename(self):
        assert sanitize_filename("document.pdf") == "document.pdf"
        assert sanitize_filename("my_file_123.txt") == "my_file_123.txt"

    def test_path_traversal_prevention(self):
        # Path() automatically handles path traversal by taking just the filename
        assert sanitize_filename("../../../etc/passwd") == "passwd"
        assert sanitize_filename("/etc/passwd") == "passwd"
        # For Windows paths, Path().name gives us just the final component
        assert sanitize_filename("..\\..\\windows\\system32\\config") == "config"

    def test_special_characters_removal(self):
        assert sanitize_filename("file<>:|?*.txt") == "file.txt"
        assert sanitize_filename("my@file#2024!.pdf") == "myfile2024.pdf"

    def test_space_handling(self):
        assert sanitize_filename("my file name.doc") == "my_file_name.doc"
        assert sanitize_filename("file   with   spaces.txt") == "file_with_spaces.txt"

    def test_hidden_file_prevention(self):
        assert sanitize_filename(".hidden_file.txt") == "_hidden_file.txt"
        assert sanitize_filename("..double_dot.pdf") == "_double_dot.pdf"

    def test_long_filename_truncation(self):
        long_name = "a" * 150 + ".txt"
        result = sanitize_filename(long_name)
        assert len(result) <= 104  # 100 chars + .txt
        assert result.endswith(".txt")

    def test_unicode_support(self):
        assert sanitize_filename("文档.pdf") == "文档.pdf"
        assert sanitize_filename("файл.txt") == "файл.txt"

    def test_empty_filename(self):
        assert sanitize_filename("") == "unnamed_file"
        assert sanitize_filename("   ") == "unnamed_file"


class TestFileValidation:
    """Test file validation functions (blacklist approach)"""

    def test_allowed_extensions(self):
        """Test that common educational file types are allowed"""
        allowed_files = [
            "document.pdf", "code.py", "image.jpg", "data.csv",
            "archive.zip", "notebook.ipynb", "script.sh",
            "data.dat", "config.conf", "readme.rst", "makefile.mk",
            "model.h5", "weights.pkl", "data.npy", "matrix.npz"
        ]
        for filename in allowed_files:
            valid, error = validate_file_extension(filename)
            assert valid is True, f"File {filename} should be allowed"
            assert error is None

    def test_blocked_extensions(self):
        """Test that dangerous executable extensions are blocked"""
        blocked_files = [
            "program.exe", "app.dmg", "installer.msi", "library.dll",
            "script.vbs", "macro.docm", "virus.scr", "malware.com"
        ]
        for filename in blocked_files:
            valid, error = validate_file_extension(filename)
            assert valid is False, f"File {filename} should be blocked"
            assert "not allowed" in error

    def test_no_extension_allowed(self):
        """Files without extensions should be allowed (common for data files, Makefile, etc.)"""
        valid, error = validate_file_extension("Makefile")
        assert valid is True
        assert error is None

    def test_allowed_content_types(self):
        """Test that common MIME types are allowed"""
        allowed_types = [
            ("application/pdf", "doc.pdf"),
            ("text/plain", "file.txt"),
            ("image/jpeg", "photo.jpg"),
            ("application/zip", "archive.zip"),
            ("application/octet-stream", "data.bin"),  # Generic binary allowed
        ]
        for content_type, filename in allowed_types:
            valid, error = validate_content_type(content_type, filename)
            assert valid is True, f"Content type {content_type} should be allowed"
            assert error is None

    def test_blocked_content_types(self):
        """Test that dangerous MIME types are blocked"""
        blocked_types = [
            ("application/x-executable", "program"),
            ("application/x-msdownload", "installer.exe"),
            ("application/x-msi", "setup.msi"),
        ]
        for content_type, filename in blocked_types:
            valid, error = validate_content_type(content_type, filename)
            assert valid is False, f"Content type {content_type} should be blocked"
            assert "not allowed" in error

    def test_file_size_validation(self):
        # Valid sizes
        valid, error = validate_file_size(1024)  # 1KB
        assert valid is True

        valid, error = validate_file_size(MAX_UPLOAD_SIZE)  # Exactly at limit
        assert valid is True

        # Invalid sizes
        valid, error = validate_file_size(MAX_UPLOAD_SIZE + 1)
        assert valid is False
        assert "exceeds maximum" in error

        valid, error = validate_file_size(0)
        assert valid is False
        assert "Empty files" in error


class TestContentSecurity:
    """Test file content security checks"""

    def test_safe_text_file(self):
        content = b"This is a safe text file content"
        file_data = io.BytesIO(content)
        valid, error = check_file_content_security(file_data, "document.txt")
        assert valid is True
        assert error is None

    def test_windows_executable_detection(self):
        content = b"MZ\x90\x00\x03\x00\x00\x00"  # PE header
        file_data = io.BytesIO(content)
        valid, error = check_file_content_security(file_data, "program.txt")
        assert valid is False
        assert "Windows executable" in error

    def test_linux_executable_detection(self):
        content = b"\x7fELF\x02\x01\x01\x00"  # ELF header
        file_data = io.BytesIO(content)
        valid, error = check_file_content_security(file_data, "program")
        assert valid is False
        assert "Linux executable" in error

    def test_legitimate_zip_allowed(self):
        content = b"PK\x03\x04\x14\x00\x00\x00"  # ZIP header
        file_data = io.BytesIO(content)
        valid, error = check_file_content_security(file_data, "archive.zip")
        assert valid is True
        assert error is None

    def test_disguised_zip_blocked(self):
        content = b"PK\x03\x04\x14\x00\x00\x00"  # ZIP header
        file_data = io.BytesIO(content)
        valid, error = check_file_content_security(file_data, "document.pdf")
        assert valid is False
        assert "disguised" in error

    def test_script_with_shebang(self):
        # Allowed for legitimate script files
        content = b"#!/usr/bin/python3\nprint('hello')"
        file_data = io.BytesIO(content)
        valid, error = check_file_content_security(file_data, "script.py")
        assert valid is True

        # Blocked for non-script files with extension
        file_data.seek(0)
        valid, error = check_file_content_security(file_data, "document.txt")
        assert valid is False
        assert "Executable scripts" in error

    def test_shebang_allowed_for_files_without_extension(self):
        """Files without extension should allow shebangs (common for scripts)"""
        content = b"#!/bin/bash\necho hello"
        file_data = io.BytesIO(content)
        valid, error = check_file_content_security(file_data, "myscript")
        assert valid is True
        assert error is None


class TestStoragePathValidation:
    """Test storage path validation"""

    def test_valid_paths(self):
        valid_paths = [
            "uploads/user123/file.pdf",
            "courses/cs101/materials/lecture.ppt",
            "temp/session123/data.csv"
        ]
        for path in valid_paths:
            valid, error = validate_storage_path(path)
            assert valid is True
            assert error is None

    def test_path_traversal_attempts(self):
        invalid_paths = [
            "../../../etc/passwd",
            "uploads/../../../etc/passwd",
            "/etc/passwd",
            "uploads\\..\\.."
        ]
        for path in invalid_paths:
            valid, error = validate_storage_path(path)
            assert valid is False
            assert "Invalid storage path" in error or "invalid characters" in error


class TestFullFileValidation:
    """Test complete file validation flow"""

    def test_valid_file_passes_all_checks(self):
        filename = "document.pdf"
        content_type = "application/pdf"
        file_size = 1024 * 1024  # 1MB
        file_data = io.BytesIO(b"PDF content here")

        # Should not raise any exception
        perform_full_file_validation(filename, content_type, file_size, file_data)

    def test_data_file_passes_validation(self):
        """Test that .dat and other data files pass validation"""
        filename = "inter_data.dat"
        content_type = "application/octet-stream"
        file_size = 1024
        file_data = io.BytesIO(b"binary data content")

        # Should not raise any exception
        perform_full_file_validation(filename, content_type, file_size, file_data)

    def test_oversized_file_rejected(self):
        filename = "large.pdf"
        content_type = "application/pdf"
        file_size = MAX_UPLOAD_SIZE + 1
        file_data = io.BytesIO(b"x")

        with pytest.raises(BadRequestException) as exc:
            perform_full_file_validation(filename, content_type, file_size, file_data)
        assert "exceeds maximum" in str(exc.value.detail)

    def test_blocked_extension_rejected(self):
        filename = "program.exe"
        content_type = "application/octet-stream"
        file_size = 1024
        file_data = io.BytesIO(b"dummy content")

        with pytest.raises(BadRequestException) as exc:
            perform_full_file_validation(filename, content_type, file_size, file_data)
        assert "not allowed" in str(exc.value.detail)

    def test_dangerous_content_rejected(self):
        filename = "fake.pdf"
        content_type = "application/pdf"
        file_size = 1024
        file_data = io.BytesIO(b"MZ\x90\x00")  # Windows executable header

        with pytest.raises(BadRequestException) as exc:
            perform_full_file_validation(filename, content_type, file_size, file_data)
        assert "Windows executable" in str(exc.value.detail)
