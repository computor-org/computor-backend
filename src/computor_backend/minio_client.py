import os
from typing import Optional
from minio import Minio
from minio.error import S3Error
import logging
from .utils.docker_utils import is_running_in_docker

logger = logging.getLogger(__name__)


def get_minio_endpoint() -> str:
    """
    Get MinIO endpoint, handling Docker networking.
    
    Returns:
        str: MinIO endpoint URL
    """
    endpoint = os.environ.get('MINIO_ENDPOINT', 'localhost:9000')
    
    # In Docker environment, use the MinIO service name for container-to-container communication
    if is_running_in_docker() and 'localhost' in endpoint:
        # When services communicate within Docker network, use service name
        return endpoint.replace('localhost', 'minio')
    
    return endpoint


# Environment configuration
MINIO_ENDPOINT = get_minio_endpoint()
MINIO_ACCESS_KEY = os.environ.get('MINIO_ACCESS_KEY', 'minioadmin')
MINIO_SECRET_KEY = os.environ.get('MINIO_SECRET_KEY', 'minioadmin')
MINIO_SECURE = os.environ.get('MINIO_SECURE', 'false').lower() == 'true'
MINIO_REGION = os.environ.get('MINIO_REGION', 'us-east-1')
MINIO_DEFAULT_BUCKET = os.environ.get('MINIO_DEFAULT_BUCKET', 'computor-storage')

_minio_client: Optional[Minio] = None


def get_minio_client() -> Minio:
    """Get the singleton MinIO client instance"""
    global _minio_client
    if _minio_client is None:
        logger.info(f"Initializing MinIO client for endpoint: {MINIO_ENDPOINT}")
        _minio_client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE,
            region=MINIO_REGION
        )
        
        # Ensure default bucket exists
        try:
            if not _minio_client.bucket_exists(MINIO_DEFAULT_BUCKET):
                logger.info(f"Creating default bucket: {MINIO_DEFAULT_BUCKET}")
                _minio_client.make_bucket(MINIO_DEFAULT_BUCKET, location=MINIO_REGION)
        except S3Error as e:
            logger.warning(f"Error checking/creating default bucket: {e}")
            
    return _minio_client


def reset_minio_client():
    """Reset the MinIO client (useful for testing)"""
    global _minio_client
    _minio_client = None