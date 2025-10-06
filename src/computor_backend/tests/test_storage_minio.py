import pytest
import io
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from minio.error import S3Error

from computor_backend.minio_client import get_minio_client, reset_minio_client
from computor_backend.services.storage_service import StorageService, get_storage_service
from computor_types.storage import (
    StorageObjectMetadata,
    BucketInfo,
    PresignedUrlResponse,
    StorageUsageStats
)
from computor_backend.api.exceptions import (
    ServiceUnavailableException,
    NotFoundException,
    BadRequestException
)


@pytest.fixture
def mock_minio_client():
    """Create a mock MinIO client"""
    with patch('computor_backend.minio_client.Minio') as mock_minio_class:
        mock_client = MagicMock()
        mock_minio_class.return_value = mock_client
        
        # Reset the client to force recreation with mock
        reset_minio_client()
        
        yield mock_client
        
        # Reset after test
        reset_minio_client()


@pytest.fixture
def storage_service(mock_minio_client):
    """Create a storage service with mocked MinIO client"""
    service = StorageService()
    service.client = mock_minio_client
    return service


class TestMinIOClient:
    """Test MinIO client initialization and configuration"""
    
    def test_minio_client_singleton(self):
        """Test that MinIO client is a singleton"""
        client1 = get_minio_client()
        client2 = get_minio_client()
        assert client1 is client2
    
    def test_minio_client_environment_config(self):
        """Test MinIO client reads environment configuration"""
        # We need to patch the module-level constants, not the environment variables
        # since they're read at import time
        with patch('computor_backend.minio_client.MINIO_ENDPOINT', 'test-endpoint:9000'):
            with patch('computor_backend.minio_client.MINIO_ACCESS_KEY', 'test-access-key'):
                with patch('computor_backend.minio_client.MINIO_SECRET_KEY', 'test-secret-key'):
                    with patch('computor_backend.minio_client.MINIO_SECURE', True):
                        with patch('computor_backend.minio_client.MINIO_REGION', 'us-west-2'):
                            with patch('computor_backend.minio_client.Minio') as mock_minio:
                                reset_minio_client()
                                get_minio_client()
                                
                                mock_minio.assert_called_once_with(
                                    'test-endpoint:9000',
                                    access_key='test-access-key',
                                    secret_key='test-secret-key',
                                    secure=True,
                                    region='us-west-2'
                                )


