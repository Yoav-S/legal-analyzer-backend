"""
File storage service for S3 and Cloudflare R2.
"""
import aiofiles
from typing import BinaryIO, Optional
from pathlib import Path
import uuid

from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class StorageService:
    """Service for file storage (S3 or R2)."""
    
    def __init__(self):
        self.storage_type = settings.STORAGE_TYPE
        self.bucket_name = settings.S3_BUCKET_NAME if self.storage_type == "s3" else settings.R2_BUCKET_NAME
        
        if self.storage_type == "s3":
            import boto3
            from botocore.config import Config
            
            if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
                raise ValueError("AWS credentials not configured")
            
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
                config=Config(signature_version="s3v4"),
            )
        elif self.storage_type == "r2":
            import boto3
            from botocore.config import Config
            
            if not settings.R2_ACCESS_KEY_ID or not settings.R2_SECRET_ACCESS_KEY:
                raise ValueError("R2 credentials not configured")
            
            self.s3_client = boto3.client(
                "s3",
                endpoint_url=settings.R2_ENDPOINT_URL,
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                region_name="auto",
                config=Config(signature_version="s3v4"),
            )
        else:
            raise ValueError(f"Unsupported storage type: {self.storage_type}")
    
    async def upload_file(
        self,
        file_content: bytes,
        file_name: str,
        user_id: str,
        folder: str = "documents",
    ) -> str:
        """
        Upload file to storage.
        
        Args:
            file_content: File content as bytes
            file_name: Original file name
            user_id: User ID for folder organization
            folder: Storage folder (default: "documents")
            
        Returns:
            File URL/path in storage
        """
        import asyncio
        
        # Generate unique file key
        file_extension = Path(file_name).suffix
        unique_id = str(uuid.uuid4())
        file_key = f"{folder}/{user_id}/{unique_id}{file_extension}"
        
        try:
            # Upload to S3/R2 (boto3 is sync, so we run in executor)
            def _upload():
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=file_key,
                    Body=file_content,
                    ContentType=self._get_content_type(file_extension),
                )
            
            await asyncio.to_thread(_upload)
            
            # Generate URL
            if self.storage_type == "s3":
                file_url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{file_key}"
            else:
                # R2 public URL (adjust based on your R2 setup)
                file_url = f"https://{self.bucket_name}.r2.cloudflarestorage.com/{file_key}"
            
            logger.info(f"File uploaded: {file_key}")
            return file_url
            
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise
    
    async def download_file(self, file_key: str) -> bytes:
        """
        Download file from storage.
        
        Args:
            file_key: File key/path in storage
            
        Returns:
            File content as bytes
        """
        try:
            import asyncio
            # boto3 is sync, so we run in executor
            def _download():
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_key)
                return response["Body"].read()
            
            return await asyncio.to_thread(_download)
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            raise
    
    async def delete_file(self, file_key: str) -> bool:
        """
        Delete file from storage.
        
        Args:
            file_key: File key/path in storage
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_key)
            logger.info(f"File deleted: {file_key}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    def _get_content_type(self, extension: str) -> str:
        """Get content type from file extension."""
        content_types = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
            ".txt": "text/plain",
        }
        return content_types.get(extension.lower(), "application/octet-stream")
    
    def extract_file_key_from_url(self, file_url: str) -> str:
        """
        Extract file key from storage URL.
        
        Args:
            file_url: Full file URL
            
        Returns:
            File key/path
        """
        # Extract key from URL (remove domain and bucket)
        if "s3.amazonaws.com" in file_url or "r2.cloudflarestorage.com" in file_url:
            parts = file_url.split("/")
            # Find the bucket name index and get everything after
            try:
                bucket_index = parts.index(self.bucket_name)
                return "/".join(parts[bucket_index + 1:])
            except ValueError:
                # Fallback: try to extract from common patterns
                if "/" in file_url:
                    return file_url.split(f"{self.bucket_name}/")[-1]
        return file_url

