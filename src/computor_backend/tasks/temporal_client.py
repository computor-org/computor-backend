"""
Temporal client configuration and initialization.
"""

import os
from temporalio.client import Client, TLSConfig
from temporalio.common import RetryPolicy
from typing import Optional
import asyncio


# Temporal server configuration from environment
TEMPORAL_HOST = os.environ.get('TEMPORAL_HOST', 'localhost')
TEMPORAL_PORT = int(os.environ.get('TEMPORAL_PORT', '7233'))
TEMPORAL_NAMESPACE = os.environ.get('TEMPORAL_NAMESPACE', 'default')

# TLS configuration (optional)
TEMPORAL_TLS_CERT = os.environ.get('TEMPORAL_TLS_CERT')
TEMPORAL_TLS_KEY = os.environ.get('TEMPORAL_TLS_KEY')
TEMPORAL_TLS_CA = os.environ.get('TEMPORAL_TLS_CA')

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
            tls_config = None
            
            # Configure TLS if certificates are provided
            if TEMPORAL_TLS_CERT and TEMPORAL_TLS_KEY:
                tls_config = TLSConfig(
                    client_cert=TEMPORAL_TLS_CERT.encode(),
                    client_private_key=TEMPORAL_TLS_KEY.encode(),
                    server_root_ca_cert=TEMPORAL_TLS_CA.encode() if TEMPORAL_TLS_CA else None,
                )
            
            # Create client
            _client = await Client.connect(
                target_host=f"{TEMPORAL_HOST}:{TEMPORAL_PORT}",
                namespace=TEMPORAL_NAMESPACE,
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