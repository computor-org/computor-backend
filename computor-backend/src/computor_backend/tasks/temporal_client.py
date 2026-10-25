"""
Temporal client configuration and initialization.
"""

from temporalio.client import Client, TLSConfig
from typing import Optional
import asyncio
import base64
import binascii

from .worker_settings import get_worker_settings


# Default task queue
DEFAULT_TASK_QUEUE = "computor-tasks"

# NOTE: there is deliberately no module-level default RetryPolicy here. The one
# that used to live at this spot had bare ints where temporalio wants
# timedeltas, so it would have raised on conversion had anything ever used it —
# nothing did. Per-workflow policy belongs in BaseWorkflow.get_retry_policy().

_client: Optional[Client] = None
_client_lock = asyncio.Lock()


def _pem(value: str) -> bytes:
    """PEM bytes from either PEM text or single-line base64 of it.

    Single-line base64 lets a certificate live in a compose ``.env`` file,
    which cannot hold the multi-line PEM form reliably.
    """
    if value.lstrip().startswith("-----BEGIN"):
        return value.encode()
    try:
        decoded = base64.b64decode(value.strip(), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Temporal TLS value is neither PEM nor base64 PEM") from exc
    if not decoded.lstrip().startswith(b"-----BEGIN"):
        raise ValueError("Temporal TLS value is neither PEM nor base64 PEM")
    return decoded


def build_tls_config(settings) -> Optional[TLSConfig]:
    """mTLS settings for the frontend, or None when no client cert is set.

    A half-configured client (cert without key or the reverse) is an error
    rather than a silent fallback to plaintext.
    """
    cert, key = settings.temporal_tls_cert, settings.temporal_tls_key
    if not cert and not key:
        return None
    if not (cert and key):
        raise ValueError("TEMPORAL_TLS_CERT and TEMPORAL_TLS_KEY must be set together")
    return TLSConfig(
        client_cert=_pem(cert),
        client_private_key=_pem(key),
        server_root_ca_cert=_pem(settings.temporal_tls_ca) if settings.temporal_tls_ca else None,
        domain=settings.temporal_tls_server_name or None,
    )


def build_rpc_metadata(settings, tls_config: Optional[TLSConfig]) -> dict:
    """gRPC headers carrying TEMPORAL_API_KEY, or none when it is unset.

    The token is a bearer credential, so it is only sent over TLS.
    """
    token = (settings.temporal_api_key or "").strip()
    if not token:
        return {}
    if tls_config is None:
        raise ValueError("TEMPORAL_API_KEY requires TLS (set TEMPORAL_TLS_CERT and TEMPORAL_TLS_KEY)")
    return {"authorization": f"Bearer {token}"}


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
            tls_config = build_tls_config(settings)
            rpc_metadata = build_rpc_metadata(settings, tls_config)

            # Create client
            connect_kwargs = {"rpc_metadata": rpc_metadata} if rpc_metadata else {}
            _client = await Client.connect(
                target_host=f"{settings.temporal_host}:{settings.temporal_port}",
                namespace=settings.temporal_namespace,
                tls=tls_config,
                **connect_kwargs,
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