class TestStorageService:
    """Test storage service operations"""
    
    @pytest.mark.asyncio
    async def test_upload_file(self, storage_service, mock_minio_client):
        """Test file upload"""
        # Mock stat_object response
        mock_stat = Mock()
        mock_stat.content_type = 'text/plain'
        mock_stat.size = 100
        mock_stat.etag = 'test-etag'
        mock_stat.last_modified = datetime.now(timezone.utc)
        mock_stat.metadata = {}
        
        mock_minio_client.bucket_exists.return_value = True
        mock_minio_client.stat_object.return_value = mock_stat
        
        # Test upload
        file_data = io.BytesIO(b"test content")
        result = await storage_service.upload_file(
            file_data=file_data,
            object_key='test/file.txt',
            content_type='text/plain',
            metadata={'user': 'test'}
        )
        
        # Verify calls
        mock_minio_client.put_object.assert_called_once()
        assert result.content_type == 'text/plain'
        assert result.size == 100
        assert result.etag == 'test-etag'
    
    @pytest.mark.asyncio
    async def test_upload_file_bucket_creation(self, storage_service, mock_minio_client):
        """Test that bucket is created if it doesn't exist"""
        mock_minio_client.bucket_exists.return_value = False
        
        await storage_service.ensure_bucket_exists('new-bucket')
        
        mock_minio_client.make_bucket.assert_called_once_with('new-bucket')
    
    @pytest.mark.asyncio
    async def test_download_file(self, storage_service, mock_minio_client):
        """Test file download"""
        mock_response = Mock()
        mock_response.read.return_value = b"test content"
        mock_minio_client.get_object.return_value = mock_response
        
        result = await storage_service.download_file('test/file.txt')
        
        assert result == b"test content"
        mock_response.close.assert_called_once()
        mock_response.release_conn.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_download_file_not_found(self, storage_service, mock_minio_client):
        """Test download of non-existent file"""
        error = S3Error('NoSuchKey', 'The specified key does not exist.', 
                        resource='test/file.txt', request_id='test', 
                        host_id='test', response='test')
        mock_minio_client.get_object.side_effect = error
        
        with pytest.raises(NotFoundException) as exc:
            await storage_service.download_file('test/file.txt')
        
        assert "Object not found: test/file.txt" in str(exc.value)
    
    @pytest.mark.asyncio
    async def test_delete_file(self, storage_service, mock_minio_client):
        """Test file deletion"""
        result = await storage_service.delete_file('test/file.txt')
        
        assert result is True
        mock_minio_client.remove_object.assert_called_once_with(
            storage_service.default_bucket, 'test/file.txt'
        )
    
    @pytest.mark.asyncio
    async def test_list_objects(self, storage_service, mock_minio_client):
        """Test listing objects"""
        mock_obj1 = Mock()
        mock_obj1.object_name = 'file1.txt'
        mock_obj1.size = 100
        
        mock_obj2 = Mock()
        mock_obj2.object_name = 'file2.txt'
        mock_obj2.size = 200
        
        mock_minio_client.list_objects.return_value = [mock_obj1, mock_obj2]
        
        result = await storage_service.list_objects(prefix='test/')
        
        assert len(result) == 2
        assert result[0].object_name == 'file1.txt'
        assert result[1].object_name == 'file2.txt'
    
    @pytest.mark.asyncio
    async def test_generate_presigned_url_get(self, storage_service, mock_minio_client):
        """Test generating presigned URL for GET"""
        mock_minio_client.presigned_get_object.return_value = 'https://example.com/presigned'
        
        result = await storage_service.generate_presigned_url(
            object_key='test/file.txt',
            method='GET',
            expiry_seconds=3600
        )
        
        assert isinstance(result, PresignedUrlResponse)
        assert result.url == 'https://example.com/presigned'
        assert result.method == 'GET'
    
    @pytest.mark.asyncio
    async def test_generate_presigned_url_put(self, storage_service, mock_minio_client):
        """Test generating presigned URL for PUT"""
        mock_minio_client.presigned_put_object.return_value = 'https://example.com/presigned'
        
        result = await storage_service.generate_presigned_url(
            object_key='test/file.txt',
            method='PUT',
            expiry_seconds=3600
        )
        
        assert isinstance(result, PresignedUrlResponse)
        assert result.url == 'https://example.com/presigned'
        assert result.method == 'PUT'
    
    @pytest.mark.asyncio
    async def test_copy_object(self, storage_service, mock_minio_client):
        """Test copying an object"""
        mock_stat = Mock()
        mock_stat.content_type = 'text/plain'
        mock_stat.size = 100
        mock_stat.etag = 'test-etag'
        mock_stat.last_modified = datetime.now(timezone.utc)
        mock_stat.metadata = {}
        
        mock_minio_client.bucket_exists.return_value = True
        mock_minio_client.stat_object.return_value = mock_stat
        
        result = await storage_service.copy_object(
            source_object='source/file.txt',
            dest_object='dest/file.txt'
        )
        
        mock_minio_client.copy_object.assert_called_once()
        assert isinstance(result, StorageObjectMetadata)
    
    @pytest.mark.asyncio
    async def test_list_buckets(self, storage_service, mock_minio_client):
        """Test listing buckets"""
        mock_bucket1 = Mock()
        mock_bucket1.name = 'bucket1'
        mock_bucket1.creation_date = datetime.now(timezone.utc)
        
        mock_bucket2 = Mock()
        mock_bucket2.name = 'bucket2'
        mock_bucket2.creation_date = datetime.now(timezone.utc)
        
        mock_minio_client.list_buckets.return_value = [mock_bucket1, mock_bucket2]
        
        result = await storage_service.list_buckets()
        
        assert len(result) == 2
        assert all(isinstance(b, BucketInfo) for b in result)
        assert result[0].bucket_name == 'bucket1'
        assert result[1].bucket_name == 'bucket2'
    
    @pytest.mark.asyncio
    async def test_create_bucket(self, storage_service, mock_minio_client):
        """Test bucket creation"""
        mock_minio_client.bucket_exists.return_value = False
        
        result = await storage_service.create_bucket('new-bucket', region='us-west-2')
        
        mock_minio_client.make_bucket.assert_called_once_with('new-bucket', location='us-west-2')
        assert isinstance(result, BucketInfo)
        assert result.bucket_name == 'new-bucket'
    
    @pytest.mark.asyncio
    async def test_create_bucket_already_exists(self, storage_service, mock_minio_client):
        """Test creating a bucket that already exists"""
        mock_minio_client.bucket_exists.return_value = True
        
        with pytest.raises(BadRequestException) as exc:
            await storage_service.create_bucket('existing-bucket')
        
        assert "Bucket already exists: existing-bucket" in str(exc.value)
    
    @pytest.mark.asyncio
    async def test_delete_bucket(self, storage_service, mock_minio_client):
        """Test bucket deletion"""
        result = await storage_service.delete_bucket('test-bucket')
        
        assert result is True
        mock_minio_client.remove_bucket.assert_called_once_with('test-bucket')
    
    @pytest.mark.asyncio
    async def test_delete_bucket_force(self, storage_service, mock_minio_client):
        """Test force deletion of non-empty bucket"""
        mock_obj = Mock()
        mock_obj.object_name = 'file.txt'
        mock_minio_client.list_objects.return_value = [mock_obj]
        
        result = await storage_service.delete_bucket('test-bucket', force=True)
        
        assert result is True
        mock_minio_client.remove_object.assert_called_once_with('test-bucket', 'file.txt')
        mock_minio_client.remove_bucket.assert_called_once_with('test-bucket')
    
    @pytest.mark.asyncio
    async def test_get_bucket_stats(self, storage_service, mock_minio_client):
        """Test getting bucket statistics"""
        mock_obj1 = Mock()
        mock_obj1.size = 100
        
        mock_obj2 = Mock()
        mock_obj2.size = 200
        
        mock_minio_client.list_objects.return_value = [mock_obj1, mock_obj2]
        
        result = await storage_service.get_bucket_stats('test-bucket')
        
        assert isinstance(result, StorageUsageStats)
        assert result.bucket_name == 'test-bucket'
        assert result.object_count == 2
        assert result.total_size == 300
    
    @pytest.mark.asyncio
    async def test_extract_custom_metadata(self, storage_service):
        """Test custom metadata extraction"""
        metadata = {
            'X-Amz-Meta-User': 'test-user',
            'X-Amz-Meta-Department': 'engineering',
            'Content-Type': 'text/plain'
        }
        
        result = storage_service._extract_custom_metadata(metadata)
        
        assert result == {
            'user': 'test-user',
            'department': 'engineering'
        }
        assert 'Content-Type' not in result


class TestStorageServiceErrors:
    """Test error handling in storage service"""
    
    @pytest.mark.asyncio
    async def test_service_unavailable_on_s3_error(self, storage_service, mock_minio_client):
        """Test that S3 errors are converted to ServiceUnavailableException"""
        error = S3Error('InternalError', 'Internal Server Error', 
                        resource='test', request_id='test', 
                        host_id='test', response='test')
        mock_minio_client.list_buckets.side_effect = error
        
        with pytest.raises(ServiceUnavailableException):
            await storage_service.list_buckets()
    
    @pytest.mark.asyncio
    async def test_not_found_bucket(self, storage_service, mock_minio_client):
        """Test NotFoundException for missing buckets"""
        error = S3Error('NoSuchBucket', 'The specified bucket does not exist.', 
                        resource='missing-bucket', request_id='test', 
                        host_id='test', response='test')
        mock_minio_client.list_objects.side_effect = error
        
        with pytest.raises(NotFoundException) as exc:
            await storage_service.list_objects(bucket_name='missing-bucket')
        
        assert "Bucket not found: missing-bucket" in str(exc.value)