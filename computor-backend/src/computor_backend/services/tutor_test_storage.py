"""
Service for storing tutor test files, results, and artifacts in MinIO.

This module handles ephemeral storage for tutor testing - tutors can test their
own code against assignment references without creating database records.

Storage structure in 'tutor-tests' bucket:
- {test_id}/input/{filename}     - Uploaded tutor files (from ZIP)
- {test_id}/result.json          - Test results JSON
- {test_id}/artifacts/{filename} - Generated artifacts (plots, figures, etc.)

All objects are automatically cleaned up via MinIO lifecycle policy (1 day expiration).
"""

import json
import logging
import zipfile
from datetime import timedelta
from io import BytesIO
from typing import Optional
from uuid import UUID

from minio.commonconfig import ENABLED, Filter
from minio.lifecycleconfig import Expiration, LifecycleConfig, Rule

from ..api.exceptions import NotFoundException, ServiceUnavailableException
from ..minio_client import get_minio_client

logger = logging.getLogger(__name__)

# Dedicated bucket for tutor tests (ephemeral)
TUTOR_TESTS_BUCKET = "tutor-tests"

# Lifecycle expiration in days (MinIO minimum is 1 day)
TUTOR_TESTS_EXPIRATION_DAYS = 1


def ensure_tutor_tests_bucket_exists() -> None:
    """
    Ensure the tutor-tests bucket exists with lifecycle policy.

    Creates the bucket if it doesn't exist and configures automatic
    object expiration after TUTOR_TESTS_EXPIRATION_DAYS.
    """
    client = get_minio_client()

    try:
        if not client.bucket_exists(TUTOR_TESTS_BUCKET):
            logger.info(f"Creating bucket: {TUTOR_TESTS_BUCKET}")
            client.make_bucket(TUTOR_TESTS_BUCKET)

            # Configure lifecycle policy for automatic cleanup
            lifecycle_config = LifecycleConfig([
                Rule(
                    ENABLED,
                    rule_filter=Filter(prefix=""),  # All objects in bucket
                    rule_id="tutor-tests-auto-expiry",
                    expiration=Expiration(days=TUTOR_TESTS_EXPIRATION_DAYS),
                ),
            ])
            client.set_bucket_lifecycle(TUTOR_TESTS_BUCKET, lifecycle_config)
            logger.info(
                f"Configured lifecycle policy: objects expire after "
                f"{TUTOR_TESTS_EXPIRATION_DAYS} day(s)"
            )
    except Exception as e:
        logger.error(f"Error ensuring tutor-tests bucket exists: {e}")
        raise ServiceUnavailableException(f"Storage service error: {e}")


async def store_tutor_test_input(
    test_id: str | UUID,
    zip_data: bytes,
) -> dict:
    """
    Store tutor's uploaded ZIP file contents in MinIO.

    Extracts the ZIP and stores each file individually under {test_id}/input/.

    Args:
        test_id: Unique identifier for this test run
        zip_data: Raw bytes of the uploaded ZIP file

    Returns:
        Dict with storage info: files_count, total_size, file_list

    Raises:
        ServiceUnavailableException: If storage fails
    """
    client = get_minio_client()
    ensure_tutor_tests_bucket_exists()

    test_id_str = str(test_id)
    files_stored = []
    total_size = 0

    try:
        zip_buffer = BytesIO(zip_data)

        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            # Security check: limit file count and total size
            file_list = zip_file.namelist()
            if len(file_list) > 1000:
                raise ServiceUnavailableException(
                    "ZIP contains too many files (max 1000)"
                )

            for filename in file_list:
                # Skip directories
                if filename.endswith('/'):
                    continue

                # Skip hidden files and system files
                if filename.startswith('.') or filename.startswith('__'):
                    continue

                # Read file content
                file_content = zip_file.read(filename)
                file_size = len(file_content)
                total_size += file_size

                # Security check: max 100MB total
                if total_size > 100 * 1024 * 1024:
                    raise ServiceUnavailableException(
                        "ZIP total size exceeds 100MB limit"
                    )

                # Store in MinIO
                # Handle nested directories in ZIP - flatten or preserve structure
                # We preserve the structure as-is
                object_key = f"{test_id_str}/input/{filename}"

                file_stream = BytesIO(file_content)
                client.put_object(
                    bucket_name=TUTOR_TESTS_BUCKET,
                    object_name=object_key,
                    data=file_stream,
                    length=file_size,
                    content_type="application/octet-stream",
                    metadata={
                        "x-amz-meta-test-id": test_id_str,
                        "x-amz-meta-type": "tutor-test-input",
                    }
                )

                files_stored.append(filename)
                logger.debug(f"Stored tutor test input: {object_key}")

        logger.info(
            f"Stored {len(files_stored)} files for tutor test {test_id_str} "
            f"({total_size} bytes)"
        )

        return {
            "files_count": len(files_stored),
            "total_size": total_size,
            "file_list": files_stored,
        }

    except zipfile.BadZipFile:
        raise ServiceUnavailableException("Invalid ZIP file")
    except Exception as e:
        logger.error(f"Error storing tutor test input: {e}")
        raise ServiceUnavailableException(f"Storage error: {e}")


