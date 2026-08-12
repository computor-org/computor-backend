"""
Tests for Temporal client configuration and initialization.
"""

import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock
from temporalio.client import Client

from computor_backend.tasks.temporal_client import (
    get_temporal_client,
    close_temporal_client,
    get_task_queue_name,
    DEFAULT_TASK_QUEUE,
)
from computor_backend.tasks.worker_settings import get_worker_settings


class TestTemporalClient:
    """Test cases for Temporal client functionality."""

    @pytest.mark.asyncio
    async def test_get_temporal_client_creates_singleton(self):
        """Test that get_temporal_client creates a singleton instance."""
        # Reset global client
        from computor_backend.tasks import temporal_client
        temporal_client._client = None
        
        with patch('computor_backend.tasks.temporal_client.Client.connect') as mock_connect:
            mock_client = MagicMock()
            mock_connect.return_value = mock_client
            
            # First call should create client
            client1 = await get_temporal_client()
            assert client1 == mock_client
            assert mock_connect.call_count == 1
            
            # Second call should return same instance
            client2 = await get_temporal_client()
            assert client2 == mock_client
            assert mock_connect.call_count == 1  # Still only called once
            
        # Cleanup
        temporal_client._client = None

    @pytest.mark.asyncio
    async def test_get_temporal_client_with_default_config(self):
        """Test client creation with default configuration."""
        from computor_backend.tasks import temporal_client
        temporal_client._client = None
        
        with patch('computor_backend.tasks.temporal_client.Client.connect') as mock_connect:
            mock_client = MagicMock()
            mock_connect.return_value = mock_client
            
            await get_temporal_client()

            # Verify connection parameters
            settings = get_worker_settings()
            mock_connect.assert_called_once_with(
                target_host=f"{settings.temporal_host}:{settings.temporal_port}",
                namespace=settings.temporal_namespace,
                tls=None
            )
            
        # Cleanup
        temporal_client._client = None

    @pytest.mark.asyncio
    async def test_get_temporal_client_with_tls(self):
        """Test client creation with TLS configuration."""
        from computor_backend.tasks import temporal_client
        temporal_client._client = None
        
        # Mock TLS environment variables
        with patch.dict(os.environ, {
            'TEMPORAL_TLS_CERT': 'test_cert',
            'TEMPORAL_TLS_KEY': 'test_key',
            'TEMPORAL_TLS_CA': 'test_ca'
        }):
            # Settings are read lazily and cached, so drop the cache rather than
            # reloading the module (the config no longer lives at import time).
            get_worker_settings.cache_clear()

            with patch('computor_backend.tasks.temporal_client.Client.connect') as mock_connect:
                mock_client = MagicMock()
                mock_connect.return_value = mock_client

                await temporal_client.get_temporal_client()

                # Verify TLS config was created
                call_args = mock_connect.call_args
                assert call_args[1]['tls'] is not None

        # Cleanup: drop the client and the TLS-flavoured settings cache.
        temporal_client._client = None
        get_worker_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_close_temporal_client(self):
        """Test closing the Temporal client connection."""
        from computor_backend.tasks import temporal_client
        
        # Create a mock client
        mock_client = AsyncMock()
        temporal_client._client = mock_client
        
        # Close the client
        await close_temporal_client()
        
        # Verify client was closed and reset
        mock_client.close.assert_called_once()
        assert temporal_client._client is None

    @pytest.mark.asyncio
    async def test_close_temporal_client_when_none(self):
        """Test closing when no client exists."""
        from computor_backend.tasks import temporal_client
        temporal_client._client = None
        
        # Should not raise any errors
        await close_temporal_client()
        assert temporal_client._client is None

    def test_get_task_queue_name_with_default(self):
        """Test get_task_queue_name returns default when none provided."""
        result = get_task_queue_name(None)
        assert result == DEFAULT_TASK_QUEUE
        
        result = get_task_queue_name()
        assert result == DEFAULT_TASK_QUEUE

    def test_get_task_queue_name_with_custom(self):
        """Test get_task_queue_name returns custom queue name."""
        custom_queue = "custom-queue"
        result = get_task_queue_name(custom_queue)
        assert result == custom_queue

    # Temporal config is no longer module-level constants in temporal_client:
    # get_temporal_client() reads it lazily from WorkerSettings so env overrides
    # in effect at connect time are honored. These assert the settings instead,
    # clearing the lru_cache rather than reloading the module.

    def test_environment_variable_defaults(self):
        """Test that environment variables have correct defaults."""
        with patch.dict(os.environ, {}, clear=True):
            get_worker_settings.cache_clear()
            try:
                settings = get_worker_settings()
                assert settings.temporal_host == 'localhost'
                assert settings.temporal_port == 7233
                assert settings.temporal_namespace == 'default'
                assert settings.temporal_tls_cert is None
                assert settings.temporal_tls_key is None
                assert settings.temporal_tls_ca is None
            finally:
                get_worker_settings.cache_clear()

    def test_environment_variable_overrides(self):
        """Test that environment variables can be overridden."""
        with patch.dict(os.environ, {
            'TEMPORAL_HOST': 'custom-host',
            'TEMPORAL_PORT': '8888',
            'TEMPORAL_NAMESPACE': 'custom-namespace'
        }):
            get_worker_settings.cache_clear()
            try:
                settings = get_worker_settings()
                assert settings.temporal_host == 'custom-host'
                assert settings.temporal_port == 8888
                assert settings.temporal_namespace == 'custom-namespace'
            finally:
                get_worker_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_concurrent_client_creation(self):
        """Test that concurrent calls to get_temporal_client work correctly."""
        from computor_backend.tasks import temporal_client
        temporal_client._client = None
        
        with patch('computor_backend.tasks.temporal_client.Client.connect') as mock_connect:
            mock_client = MagicMock()
            mock_connect.return_value = mock_client
            
            # Simulate concurrent calls
            import asyncio
            results = await asyncio.gather(
                get_temporal_client(),
                get_temporal_client(),
                get_temporal_client()
            )
            
            # All should return the same instance
            assert all(r == mock_client for r in results)
            # Connect should only be called once
            assert mock_connect.call_count == 1
            
        # Cleanup
        temporal_client._client = None