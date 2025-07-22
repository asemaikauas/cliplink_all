"""
Azure Blob Storage Service

This module provides async operations for uploading, downloading, and managing
video files and clips in Azure Blob Storage.
"""

import os
import asyncio
import logging
from typing import Optional, List, BinaryIO, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
import aiofiles
import aiohttp

from dotenv import load_dotenv 

load_dotenv()

from azure.storage.blob.aio import BlobServiceClient
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from azure.identity.aio import DefaultAzureCredential
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError

from ..exceptions import FileUploadError, FileDownloadError

logger = logging.getLogger(__name__)


class AzureBlobStorageService:
    """
    Service for managing files in Azure Blob Storage
    """
    
    def __init__(self):
        self.account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        self.account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
        self.connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "cliplink")
        
        # Initialize blob service client
        self.blob_service_client = None
        self._initialize_client()
        
        # Container names for different file types (matching existing Azure containers)
        base_name = self.container_name.lower()  # Keep original name format
        self.containers = {
            "temp_videos": f"{base_name}-temp-videos",  # Temporary storage for processing (if needed)
            "clips": f"{base_name}-clips",              # Permanent clip storage → onelinkdb-clips
            "thumbnails": f"{base_name}-thumbnails",    # Permanent thumbnail storage → onelinkdb-thumbnails
            "temp": f"{base_name}-temp"                 # General temporary files (if needed)
        }
    
    def _initialize_client(self):
        """Initialize Azure Blob Storage client"""
        try:
            if self.connection_string:
                self.blob_service_client = BlobServiceClient.from_connection_string(
                    self.connection_string
                )
            elif self.account_name and self.account_key:
                account_url = f"https://{self.account_name}.blob.core.windows.net"
                self.blob_service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=self.account_key
                )
            else:
                # Use DefaultAzureCredential for managed identity
                account_url = f"https://{self.account_name}.blob.core.windows.net"
                credential = DefaultAzureCredential()
                self.blob_service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=credential
                )
                
            logger.info(f"Azure Blob Storage client initialized for account: {self.account_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure Blob Storage client: {str(e)}")
            raise
    
    async def ensure_containers_exist(self):
        """Ensure all required containers exist"""
        try:
            for container_type, container_name in self.containers.items():
                try:
                    await self.blob_service_client.create_container(container_name)
                    logger.info(f"Created container: {container_name}")
                except ResourceExistsError:
                    logger.debug(f"Container already exists: {container_name}")
                except Exception as e:
                    logger.error(f"Error creating container {container_name}: {str(e)}")
                    raise
        except Exception as e:
            logger.error(f"Failed to ensure containers exist: {str(e)}")
            raise
    
    def _sanitize_blob_name(self, blob_name: str) -> str:
        """
        Sanitize blob name for Azure Blob Storage compliance
        
        Azure Blob Storage naming requirements:
        - Must be 1-1024 characters long
        - Can contain letters, numbers, and these characters: . - _ / 
        - Cannot contain spaces or other special characters
        - Must be URL-safe
        """
        import urllib.parse
        import unicodedata
        import re
        
        # Step 1: Handle Unicode characters (like Cyrillic) by converting to ASCII
        # This converts accented characters to their ASCII equivalents
        try:
            # Normalize Unicode and convert to ASCII
            sanitized = unicodedata.normalize('NFKD', blob_name)
            sanitized = sanitized.encode('ascii', 'ignore').decode('ascii')
        except Exception:
            # Fallback: just remove non-ASCII characters
            sanitized = ''.join(char for char in blob_name if ord(char) < 128)
        
        # Step 2: Replace problematic characters
        sanitized = sanitized.replace("\\", "/")  # Normalize path separators
        sanitized = sanitized.replace(" ", "_")   # Replace spaces with underscores
        
        # Step 3: Remove any remaining problematic characters
        # Keep only: letters, numbers, dots, hyphens, underscores, forward slashes
        sanitized = re.sub(r'[^a-zA-Z0-9.\-_/]', '_', sanitized)
        
        # Step 4: Clean up multiple consecutive underscores/separators
        sanitized = re.sub(r'[_]{2,}', '_', sanitized)  # Multiple underscores -> single
        sanitized = re.sub(r'[/]{2,}', '/', sanitized)  # Multiple slashes -> single
        
        # Step 5: Remove leading/trailing separators
        sanitized = sanitized.strip('/_')
        
        # Step 6: Ensure it's not empty and not too long
        if not sanitized:
            sanitized = "unnamed_file"
        
        # Limit to 1000 characters (Azure limit is 1024, leaving some buffer)
        if len(sanitized) > 1000:
            # Keep the extension if possible
            if '.' in sanitized:
                name_part, ext_part = sanitized.rsplit('.', 1)
                max_name_length = 1000 - len(ext_part) - 1  # -1 for the dot
                sanitized = name_part[:max_name_length] + '.' + ext_part
            else:
                sanitized = sanitized[:1000]
        
        # Step 7: Final URL encoding for any remaining edge cases
        sanitized = urllib.parse.quote(sanitized, safe='/./_-')
        
        return sanitized
    
    async def upload_file(
        self, 
        file_path: str, 
        blob_name: str, 
        container_type: str = "clips",
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Upload a file to Azure Blob Storage
        
        Args:
            file_path: Local path to the file to upload
            blob_name: Name for the blob in Azure Storage
            container_type: Type of container (videos, clips, thumbnails, temp)
            content_type: MIME type of the file
            metadata: Optional metadata to attach to the blob
            
        Returns:
            Azure Blob Storage URL for the uploaded file
        """
        try:
            container_name = self.containers[container_type]
            # Sanitize blob name for Azure compliance
            original_blob_name = blob_name
            blob_name = self._sanitize_blob_name(blob_name)
            
            logger.info(f"🔄 Uploading to Azure: container='{container_name}', blob='{blob_name}'")
            if original_blob_name != blob_name:
                logger.info(f"📝 Blob name sanitized: '{original_blob_name}' → '{blob_name}'")
            
            # Ensure container exists
            await self.ensure_containers_exist()
            
            # Determine content type if not provided
            if not content_type:
                content_type = self._get_content_type(file_path)
            
            # Upload file
            async with aiofiles.open(file_path, 'rb') as file:
                blob_client = self.blob_service_client.get_blob_client(
                    container=container_name,
                    blob=blob_name
                )
                
                file_data = await file.read()
                
                await blob_client.upload_blob(
                    file_data,
                    content_type=content_type,
                    metadata=metadata,
                    overwrite=True
                )
            
            # Generate the blob URL
            blob_url = f"https://{self.account_name}.blob.core.windows.net/{container_name}/{blob_name}"
            
            logger.info(f"Successfully uploaded {file_path} to {blob_url}")
            return blob_url
            
        except Exception as e:
            error_details = {
                "file_path": file_path,
                "original_blob_name": original_blob_name,
                "sanitized_blob_name": blob_name,
                "container_name": container_name,
                "container_type": container_type,
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
            
            logger.error(f"❌ Azure upload failed with details: {error_details}")
            
            # Check for common issues
            if "400" in str(e) and "Bad Request" in str(e):
                logger.error(f"🔍 Azure 400 Error Analysis:")
                logger.error(f"   Original name: '{original_blob_name}'")
                logger.error(f"   Sanitized name: '{blob_name}'")
                logger.error(f"   Container: '{container_name}'")
                logger.error(f"   File exists: {Path(file_path).exists()}")
                logger.error(f"   File size: {Path(file_path).stat().st_size if Path(file_path).exists() else 'N/A'} bytes")
                
                # Additional blob name validation
                if len(blob_name) == 0:
                    logger.error(f"   ❌ Blob name is empty after sanitization!")
                elif len(blob_name) > 1024:
                    logger.error(f"   ❌ Blob name too long: {len(blob_name)} characters")
                elif blob_name.startswith('/') or blob_name.endswith('/'):
                    logger.error(f"   ❌ Blob name has invalid leading/trailing slashes")
                else:
                    logger.error(f"   ✅ Blob name appears valid, issue might be elsewhere")
            
            raise FileUploadError(f"Failed to upload file to Azure Blob Storage: {str(e)}")
    
    async def upload_stream(
        self,
        file_stream: BinaryIO,
        blob_name: str,
        container_type: str = "clips",
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Upload a file stream to Azure Blob Storage
        
        Args:
            file_stream: Binary file stream
            blob_name: Name for the blob in Azure Storage
            container_type: Type of container (videos, clips, thumbnails, temp)
            content_type: MIME type of the file
            metadata: Optional metadata to attach to the blob
            
        Returns:
            Azure Blob Storage URL for the uploaded file
        """
        try:
            container_name = self.containers[container_type]
            # Sanitize blob name for Azure compliance
            blob_name = self._sanitize_blob_name(blob_name)
            
            # Ensure container exists
            await self.ensure_containers_exist()
            
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            
            await blob_client.upload_blob(
                file_stream,
                content_type=content_type,
                metadata=metadata,
                overwrite=True
            )
            
            # Generate the blob URL
            blob_url = f"https://{self.account_name}.blob.core.windows.net/{container_name}/{blob_name}"
            
            logger.info(f"Successfully uploaded stream to {blob_url}")
            return blob_url
            
        except Exception as e:
            logger.error(f"Failed to upload stream: {str(e)}")
            raise FileUploadError(f"Failed to upload stream to Azure Blob Storage: {str(e)}")
    
    async def download_file(
        self,
        blob_url: str,
        download_path: str
    ) -> str:
        """
        Download a file from Azure Blob Storage
        
        Args:
            blob_url: Azure Blob Storage URL
            download_path: Local path where to save the file
            
        Returns:
            Local path to the downloaded file
        """
        try:
            # Parse blob URL to get container and blob name
            container_name, blob_name = self._parse_blob_url(blob_url)
            
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(download_path), exist_ok=True)
            
            # Download file
            async with aiofiles.open(download_path, 'wb') as file:
                download_stream = await blob_client.download_blob()
                async for chunk in download_stream.chunks():
                    await file.write(chunk)
            
            logger.info(f"Successfully downloaded {blob_url} to {download_path}")
            return download_path
            
        except Exception as e:
            logger.error(f"Failed to download file {blob_url}: {str(e)}")
            raise FileDownloadError(f"Failed to download file from Azure Blob Storage: {str(e)}")
    
    async def delete_file(self, blob_url: str) -> bool:
        """
        Delete a file from Azure Blob Storage
        
        Args:
            blob_url: Azure Blob Storage URL
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            container_name, blob_name = self._parse_blob_url(blob_url)
            
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            
            await blob_client.delete_blob()
            logger.info(f"Successfully deleted {blob_url}")
            return True
            
        except ResourceNotFoundError:
            logger.warning(f"Blob not found for deletion: {blob_url}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete file {blob_url}: {str(e)}")
            return False
    
    async def generate_sas_url(
        self,
        blob_url: str,
        expiry_hours: int = 24,
        permissions: str = "r"
    ) -> str:
        """
        Generate a SAS URL for temporary access to a blob
        
        Args:
            blob_url: Azure Blob Storage URL
            expiry_hours: Number of hours until the SAS expires
            permissions: Permissions for the SAS (r=read, w=write, d=delete)
            
        Returns:
            SAS URL for temporary access
        """
        try:
            container_name, blob_name = self._parse_blob_url(blob_url)
            
            # Define SAS permissions
            sas_permissions = BlobSasPermissions(
                read="r" in permissions,
                write="w" in permissions,
                delete="d" in permissions
            )
            
            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=self.account_name,
                container_name=container_name,
                blob_name=blob_name,
                account_key=self.account_key,
                permission=sas_permissions,
                expiry=datetime.utcnow() + timedelta(hours=expiry_hours)
            )
            
            # Construct SAS URL
            sas_url = f"{blob_url}?{sas_token}"
            
            logger.info(f"Generated SAS URL for {blob_url} (expires in {expiry_hours}h)")
            return sas_url
            
        except Exception as e:
            logger.error(f"Failed to generate SAS URL for {blob_url}: {str(e)}")
            raise
    
    async def list_blobs(
        self,
        container_type: str = "clips",
        prefix: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List blobs in a container
        
        Args:
            container_type: Type of container to list
            prefix: Optional prefix to filter blobs
            
        Returns:
            List of blob information dictionaries
        """
        try:
            container_name = self.containers[container_type]
            
            container_client = self.blob_service_client.get_container_client(container_name)
            
            blobs = []
            async for blob in container_client.list_blobs(name_starts_with=prefix):
                blob_info = {
                    "name": blob.name,
                    "size": blob.size,
                    "last_modified": blob.last_modified,
                    "content_type": blob.content_settings.content_type if blob.content_settings else None,
                    "url": f"https://{self.account_name}.blob.core.windows.net/{container_name}/{blob.name}"
                }
                blobs.append(blob_info)
            
            logger.info(f"Listed {len(blobs)} blobs from {container_name}")
            return blobs
            
        except Exception as e:
            logger.error(f"Failed to list blobs in {container_type}: {str(e)}")
            raise
    
    async def get_blob_metadata(self, blob_url: str) -> Dict[str, Any]:
        """
        Get metadata for a blob
        
        Args:
            blob_url: Azure Blob Storage URL
            
        Returns:
            Blob metadata dictionary
        """
        try:
            container_name, blob_name = self._parse_blob_url(blob_url)
            
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            
            properties = await blob_client.get_blob_properties()
            
            metadata = {
                "name": blob_name,
                "size": properties.size,
                "last_modified": properties.last_modified,
                "content_type": properties.content_settings.content_type if properties.content_settings else None,
                "metadata": properties.metadata,
                "url": blob_url
            }
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to get metadata for {blob_url}: {str(e)}")
            raise
    
    def _parse_blob_url(self, blob_url: str) -> tuple[str, str]:
        """
        Parse Azure Blob Storage URL to extract container and blob names
        
        Args:
            blob_url: Azure Blob Storage URL
            
        Returns:
            Tuple of (container_name, blob_name)
        """
        try:
            # Remove the account URL part
            url_parts = blob_url.replace(f"https://{self.account_name}.blob.core.windows.net/", "")
            
            # Split by first slash to get container and blob
            parts = url_parts.split("/", 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid blob URL format: {blob_url}")
            
            container_name, blob_name = parts
            return container_name, blob_name
            
        except Exception as e:
            logger.error(f"Failed to parse blob URL {blob_url}: {str(e)}")
            raise ValueError(f"Invalid blob URL format: {blob_url}")
    
    def _get_content_type(self, file_path: str) -> str:
        """
        Determine content type based on file extension
        
        Args:
            file_path: Path to the file
            
        Returns:
            MIME type string
        """
        extension = Path(file_path).suffix.lower()
        
        content_types = {
            ".mp4": "video/mp4",
            ".avi": "video/x-msvideo",
            ".mov": "video/quicktime",
            ".wmv": "video/x-ms-wmv",
            ".flv": "video/x-flv",
            ".webm": "video/webm",
            ".mkv": "video/x-matroska",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".webp": "image/webp",
            ".srt": "text/srt",
            ".vtt": "text/vtt",
            ".txt": "text/plain",
            ".json": "application/json"
        }
        
        return content_types.get(extension, "application/octet-stream")
    
    async def upload_temp_video(
        self,
        file_path: str,
        video_id: str,
        expiry_hours: int = 24
    ) -> str:
        """
        Upload a video temporarily for processing
        
        Args:
            file_path: Local path to the video file
            video_id: Video ID for naming
            expiry_hours: Hours until automatic deletion
            
        Returns:
            Azure Blob Storage URL for the temporary video
        """
        try:
            file_extension = Path(file_path).suffix
            blob_name = f"{video_id}/original{file_extension}"
            
            # Add metadata with expiry info
            metadata = {
                "video_id": video_id,
                "purpose": "temporary_processing",
                "expires_at": (datetime.utcnow() + timedelta(hours=expiry_hours)).isoformat(),
                "auto_delete": "true"
            }
            
            blob_url = await self.upload_file(
                file_path=file_path,
                blob_name=blob_name,
                container_type="temp_videos",
                metadata=metadata
            )
            
            logger.info(f"Uploaded temporary video {video_id} (expires in {expiry_hours}h)")
            return blob_url
            
        except Exception as e:
            logger.error(f"Failed to upload temporary video {video_id}: {str(e)}")
            raise
    
    async def cleanup_expired_temp_videos(self):
        """
        Clean up expired temporary videos
        """
        try:
            container_name = self.containers["temp_videos"]
            container_client = self.blob_service_client.get_container_client(container_name)
            
            current_time = datetime.utcnow()
            deleted_count = 0
            
            async for blob in container_client.list_blobs(include=['metadata']):
                try:
                    # Check if blob has expiry metadata
                    if blob.metadata and blob.metadata.get('expires_at'):
                        expires_at = datetime.fromisoformat(blob.metadata['expires_at'])
                        
                        if current_time > expires_at:
                            # Delete expired blob
                            blob_client = container_client.get_blob_client(blob.name)
                            await blob_client.delete_blob()
                            deleted_count += 1
                            logger.info(f"Deleted expired temporary video: {blob.name}")
                
                except Exception as e:
                    logger.warning(f"Failed to process blob {blob.name}: {str(e)}")
                    continue
            
            logger.info(f"Cleanup completed: deleted {deleted_count} expired temporary videos")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired videos: {str(e)}")
            return 0
    
    async def delete_temp_video(self, video_id: str) -> bool:
        """
        Delete temporary video after processing is complete
        
        Args:
            video_id: Video ID to delete
            
        Returns:
            True if deletion was successful
        """
        try:
            container_name = self.containers["temp_videos"]
            container_client = self.blob_service_client.get_container_client(container_name)
            
            # Find and delete all blobs for this video
            deleted_count = 0
            async for blob in container_client.list_blobs(name_starts_with=f"{video_id}/"):
                try:
                    blob_client = container_client.get_blob_client(blob.name)
                    await blob_client.delete_blob()
                    deleted_count += 1
                    logger.info(f"Deleted temporary video file: {blob.name}")
                except Exception as e:
                    logger.warning(f"Failed to delete {blob.name}: {str(e)}")
            
            if deleted_count > 0:
                logger.info(f"Successfully deleted {deleted_count} temporary files for video {video_id}")
                return True
            else:
                logger.warning(f"No temporary files found for video {video_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete temporary video {video_id}: {str(e)}")
            return False
    
    async def close(self):
        """Close the Azure Blob Storage client"""
        if self.blob_service_client:
            await self.blob_service_client.close()
            logger.info("Azure Blob Storage client closed")


# Global instance
azure_storage_service = AzureBlobStorageService()


async def get_azure_storage_service() -> AzureBlobStorageService:
    """Dependency injection for Azure Blob Storage service"""
    return azure_storage_service 