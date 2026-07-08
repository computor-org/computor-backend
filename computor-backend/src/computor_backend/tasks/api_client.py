"""Shared API-client helpers for testing activities.

Student and tutor testing activities each hand-rolled the same three things:
the env-first API config, the ``ComputorClient`` preamble, and the
zip-a-directory-and-upload artifact flow. They live here once.
"""
import logging
import os
import zipfile
from contextlib import asynccontextmanager
from io import BytesIO
from typing import Any, Dict, Optional

from temporalio.exceptions import ApplicationError

from computor_client import ComputorClient
from computor_backend.utils.docker_utils import transform_localhost_url
from computor_backend.tasks.worker_settings import get_worker_settings

logger = logging.getLogger(__name__)

_DEFAULT_API_URL = "http://localhost:8000"


def resolve_api_config(api_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return the effective ``{url, token}``, letting the worker env override.

    Activities read config from the worker they run on (``API_URL`` /
    ``API_TOKEN``), falling back to the workflow-passed value — so the same
    activity works regardless of which worker picks it up.
    """
    api_config = api_config or {}
    settings = get_worker_settings()
    # ``API_URL`` env overrides the workflow-passed url; else fall back to the
    # passed url, then to the static default (== settings.api_url's default).
    # model_fields_set tells us whether API_URL was actually in the environment,
    # preserving the old os.environ.get("API_URL", api_config[...]) precedence.
    if "api_url" in settings.model_fields_set:
        url = settings.api_url
    else:
        url = api_config.get("url", settings.api_url)
    return {
        "url": url,
        "token": settings.api_token or api_config.get("token"),
    }


@asynccontextmanager
async def open_computor_client(api_config: Optional[Dict[str, Any]]):
    """Async context manager yielding a ``ComputorClient`` for ``api_config``.

    Applies the docker-aware URL transform and X-API-Token header, and raises
    a Temporal ``ApplicationError`` when the token is missing.
    """
    cfg = api_config or {}
    base_url = transform_localhost_url(cfg.get("url", _DEFAULT_API_URL))
    token = cfg.get("token")
    if not token:
        raise ApplicationError("API token is required but not provided in api_config")
    async with ComputorClient(base_url=base_url, headers={"X-API-Token": token}) as client:
        yield client


async def upload_artifacts_zip(
    api_config: Optional[Dict[str, Any]],
    endpoint: str,
    artifacts_path: str,
) -> int:
    """Zip every file under ``artifacts_path`` and POST it to ``endpoint``.

    Returns the number of files uploaded (0 when the path is missing or empty).
    """
    if not os.path.exists(artifacts_path):
        logger.info("Artifacts path does not exist: %s", artifacts_path)
        return 0

    zip_buffer = BytesIO()
    file_count = 0
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, _dirs, filenames in os.walk(artifacts_path):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, artifacts_path)
                zip_file.write(file_path, rel_path)
                file_count += 1
                logger.debug("Added artifact '%s' to ZIP", rel_path)

    if file_count == 0:
        logger.info("No artifacts to upload")
        return 0

    zip_buffer.seek(0)
    zip_data = zip_buffer.read()
    logger.info("Uploading %d artifacts as ZIP (%d bytes) to %s", file_count, len(zip_data), endpoint)

    async with open_computor_client(api_config) as client:
        response = await client._http.post(
            endpoint,
            files={"file": ("artifacts.zip", zip_data, "application/zip")},
        )
        response.raise_for_status()

    logger.info("Uploaded %d artifacts via API to %s", file_count, endpoint)
    return file_count
