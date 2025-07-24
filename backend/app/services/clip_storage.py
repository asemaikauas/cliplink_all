"""
Clip Storage Service

This module handles the storage and retrieval of video clips using Azure Blob Storage.
It integrates with the existing video processing pipeline to automatically upload
processed clips to Azure Blob Storage.
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from uuid import uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from .azure_storage import AzureBlobStorageService, get_azure_storage_service
from ..models import Clip, Video
from ..exceptions import FileUploadError, FileDownloadError

logger = logging.getLogger(__name__)


class ClipStorageService:
    """
    Service for managing video clips in Azure Blob Storage
    """
    
    def __init__(self, azure_storage: AzureBlobStorageService):
        self.azure_storage = azure_storage
        self.temp_dir = Path(os.getenv("TEMP_DIR", "/tmp/cliplink"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    async def upload_clip(
        self,
        clip_file_path: str,
        video_id: str,
        start_time: float,
        end_time: float,
        db: AsyncSession,
        thumbnail_path: Optional[str] = None,
        title: Optional[str] = None
    ) -> Clip:
        """
        Upload a video clip to Azure Blob Storage and save metadata to database
        
        Args:
            clip_file_path: Local path to the clip file
            video_id: ID of the parent video
            start_time: Start time of the clip in seconds
            end_time: End time of the clip in seconds
            db: Database session
            thumbnail_path: Optional path to thumbnail image
            
        Returns:
            Clip database object with Azure Blob Storage URLs
        """
        try:
            # Generate unique blob name
            clip_id = str(uuid4())
            file_extension = Path(clip_file_path).suffix
            blob_name = f"{video_id}/{clip_id}{file_extension}"
            
            # Metadata for the clip
            metadata = {
                "video_id": video_id,
                "clip_id": clip_id,
                "start_time": str(start_time),
                "end_time": str(end_time),
                "duration": str(end_time - start_time),
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Upload clip to Azure Blob Storage
            logger.info(f"Uploading clip {clip_id} to Azure Blob Storage...")
            clip_blob_url = await self.azure_storage.upload_file(
                file_path=clip_file_path,
                blob_name=blob_name,
                container_type="clips",
                metadata=metadata
            )
            
            # Upload thumbnail if provided
            thumbnail_blob_url = None
            if thumbnail_path and os.path.exists(thumbnail_path):
                thumbnail_extension = Path(thumbnail_path).suffix
                thumbnail_blob_name = f"{video_id}/{clip_id}_thumbnail{thumbnail_extension}"
                
                logger.info(f"Uploading thumbnail for clip {clip_id}...")
                thumbnail_blob_url = await self.azure_storage.upload_file(
                    file_path=thumbnail_path,
                    blob_name=thumbnail_blob_name,
                    container_type="thumbnails",
                    metadata=metadata
                )
            
            # Get file size
            file_size = os.path.getsize(clip_file_path)
            
            # Create database record
            clip = Clip(
                id=clip_id,
                video_id=video_id,
                blob_url=clip_blob_url,
                thumbnail_url=thumbnail_blob_url,
                title=title,
                start_time=start_time,
                end_time=end_time,
                duration=end_time - start_time,
                file_size=file_size
            )
            
            db.add(clip)
            await db.commit()
            await db.refresh(clip)
            
            logger.info(f"Successfully uploaded clip {clip_id} to Azure Blob Storage")
            return clip
            
        except Exception as e:
            logger.error(f"Failed to upload clip: {str(e)}")
            await db.rollback()
            raise FileUploadError(f"Failed to upload clip to Azure Blob Storage: {str(e)}")
    
    async def download_clip(
        self,
        clip: Clip,
        download_dir: Optional[str] = None
    ) -> str:
        """
        Download a clip from Azure Blob Storage to local storage
        
        Args:
            clip: Clip database object
            download_dir: Directory to download to (default: temp directory)
            
        Returns:
            Local path to downloaded file
        """
        try:
            if not download_dir:
                download_dir = self.temp_dir
            
            # Create download directory
            Path(download_dir).mkdir(parents=True, exist_ok=True)
            
            # Generate local filename
            file_extension = Path(clip.blob_url).suffix
            local_filename = f"{clip.id}{file_extension}"
            local_path = Path(download_dir) / local_filename
            
            # Download from Azure Blob Storage
            logger.info(f"Downloading clip {clip.id} from Azure Blob Storage...")
            await self.azure_storage.download_file(
                blob_url=clip.blob_url,
                download_path=str(local_path)
            )
            
            logger.info(f"Successfully downloaded clip {clip.id} to {local_path}")
            return str(local_path)
            
        except Exception as e:
            logger.error(f"Failed to download clip {clip.id}: {str(e)}")
            raise FileDownloadError(f"Failed to download clip from Azure Blob Storage: {str(e)}")
    
    async def delete_clip(
        self,
        clip: Clip,
        db: AsyncSession
    ) -> bool:
        """
        Delete a clip from both Azure Blob Storage and database
        
        Args:
            clip: Clip database object
            db: Database session
            
        Returns:
            True if deletion was successful
        """
        try:
            # Delete from Azure Blob Storage
            logger.info(f"Deleting clip {clip.id} from Azure Blob Storage...")
            
            # Delete main clip file
            await self.azure_storage.delete_file(clip.blob_url)
            
            # Delete thumbnail if it exists
            if clip.thumbnail_url:
                await self.azure_storage.delete_file(clip.thumbnail_url)
            
            # Delete from database
            await db.delete(clip)
            await db.commit()
            
            logger.info(f"Successfully deleted clip {clip.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete clip {clip.id}: {str(e)}")
            await db.rollback()
            return False
    
    async def generate_clip_access_url(
        self,
        clip: Clip,
        expiry_hours: int = 24
    ) -> str:
        """
        Generate a temporary access URL for a clip
        
        Args:
            clip: Clip database object
            expiry_hours: Number of hours until URL expires
            
        Returns:
            Temporary access URL
        """
        try:
            sas_url = await self.azure_storage.generate_sas_url(
                blob_url=clip.blob_url,
                expiry_hours=expiry_hours,
                permissions="r"
            )
            
            logger.info(f"Generated access URL for clip {clip.id} (expires in {expiry_hours}h)")
            return sas_url
            
        except Exception as e:
            logger.error(f"Failed to generate access URL for clip {clip.id}: {str(e)}")
            raise
    
    async def get_clip_metadata(
        self,
        clip: Clip
    ) -> Dict[str, Any]:
        """
        Get detailed metadata for a clip from Azure Blob Storage
        
        Args:
            clip: Clip database object
            
        Returns:
            Metadata dictionary
        """
        try:
            metadata = await self.azure_storage.get_blob_metadata(clip.blob_url)
            
            # Combine with database metadata
            combined_metadata = {
                "clip_id": str(clip.id),
                "video_id": str(clip.video_id),
                "start_time": clip.start_time,
                "end_time": clip.end_time,
                "duration": clip.duration,
                "file_size": clip.file_size,
                "created_at": clip.created_at.isoformat(),
                "blob_url": clip.blob_url,
                "thumbnail_url": clip.thumbnail_url,
                "azure_metadata": metadata
            }
            
            return combined_metadata
            
        except Exception as e:
            logger.error(f"Failed to get metadata for clip {clip.id}: {str(e)}")
            raise
    
    async def list_clips_for_video(
        self,
        video_id: str,
        db: AsyncSession
    ) -> List[Clip]:
        """
        List all clips for a specific video
        
        Args:
            video_id: ID of the video
            db: Database session
            
        Returns:
            List of Clip objects
        """
        try:
            from sqlalchemy import select
            
            query = select(Clip).where(Clip.video_id == video_id).order_by(Clip.start_time)
            result = await db.execute(query)
            clips = result.scalars().all()
            
            logger.info(f"Found {len(clips)} clips for video {video_id}")
            return clips
            
        except Exception as e:
            logger.error(f"Failed to list clips for video {video_id}: {str(e)}")
            raise
    
    async def cleanup_temp_files(self, older_than_hours: int = 24):
        """
        Clean up temporary files older than specified hours
        
        Args:
            older_than_hours: Remove files older than this many hours
        """
        try:
            current_time = datetime.now()
            cutoff_time = current_time.timestamp() - (older_than_hours * 3600)
            
            cleaned_count = 0
            for file_path in self.temp_dir.glob("*"):
                if file_path.is_file():
                    if file_path.stat().st_mtime < cutoff_time:
                        file_path.unlink()
                        cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} temporary files")
            
        except Exception as e:
            logger.error(f"Failed to cleanup temp files: {str(e)}")
    
    async def upload_temp_video_for_processing(
        self,
        video_file_path: str,
        video_id: str,
        expiry_hours: int = 24
    ) -> str:
        """
        Upload a YouTube video temporarily for processing
        
        Args:
            video_file_path: Local path to the downloaded video
            video_id: Video ID
            expiry_hours: Hours until automatic deletion
            
        Returns:
            Azure Blob Storage URL for temporary access
        """
        try:
            blob_url = await self.azure_storage.upload_temp_video(
                file_path=video_file_path,
                video_id=video_id,
                expiry_hours=expiry_hours
            )
            
            logger.info(f"Uploaded temporary video {video_id} for processing")
            return blob_url
            
        except Exception as e:
            logger.error(f"Failed to upload temporary video {video_id}: {str(e)}")
            raise FileUploadError(f"Failed to upload temporary video: {str(e)}")
    
    async def cleanup_temp_video_after_processing(
        self,
        video_id: str,
        db: AsyncSession
    ) -> bool:
        """
        Clean up temporary video files after clip generation is complete
        
        Args:
            video_id: Video ID to clean up
            db: Database session
            
        Returns:
            True if cleanup was successful
        """
        try:
            from sqlalchemy import select
            
            # Check if all clips for this video are successfully created
            query = select(Clip).where(Clip.video_id == video_id)
            result = await db.execute(query)
            clips = result.scalars().all()
            
            if not clips:
                logger.warning(f"No clips found for video {video_id}, still cleaning up temp video")
            
            # Delete temporary video files
            success = await self.azure_storage.delete_temp_video(video_id)
            
            if success:
                logger.info(f"Successfully cleaned up temporary video {video_id}")
                
                # Update video status if needed
                video_query = select(Video).where(Video.id == video_id)
                video_result = await db.execute(video_query)
                video = video_result.scalar_one_or_none()
                
                if video:
                    logger.info(f"Video {video_id} processing and cleanup completed")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to cleanup temporary video {video_id}: {str(e)}")
            return False
    
    async def schedule_temp_video_cleanup(self):
        """
        Run cleanup of expired temporary videos (for scheduled tasks)
        """
        try:
            deleted_count = await self.azure_storage.cleanup_expired_temp_videos()
            logger.info(f"Scheduled cleanup completed: {deleted_count} expired videos deleted")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Scheduled cleanup failed: {str(e)}")
            return 0
    
    async def migrate_local_clips_to_azure(
        self,
        local_clips_dir: str,
        db: AsyncSession,
        batch_size: int = 10
    ):
        """
        Migrate existing local clips to Azure Blob Storage
        
        Args:
            local_clips_dir: Directory containing local clip files
            db: Database session
            batch_size: Number of files to process in each batch
        """
        try:
            from sqlalchemy import select
            
            logger.info("Starting migration of local clips to Azure Blob Storage...")
            
            # Find all clips that might need migration (those with local file paths)
            query = select(Clip).where(Clip.blob_url.like("file://%") | Clip.blob_url.like("/%"))
            result = await db.execute(query)
            clips_to_migrate = result.scalars().all()
            
            logger.info(f"Found {len(clips_to_migrate)} clips to migrate")
            
            migrated_count = 0
            for i in range(0, len(clips_to_migrate), batch_size):
                batch = clips_to_migrate[i:i + batch_size]
                
                for clip in batch:
                    try:
                        # Construct local file path
                        local_file_path = Path(local_clips_dir) / f"{clip.id}.mp4"
                        
                        if not local_file_path.exists():
                            logger.warning(f"Local file not found for clip {clip.id}: {local_file_path}")
                            continue
                        
                        # Upload to Azure
                        blob_name = f"{clip.video_id}/{clip.id}.mp4"
                        blob_url = await self.azure_storage.upload_file(
                            file_path=str(local_file_path),
                            blob_name=blob_name,
                            container_type="clips"
                        )
                        
                        # Update database
                        clip.blob_url = blob_url
                        clip.file_size = local_file_path.stat().st_size
                        
                        migrated_count += 1
                        logger.info(f"Migrated clip {clip.id} to Azure Blob Storage")
                        
                    except Exception as e:
                        logger.error(f"Failed to migrate clip {clip.id}: {str(e)}")
                        continue
                
                # Commit batch
                await db.commit()
                logger.info(f"Migrated batch {i//batch_size + 1}/{(len(clips_to_migrate) + batch_size - 1)//batch_size}")
                
                # Short delay between batches
                await asyncio.sleep(1)
            
            logger.info(f"Migration completed. Successfully migrated {migrated_count} clips")
            
        except Exception as e:
            logger.error(f"Failed to migrate local clips: {str(e)}")
            await db.rollback()
            raise


async def get_clip_storage_service() -> ClipStorageService:
    """Dependency injection for Clip Storage service"""
    azure_storage = await get_azure_storage_service()
    return ClipStorageService(azure_storage) 