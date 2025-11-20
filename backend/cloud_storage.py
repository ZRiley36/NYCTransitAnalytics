"""Cloud Storage Layer for GTFS-RT Raw Files

Supports AWS S3 and Google Cloud Storage (GCS)
"""

import os
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import logging

# Configure logging if not already configured
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CloudStorageProvider(ABC):
    """Abstract base class for cloud storage providers"""
    
    @abstractmethod
    async def upload_file(self, local_filepath: Path, remote_key: str) -> bool:
        """Upload a file to cloud storage"""
        pass
    
    @abstractmethod
    async def file_exists(self, remote_key: str) -> bool:
        """Check if a file exists in cloud storage"""
        pass


class S3StorageProvider(CloudStorageProvider):
    """AWS S3 Storage Provider"""
    
    def __init__(
        self,
        bucket_name: str,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region: str = "us-east-1",
    ):
        try:
            import boto3
            from botocore.config import Config
        except ImportError:
            raise ImportError(
                "boto3 is required for S3 storage. Install with: pip install boto3"
            )
        
        self.bucket_name = bucket_name
        self.region = region
        
        # Create S3 client
        config = Config(region_name=region)
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY"),
            config=config,
        )
        
        logger.info(f"S3 Storage initialized: bucket={bucket_name}, region={region}")
    
    async def upload_file(self, local_filepath: Path, remote_key: str) -> bool:
        """Upload file to S3"""
        try:
            # Run synchronous boto3 call in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.upload_file(
                    str(local_filepath),
                    self.bucket_name,
                    remote_key,
                )
            )
            logger.info(f"Uploaded to S3: s3://{self.bucket_name}/{remote_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload to S3: {e}")
            return False
    
    async def file_exists(self, remote_key: str) -> bool:
        """Check if file exists in S3"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.head_object(Bucket=self.bucket_name, Key=remote_key)
            )
            return True
        except Exception:
            return False


class GCSStorageProvider(CloudStorageProvider):
    """Google Cloud Storage Provider"""
    
    def __init__(
        self,
        bucket_name: str,
        credentials_path: Optional[str] = None,
    ):
        try:
            from google.cloud import storage
            from google.oauth2 import service_account
        except ImportError:
            raise ImportError(
                "google-cloud-storage is required for GCS. Install with: pip install google-cloud-storage"
            )
        
        self.bucket_name = bucket_name
        
        # Initialize GCS client
        if credentials_path:
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            self.storage_client = storage.Client(credentials=credentials)
        elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            self.storage_client = storage.Client()
        else:
            # Try default credentials
            self.storage_client = storage.Client()
        
        self.bucket = self.storage_client.bucket(bucket_name)
        logger.info(f"GCS Storage initialized: bucket={bucket_name}")
    
    async def upload_file(self, local_filepath: Path, remote_key: str) -> bool:
        """Upload file to GCS"""
        try:
            blob = self.bucket.blob(remote_key)
            
            # Run synchronous GCS call in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: blob.upload_from_filename(str(local_filepath))
            )
            logger.info(f"Uploaded to GCS: gs://{self.bucket_name}/{remote_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload to GCS: {e}")
            return False
    
    async def file_exists(self, remote_key: str) -> bool:
        """Check if file exists in GCS"""
        try:
            blob = self.bucket.blob(remote_key)
            loop = asyncio.get_event_loop()
            exists = await loop.run_in_executor(None, blob.exists)
            return exists
        except Exception:
            return False


class CloudStorageManager:
    """Manages cloud storage operations for GTFS-RT files"""
    
    def __init__(self, provider: Optional[CloudStorageProvider] = None):
        """
        Initialize cloud storage manager
        
        Args:
            provider: Cloud storage provider instance (S3 or GCS)
        """
        self.provider = provider
        self.stats = {
            "total_uploads": 0,
            "successful_uploads": 0,
            "failed_uploads": 0,
        }
    
    @classmethod
    def from_config(cls) -> "CloudStorageManager":
        """
        Create CloudStorageManager from environment variables
        
        Environment variables:
        - CLOUD_STORAGE_TYPE: "s3" or "gcs"
        - S3_BUCKET_NAME: S3 bucket name (if using S3)
        - AWS_ACCESS_KEY_ID: AWS access key (if using S3)
        - AWS_SECRET_ACCESS_KEY: AWS secret key (if using S3)
        - AWS_REGION: AWS region (default: us-east-1)
        - GCS_BUCKET_NAME: GCS bucket name (if using GCS)
        - GOOGLE_APPLICATION_CREDENTIALS: Path to GCS credentials JSON
        """
        storage_type = os.getenv("CLOUD_STORAGE_TYPE", "").lower()
        
        if storage_type == "s3":
            bucket_name = os.getenv("S3_BUCKET_NAME")
            if not bucket_name:
                logger.warning("S3_BUCKET_NAME not set, cloud storage disabled")
                return cls(provider=None)
            
            provider = S3StorageProvider(
                bucket_name=bucket_name,
                region=os.getenv("AWS_REGION", "us-east-1"),
            )
            return cls(provider=provider)
        
        elif storage_type == "gcs":
            bucket_name = os.getenv("GCS_BUCKET_NAME")
            if not bucket_name:
                logger.warning("GCS_BUCKET_NAME not set, cloud storage disabled")
                return cls(provider=None)
            
            credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            provider = GCSStorageProvider(
                bucket_name=bucket_name,
                credentials_path=credentials_path,
            )
            return cls(provider=provider)
        
        else:
            logger.info("No cloud storage configured (set CLOUD_STORAGE_TYPE)")
            return cls(provider=None)
    
    def is_enabled(self) -> bool:
        """Check if cloud storage is enabled"""
        return self.provider is not None
    
    def _get_daily_path(self, filename: str) -> str:
        """
        Generate daily path for file storage
        
        Format: YYYY/MM/DD/filename
        Example: 2025/11/18/vehicle_positions_20251118_193823.json
        """
        now = datetime.utcnow()
        date_path = f"{now.year:04d}/{now.month:02d}/{now.day:02d}"
        return f"{date_path}/{filename}"
    
    async def upload_gtfs_file(self, local_filepath: Path) -> bool:
        """
        Upload a GTFS-RT file to cloud storage
        
        Args:
            local_filepath: Local file path to upload
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled():
            return False
        
        if not local_filepath.exists():
            logger.error(f"File does not exist: {local_filepath}")
            return False
        
        # Generate remote key with daily path
        remote_key = self._get_daily_path(local_filepath.name)
        
        self.stats["total_uploads"] += 1
        
        success = await self.provider.upload_file(local_filepath, remote_key)
        
        if success:
            self.stats["successful_uploads"] += 1
        else:
            self.stats["failed_uploads"] += 1
        
        return success
    
    async def upload_pair(self, pb_filepath: Path, json_filepath: Optional[Path] = None) -> Dict[str, bool]:
        """
        Upload both .pb and .json files for a feed
        
        Args:
            pb_filepath: Path to Protocol Buffer file
            json_filepath: Optional path to JSON file
            
        Returns:
            Dictionary with upload results
        """
        results = {}
        
        if pb_filepath.exists():
            results["pb"] = await self.upload_gtfs_file(pb_filepath)
        
        if json_filepath and json_filepath.exists():
            results["json"] = await self.upload_gtfs_file(json_filepath)
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cloud storage statistics"""
        stats = self.stats.copy()
        stats["enabled"] = self.is_enabled()
        if self.provider:
            stats["provider"] = type(self.provider).__name__
        return stats

