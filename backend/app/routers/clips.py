"""
Clips Router

This module provides REST API endpoints for managing video clips stored in Azure Blob Storage.
It handles clip access, metadata retrieval, and secure URL generation.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import logging

from ..auth import get_current_user, User
from ..database import get_db
from ..models import Clip, Video
from ..services.clip_storage import get_clip_storage_service, ClipStorageService
from ..services.azure_storage import get_azure_storage_service, AzureBlobStorageService
from ..schemas import ClipResponse, ClipMetadataResponse, ClipAccessUrlResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/clips/{clip_id}", response_model=ClipResponse)
async def get_clip(
    clip_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get clip information by ID
    
    Args:
        clip_id: UUID of the clip
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Clip information with metadata
    """
    try:
        # Get clip from database
        query = select(Clip).where(Clip.id == clip_id)
        result = await db.execute(query)
        clip = result.scalar_one_or_none()
        
        if not clip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clip not found"
            )
        
        # Verify user has access to this clip
        video_query = select(Video).where(Video.id == clip.video_id)
        video_result = await db.execute(video_query)
        video = video_result.scalar_one_or_none()
        
        if not video or video.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this clip"
            )
        
        return ClipResponse(
            id=clip.id,
            video_id=clip.video_id,
            blob_url=clip.blob_url,
            thumbnail_url=clip.thumbnail_url,
            title=clip.title,
            start_time=clip.start_time,
            end_time=clip.end_time,
            duration=clip.duration,
            file_size=clip.file_size,
            created_at=clip.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get clip {clip_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve clip"
        )


@router.get("/clips/{clip_id}/access-url", response_model=ClipAccessUrlResponse)
async def get_clip_access_url(
    clip_id: str,
    expiry_hours: int = Query(24, ge=1, le=168, description="URL expiry time in hours"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    clip_storage: ClipStorageService = Depends(get_clip_storage_service)
):
    """
    Generate a temporary access URL for a clip
    
    Args:
        clip_id: UUID of the clip
        expiry_hours: Number of hours until the URL expires (max 168 hours/7 days)
        current_user: Authenticated user
        db: Database session
        clip_storage: Clip storage service
        
    Returns:
        Temporary access URL for the clip
    """
    try:
        # Get clip from database
        query = select(Clip).where(Clip.id == clip_id)
        result = await db.execute(query)
        clip = result.scalar_one_or_none()
        
        if not clip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clip not found"
            )
        
        # Verify user has access to this clip
        video_query = select(Video).where(Video.id == clip.video_id)
        video_result = await db.execute(video_query)
        video = video_result.scalar_one_or_none()
        
        if not video or video.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this clip"
            )
        
        # Generate access URL
        access_url = await clip_storage.generate_clip_access_url(
            clip=clip,
            expiry_hours=expiry_hours
        )
        
        return ClipAccessUrlResponse(
            clip_id=clip.id,
            access_url=access_url,
            expires_in_hours=expiry_hours
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate access URL for clip {clip_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate access URL"
        )


@router.get("/clips/{clip_id}/metadata", response_model=ClipMetadataResponse)
async def get_clip_metadata(
    clip_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    clip_storage: ClipStorageService = Depends(get_clip_storage_service)
):
    """
    Get detailed metadata for a clip
    
    Args:
        clip_id: UUID of the clip
        current_user: Authenticated user
        db: Database session
        clip_storage: Clip storage service
        
    Returns:
        Detailed clip metadata including Azure Blob Storage information
    """
    try:
        # Get clip from database
        query = select(Clip).where(Clip.id == clip_id)
        result = await db.execute(query)
        clip = result.scalar_one_or_none()
        
        if not clip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clip not found"
            )
        
        # Verify user has access to this clip
        video_query = select(Video).where(Video.id == clip.video_id)
        video_result = await db.execute(video_query)
        video = video_result.scalar_one_or_none()
        
        if not video or video.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this clip"
            )
        
        # Get metadata from Azure Blob Storage
        metadata = await clip_storage.get_clip_metadata(clip)
        
        return ClipMetadataResponse(**metadata)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get metadata for clip {clip_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve clip metadata"
        )


@router.delete("/clips/{clip_id}")
async def delete_clip(
    clip_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    clip_storage: ClipStorageService = Depends(get_clip_storage_service)
):
    """
    Delete a clip from both Azure Blob Storage and database
    
    Args:
        clip_id: UUID of the clip to delete
        current_user: Authenticated user
        db: Database session
        clip_storage: Clip storage service
        
    Returns:
        Success message
    """
    try:
        # Get clip from database
        query = select(Clip).where(Clip.id == clip_id)
        result = await db.execute(query)
        clip = result.scalar_one_or_none()
        
        if not clip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clip not found"
            )
        
        # Verify user has access to this clip
        video_query = select(Video).where(Video.id == clip.video_id)
        video_result = await db.execute(video_query)
        video = video_result.scalar_one_or_none()
        
        if not video or video.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this clip"
            )
        
        # Delete clip from Azure Blob Storage and database
        success = await clip_storage.delete_clip(clip, db)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete clip"
            )
        
        return {"message": "Clip deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete clip {clip_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete clip"
        )


@router.get("/videos/{video_id}/clips", response_model=List[ClipResponse])
async def get_video_clips(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    clip_storage: ClipStorageService = Depends(get_clip_storage_service)
):
    """
    Get all clips for a specific video
    
    Args:
        video_id: UUID of the video
        current_user: Authenticated user
        db: Database session
        clip_storage: Clip storage service
        
    Returns:
        List of clips for the video
    """
    try:
        # Verify user has access to this video
        video_query = select(Video).where(Video.id == video_id)
        video_result = await db.execute(video_query)
        video = video_result.scalar_one_or_none()
        
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        if video.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this video"
            )
        
        # Get clips for the video
        clips = await clip_storage.list_clips_for_video(video_id, db)
        
        return [
            ClipResponse(
                id=clip.id,
                video_id=clip.video_id,
                blob_url=clip.blob_url,
                thumbnail_url=clip.thumbnail_url,
                title=clip.title,
                start_time=clip.start_time,
                end_time=clip.end_time,
                duration=clip.duration,
                file_size=clip.file_size,
                created_at=clip.created_at
            )
            for clip in clips
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get clips for video {video_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve video clips"
        )


@router.post("/migrate-clips")
async def migrate_clips_to_azure(
    local_clips_dir: str = Query(..., description="Local directory containing clips to migrate"),
    batch_size: int = Query(10, ge=1, le=50, description="Number of clips to process per batch"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    clip_storage: ClipStorageService = Depends(get_clip_storage_service)
):
    """
    Migrate existing local clips to Azure Blob Storage
    
    Args:
        local_clips_dir: Directory containing local clip files
        batch_size: Number of clips to process per batch
        current_user: Authenticated user (must be admin)
        db: Database session
        clip_storage: Clip storage service
        
    Returns:
        Migration status
    """
    try:
        # This is an admin operation - add role check when roles are implemented
        # For now, we'll allow any authenticated user
        
        logger.info(f"Starting clip migration from {local_clips_dir} for user {current_user.id}")
        
        await clip_storage.migrate_local_clips_to_azure(
            local_clips_dir=local_clips_dir,
            db=db,
            batch_size=batch_size
        )
        
        return {"message": "Clip migration completed successfully"}
        
    except Exception as e:
        logger.error(f"Failed to migrate clips: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to migrate clips: {str(e)}"
        ) 