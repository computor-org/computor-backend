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
    TEMPORAL_HOST,
    TEMPORAL_PORT,
    TEMPORAL_NAMESPACE,
)


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
            mock_connect.assert_called_once_with(
                target_host=f"{TEMPORAL_HOST}:{TEMPORAL_PORT}",
                namespace=TEMPORAL_NAMESPACE,
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
            # Reload module to pick up env vars
            import importlib
            importlib.reload(temporal_client)
            
            with patch('computor_backend.tasks.temporal_client.Client.connect') as mock_connect:
                mock_client = MagicMock()
                mock_connect.return_value = mock_client
                
                await temporal_client.get_temporal_client()
                
                # Verify TLS config was created
                call_args = mock_connect.call_args
                assert call_args[1]['tls'] is not None
                
        # Cleanup and reload without TLS
        temporal_client._client = None
        with patch.dict(os.environ, {
            'TEMPORAL_TLS_CERT': '',
            'TEMPORAL_TLS_KEY': '',
            'TEMPORAL_TLS_CA': ''
        }):
            importlib.reload(temporal_client)

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

    def test_environment_variable_defaults(self):
        """Test that environment variables have correct defaults."""
        # Test with no env vars set
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            import computor_backend.tasks.temporal_client as tc
            importlib.reload(tc)
            
            assert tc.TEMPORAL_HOST == 'localhost'
            assert tc.TEMPORAL_PORT == 7233
            assert tc.TEMPORAL_NAMESPACE == 'default'
            assert tc.TEMPORAL_TLS_CERT is None
            assert tc.TEMPORAL_TLS_KEY is None
            assert tc.TEMPORAL_TLS_CA is None

    def test_environment_variable_overrides(self):
        """Test that environment variables can be overridden."""
        with patch.dict(os.environ, {
            'TEMPORAL_HOST': 'custom-host',
            'TEMPORAL_PORT': '8888',
            'TEMPORAL_NAMESPACE': 'custom-namespace'
        }):
            import importlib
            import computor_backend.tasks.temporal_client as tc
            importlib.reload(tc)
            
            assert tc.TEMPORAL_HOST == 'custom-host'
            assert tc.TEMPORAL_PORT == 8888
            assert tc.TEMPORAL_NAMESPACE == 'custom-namespace'

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