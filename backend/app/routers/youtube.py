"""YouTube video download API endpoints."""

import os
import logging
import time
import uuid
from typing import Optional, Dict, Any
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, HttpUrl

from app.services.youtube import (
    download_video, get_video_info, get_available_formats, 
    DownloadError, youtube_service
)
from app.exceptions import SubtitleError


logger = logging.getLogger(__name__)

router = APIRouter()


class YouTubeDownloadRequest(BaseModel):
    """Request model for YouTube video download."""
    youtube_url: HttpUrl = Field(..., description="YouTube video URL")
    quality: str = Field("best", description="Video quality: best, 8k, 4k, 1440p, 1080p, 720p")


class YouTubeVideoInfo(BaseModel):
    """YouTube video information response."""
    id: str
    title: str
    duration: Optional[int]
    view_count: Optional[int]
    upload_date: Optional[str]
    uploader: Optional[str]
    description: Optional[str]
    is_live: bool


class YouTubeDownloadResponse(BaseModel):
    """Response model for YouTube download."""
    task_id: str = Field(..., description="Unique download task identifier")
    success: bool = Field(..., description="Whether download was successful")
    video_info: YouTubeVideoInfo = Field(..., description="Video metadata")
    download_info: Dict[str, Any] = Field(..., description="Download details")
    file_path: str = Field(..., description="Path to downloaded video file")
    file_size_mb: float = Field(..., description="Downloaded file size in MB")
    quality_requested: str = Field(..., description="Requested quality level")
    actual_quality: Optional[str] = Field(None, description="Actual downloaded quality")
    download_time_ms: int = Field(..., description="Download time in milliseconds")


