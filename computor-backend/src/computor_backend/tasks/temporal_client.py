"""
Temporal client configuration and initialization.
"""

from temporalio.client import Client, TLSConfig
from temporalio.common import RetryPolicy
from typing import Optional
import asyncio

from .worker_settings import get_worker_settings


# Default task queue
DEFAULT_TASK_QUEUE = "computor-tasks"

# Default retry policy
DEFAULT_RETRY_POLICY = RetryPolicy(
    initial_interval=1,
    backoff_coefficient=2.0,
    maximum_interval=100,
    maximum_attempts=3,
)


_client: Optional[Client] = None
_client_lock = asyncio.Lock()


async def get_temporal_client() -> Client:
    """
    Get or create a Temporal client instance.
    
    Returns:
        Configured Temporal client
    """
    global _client
    
    async with _client_lock:
        if _client is None:
            # Read config lazily (not at import) so the environment / test
            # overrides in effect when the client first connects are honored.
            settings = get_worker_settings()
            tls_config = None

            # Configure TLS if certificates are provided
            if settings.temporal_tls_cert and settings.temporal_tls_key:
                tls_config = TLSConfig(
                    client_cert=settings.temporal_tls_cert.encode(),
                    client_private_key=settings.temporal_tls_key.encode(),
                    server_root_ca_cert=settings.temporal_tls_ca.encode() if settings.temporal_tls_ca else None,
                )

            # Create client
            _client = await Client.connect(
                target_host=f"{settings.temporal_host}:{settings.temporal_port}",
                namespace=settings.temporal_namespace,
                tls=tls_config,
            )

        return _client


def get_task_queue_name(queue_name: Optional[str] = None) -> str:
    """
    Get task queue name, using default if none provided.
    
    Args:
        queue_name: Task queue name (optional)
        
    Returns:
        Task queue name to use
    """
    return queue_name or DEFAULT_TASK_QUEUE


async def close_temporal_client():
    """Close the Temporal client connection."""
    global _client
    async with _client_lock:
        if _client:
            await _client.close()
            _client = None