async def get_tutor_test_input_path(test_id: str | UUID) -> str:
    """
    Get the MinIO prefix path for tutor test input files.

    Args:
        test_id: The test ID

    Returns:
        The prefix path: {test_id}/input/
    """
    return f"{str(test_id)}/input/"


async def download_tutor_test_input_as_zip(test_id: str | UUID) -> bytes:
    """
    Download all input files for a tutor test as a ZIP.

    Args:
        test_id: The test ID

    Returns:
        ZIP file bytes

    Raises:
        NotFoundException: If no input files found
    """
    client = get_minio_client()
    test_id_str = str(test_id)
    prefix = f"{test_id_str}/input/"

    try:
        objects = list(client.list_objects(
            TUTOR_TESTS_BUCKET,
            prefix=prefix,
            recursive=True
        ))

        if not objects:
            raise NotFoundException(f"No input files found for test {test_id_str}")

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for obj in objects:
                if obj.object_name.endswith('/'):
                    continue

                # Download file
                response = client.get_object(TUTOR_TESTS_BUCKET, obj.object_name)
                file_content = response.read()
                response.close()
                response.release_conn()

                # Add to ZIP with relative path
                relative_path = obj.object_name.replace(prefix, "")
                zip_file.writestr(relative_path, file_content)

        zip_buffer.seek(0)
        return zip_buffer.read()

    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error downloading tutor test input: {e}")
        raise ServiceUnavailableException(f"Storage error: {e}")


async def store_tutor_test_result(
    test_id: str | UUID,
    result_json: dict,
) -> str:
    """
    Store test result JSON in MinIO.

    Args:
        test_id: The test ID
        result_json: The test results dictionary

    Returns:
        The object key where result was stored
    """
    client = get_minio_client()
    ensure_tutor_tests_bucket_exists()

    test_id_str = str(test_id)
    object_key = f"{test_id_str}/result.json"

    try:
        json_bytes = json.dumps(result_json, indent=2).encode('utf-8')
        json_stream = BytesIO(json_bytes)

        client.put_object(
            bucket_name=TUTOR_TESTS_BUCKET,
            object_name=object_key,
            data=json_stream,
            length=len(json_bytes),
            content_type="application/json",
            metadata={
                "x-amz-meta-test-id": test_id_str,
                "x-amz-meta-type": "tutor-test-result",
            }
        )

        logger.info(f"Stored tutor test result: {object_key}")
        return object_key

    except Exception as e:
        logger.error(f"Error storing tutor test result: {e}")
        raise ServiceUnavailableException(f"Storage error: {e}")


async def retrieve_tutor_test_result(test_id: str | UUID) -> Optional[dict]:
    """
    Retrieve test result JSON from MinIO.

    Args:
        test_id: The test ID

    Returns:
        The test results dictionary, or None if not found
    """
    client = get_minio_client()
    test_id_str = str(test_id)
    object_key = f"{test_id_str}/result.json"

    try:
        response = client.get_object(TUTOR_TESTS_BUCKET, object_key)
        json_bytes = response.read()
        response.close()
        response.release_conn()

        return json.loads(json_bytes.decode('utf-8'))

    except Exception as e:
        if "NoSuchKey" in str(e):
            return None
        logger.error(f"Error retrieving tutor test result: {e}")
        return None


# Alias for API usage
get_tutor_test_result_from_minio = retrieve_tutor_test_result


async def store_tutor_test_artifact(
    test_id: str | UUID,
    filename: str,
    file_data: bytes,
    content_type: Optional[str] = None,
) -> dict:
    """
    Store a single artifact file in MinIO.

    Args:
        test_id: The test ID
        filename: The artifact filename
        file_data: The file content
        content_type: Optional MIME type

    Returns:
        Dict with storage info
    """
    import mimetypes

    client = get_minio_client()
    ensure_tutor_tests_bucket_exists()

    test_id_str = str(test_id)
    object_key = f"{test_id_str}/artifacts/{filename}"

    # Guess content type if not provided
    if content_type is None:
        content_type, _ = mimetypes.guess_type(filename)
        if content_type is None:
            content_type = "application/octet-stream"

    try:
        file_stream = BytesIO(file_data)
        client.put_object(
            bucket_name=TUTOR_TESTS_BUCKET,
            object_name=object_key,
            data=file_stream,
            length=len(file_data),
            content_type=content_type,
            metadata={
                "x-amz-meta-test-id": test_id_str,
                "x-amz-meta-type": "tutor-test-artifact",
                "x-amz-meta-filename": filename,
            }
        )

        logger.debug(f"Stored tutor test artifact: {object_key}")

        return {
            "object_key": object_key,
            "file_size": len(file_data),
            "content_type": content_type,
        }

    except Exception as e:
        logger.error(f"Error storing tutor test artifact: {e}")
        raise ServiceUnavailableException(f"Storage error: {e}")