@router.post("/download", response_model=YouTubeDownloadResponse)
async def download_youtube_video(
    request: YouTubeDownloadRequest,
    background_tasks: BackgroundTasks = None
) -> YouTubeDownloadResponse:
    """Download YouTube video in specified quality.
    
    This endpoint downloads YouTube videos using Apify YouTube Video Downloader API
    for reliable, high-quality downloads up to 4K resolution.
    
    Args:
        request: Download request with YouTube URL and quality preference
        background_tasks: FastAPI background tasks for cleanup
        
    Returns:
        Download response with file information and metadata
        
    Raises:
        HTTPException: If download fails
    """
    task_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        url = str(request.youtube_url)
        quality = request.quality.lower()
        
        logger.info(f"🎬 Starting YouTube download (task_id: {task_id})")
        logger.info(f"📺 URL: {url}")
        logger.info(f"🎯 Quality: {quality}")
        
        # Validate quality parameter
        valid_qualities = ["best", "8k", "4k", "1440p", "1080p", "720p"]
        if quality not in valid_qualities:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid quality '{quality}'. Must be one of: {valid_qualities}"
            )
        
        # Get video information first
        try:
            video_info_dict = get_video_info(url)
        except Exception as e:
            logger.error(f"Failed to get video info (task_id: {task_id}): {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to get video information: {str(e)}"
            )
        
        # Check if video is available for download
        if video_info_dict.get('is_live', False):
            raise HTTPException(
                status_code=400,
                detail="Cannot download live streams"
            )
        
        # Download the video
        try:
            logger.info(f"📥 Starting download with quality: {quality}")
            video_path = await download_video(url, quality)
            
            if not video_path or not video_path.exists():
                raise HTTPException(
                    status_code=500,
                    detail="Download completed but file not found"
                )
                
        except DownloadError as e:
            logger.error(f"Download failed (task_id: {task_id}): {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Unexpected download error (task_id: {task_id}): {str(e)}")
            raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")
        
        # Upload video to Azure Blob Storage temporarily
        azure_blob_url = None
        try:
            logger.info(f"☁️ Uploading video to Azure Blob Storage...")
            
            # Import and get clip storage service
            from app.services.clip_storage import get_clip_storage_service
            clip_storage = await get_clip_storage_service()
            
            # Get video ID from info
            video_id = video_info_dict.get('id', task_id)
            
            # Upload video temporarily to Azure (expires in 2 hours)
            azure_blob_url = await clip_storage.upload_temp_video_for_processing(
                video_file_path=str(video_path),
                video_id=video_id,
                expiry_hours=2
            )
            
            logger.info(f"✅ Video uploaded to Azure: {azure_blob_url}")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to upload video to Azure Blob Storage: {str(e)}")
            logger.info(f"📁 Continuing with local file: {video_path}")
            # Don't fail the request if Azure upload fails, just log it
        
        # Calculate download metrics
        download_time_ms = int((time.time() - start_time) * 1000)
        file_size_bytes = video_path.stat().st_size
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        # Extract actual quality from filename or metadata
        actual_quality = None
        filename = video_path.name
        if "8K" in filename or "4320p" in filename:
            actual_quality = "8K"
        elif "4K" in filename or "2160p" in filename:
            actual_quality = "4K"
        elif "1440p" in filename:
            actual_quality = "1440p"
        elif "1080p" in filename:
            actual_quality = "1080p"
        elif "720p" in filename:
            actual_quality = "720p"
        
        # Create video info object
        video_info = YouTubeVideoInfo(
            id=video_info_dict.get('id', ''),
            title=video_info_dict.get('title', ''),
            duration=video_info_dict.get('duration'),
            view_count=video_info_dict.get('view_count'),
            upload_date=video_info_dict.get('upload_date'),
            uploader=video_info_dict.get('uploader'),
            description=video_info_dict.get('description', ''),
            is_live=video_info_dict.get('is_live', False)
        )
        
        logger.info(
            f"✅ Download completed (task_id: {task_id}) - "
            f"{file_size_mb:.1f}MB in {download_time_ms}ms"
        )
        
        # Include Azure blob URL in download info if available
        download_info = {
            "download_time_ms": download_time_ms,
            "file_size_bytes": file_size_bytes,
            "filename": video_path.name,
            "file_path": str(video_path.absolute()),
            "quality_settings": {
                "requested": quality,
                "actual": actual_quality
            }
        }
        
        # Add Azure blob URL if upload was successful
        if azure_blob_url:
            download_info["azure_blob_url"] = azure_blob_url
            download_info["storage_location"] = "azure_blob_storage"
        else:
            download_info["storage_location"] = "local_only"
        
        response = YouTubeDownloadResponse(
            task_id=task_id,
            success=True,
            video_info=video_info,
            download_info=download_info,
            file_path=str(video_path.absolute()),
            file_size_mb=round(file_size_mb, 2),
            quality_requested=quality,
            actual_quality=actual_quality,
            download_time_ms=download_time_ms
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error (task_id: {task_id}): {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/info")
async def get_youtube_video_info(url: str):
    """Get YouTube video information without downloading.
    
    Args:
        url: YouTube video URL
        
    Returns:
        Video metadata including available formats
        
    Raises:
        HTTPException: If unable to get video info
    """
    try:
        logger.info(f"🔍 Getting video info for: {url}")
        
        # Get video info
        video_info = get_video_info(url)
        
        # Get available formats
        try:
            formats = get_available_formats(url)
            # Limit to top 10 formats to avoid overwhelming response
            formats = formats[:10]
        except Exception as e:
            logger.warning(f"Failed to get formats: {e}")
            formats = []
        
        return {
            "success": True,
            "video_info": video_info,
            "available_formats": formats,
            "supported_qualities": ["best", "8k", "4k", "1440p", "1080p", "720p"],
            "quality_descriptions": {
                "best": "Highest available quality (auto-select)",
                "8k": "8K/4320p (if available)",
                "4k": "4K/2160p Ultra HD",
                "1440p": "2K/QHD",
                "1080p": "Full HD",
                "720p": "HD"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get video info: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to get video info: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check for YouTube download service."""
    try:
        # Test Apify client availability and configuration
        from app.services.youtube import youtube_service
        
        # Check if Apify token is configured
        apify_configured = youtube_service.apify_token is not None
        
        # Test downloads directory
        downloads_dir = Path("downloads")
        downloads_dir.mkdir(exist_ok=True)
        downloads_writable = os.access(downloads_dir, os.W_OK)
        
        return {
            "status": "healthy",
            "service": "youtube_downloader_apify",
            "apify_configured": apify_configured,
            "downloads_directory": str(downloads_dir.absolute()),
            "downloads_writable": downloads_writable,
            "supported_qualities": ["best", "8k", "4k", "1440p", "1080p", "720p"],
            "max_resolution": "4K (2160p) via Apify"
        }
        
    except Exception as e:
        # Check if it's specifically an Apify configuration error
        if "APIFY_TOKEN" in str(e):
            raise HTTPException(
                status_code=503,
                detail="Apify API token not configured. Please set APIFY_TOKEN environment variable."
            )
        else:
            raise HTTPException(
                status_code=503,
                detail=f"Service unhealthy: {str(e)}"
            ) 