async def store_tutor_test_artifacts_from_zip(
    test_id: str | UUID,
    zip_data: bytes,
) -> int:
    """
    Store multiple artifacts from a ZIP file.

    Args:
        test_id: The test ID
        zip_data: ZIP file bytes containing artifacts

    Returns:
        Number of artifacts stored
    """
    client = get_minio_client()
    ensure_tutor_tests_bucket_exists()

    test_id_str = str(test_id)
    files_stored = 0

    try:
        zip_buffer = BytesIO(zip_data)

        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            for filename in zip_file.namelist():
                if filename.endswith('/'):
                    continue

                file_content = zip_file.read(filename)
                await store_tutor_test_artifact(
                    test_id=test_id,
                    filename=filename,
                    file_data=file_content,
                )
                files_stored += 1

        logger.info(f"Stored {files_stored} artifacts for tutor test {test_id_str}")
        return files_stored

    except Exception as e:
        logger.error(f"Error storing tutor test artifacts: {e}")
        raise ServiceUnavailableException(f"Storage error: {e}")


async def list_tutor_test_artifacts(test_id: str | UUID) -> list[dict]:
    """
    List all artifacts for a tutor test.

    Args:
        test_id: The test ID

    Returns:
        List of dicts with artifact info
    """
    client = get_minio_client()
    test_id_str = str(test_id)
    prefix = f"{test_id_str}/artifacts/"

    try:
        objects = client.list_objects(
            TUTOR_TESTS_BUCKET,
            prefix=prefix,
            recursive=True
        )

        artifacts = []
        for obj in objects:
            if obj.object_name.endswith('/'):
                continue

            artifacts.append({
                "filename": obj.object_name.split("/")[-1],
                "object_key": obj.object_name,
                "size": obj.size,
                "last_modified": obj.last_modified,
            })

        return artifacts

    except Exception as e:
        logger.error(f"Error listing tutor test artifacts: {e}")
        return []


async def download_tutor_test_artifacts_as_zip(test_id: str | UUID) -> Optional[bytes]:
    """
    Download all artifacts for a tutor test as a ZIP file.

    Args:
        test_id: The test ID

    Returns:
        ZIP file bytes, or None if no artifacts
    """
    client = get_minio_client()
    test_id_str = str(test_id)
    prefix = f"{test_id_str}/artifacts/"

    try:
        objects = list(client.list_objects(
            TUTOR_TESTS_BUCKET,
            prefix=prefix,
            recursive=True
        ))

        if not objects:
            return None

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for obj in objects:
                if obj.object_name.endswith('/'):
                    continue

                response = client.get_object(TUTOR_TESTS_BUCKET, obj.object_name)
                file_content = response.read()
                response.close()
                response.release_conn()

                filename = obj.object_name.split("/")[-1]
                zip_file.writestr(filename, file_content)

        zip_buffer.seek(0)
        return zip_buffer.read()

    except Exception as e:
        logger.error(f"Error downloading tutor test artifacts: {e}")
        return None


async def extract_tutor_test_input_to_directory(
    test_id: str | UUID,
    target_dir: str,
) -> str:
    """
    Extract tutor test input files from MinIO to a local directory.

    This is used by the Temporal workflow to get the tutor's files
    for test execution.

    Args:
        test_id: The test ID
        target_dir: Directory to extract files to

    Returns:
        Path to the directory containing extracted files

    Raises:
        NotFoundException: If no input files found
    """
    import os

    client = get_minio_client()
    test_id_str = str(test_id)
    prefix = f"{test_id_str}/input/"

    try:
        objects = list(client.list_objects(
            TUTOR_TESTS_BUCKET,
            prefix=prefix,
            recursive=True
        ))

        if not objects:
            raise NotFoundException(f"No input files found for test {test_id_str}")

        os.makedirs(target_dir, exist_ok=True)

        for obj in objects:
            if obj.object_name.endswith('/'):
                continue

            # Get relative path within input/
            relative_path = obj.object_name.replace(prefix, "")
            local_path = os.path.join(target_dir, relative_path)

            # Create parent directories
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # Download file
            response = client.get_object(TUTOR_TESTS_BUCKET, obj.object_name)
            with open(local_path, 'wb') as f:
                f.write(response.read())
            response.close()
            response.release_conn()

            logger.debug(f"Extracted: {obj.object_name} -> {local_path}")

        logger.info(f"Extracted tutor test input to {target_dir}")
        return target_dir

    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error extracting tutor test input: {e}")
        raise ServiceUnavailableException(f"Storage error: {e}")
