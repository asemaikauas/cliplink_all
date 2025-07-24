"""
Cliplink Backend API

This is the main FastAPI application for the Cliplink backend service.
It provides authenticated endpoints for managing YouTube video submissions
and retrieving processed clips.
"""

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime
import uvicorn
import os
import logging

# Configure logging to suppress status polling noise
class StatusEndpointFilter(logging.Filter):
    def filter(self, record):
        # Filter out GET requests to /workflow/status/ endpoints
        try:
            message = record.getMessage()
            # Filter status polling requests and health checks
            if ('GET /workflow/status/' in message or 
                'GET /workflow/workflow-status/' in message or
                'GET /health' in message):
                return False
        except:
            pass
        return True

# Apply filter to uvicorn access logs
logging.getLogger("uvicorn.access").addFilter(StatusEndpointFilter())

from .auth import get_current_user, User
from .database import get_db, init_db, close_db
from .models import Video, Clip, ClipViewLog
from .schemas import (
    VideoResponse, 
    VideoSummaryResponse, 
    VideosListResponse,
    HealthResponse,
    ErrorResponse
)

# Import existing routers for video processing
from .routers import transcript, workflow, subtitles, users, clips

# Create FastAPI app
app = FastAPI(
    title="Cliplink Backend API",
    description="Backend service for Cliplink AI - YouTube video to vertical clips",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Static file serving for thumbnails and clips
import pathlib
thumbnails_dir = pathlib.Path("downloads/thumbnails")
thumbnails_dir.mkdir(parents=True, exist_ok=True)
app.mount("/thumbnails", StaticFiles(directory="downloads/thumbnails"), name="thumbnails")

# Static file serving for clips
clips_dir = pathlib.Path("downloads/clips")
clips_dir.mkdir(parents=True, exist_ok=True)
app.mount("/clips", StaticFiles(directory="downloads/clips"), name="clips")

# Include the video processing routers
app.include_router(transcript.router, prefix="/api/transcript", tags=["Transcript"])
app.include_router(workflow.router, prefix="/api/workflow", tags=["Workflow"])
app.include_router(subtitles.router, prefix="/api/subtitles", tags=["Subtitles"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(clips.router, prefix="/api", tags=["Clips"])

# Debug endpoint to test API routing
@app.get("/api/debug")
async def debug_endpoint():
    return {"message": "API is working", "timestamp": datetime.now()}

# Health check endpoint (keep at root level)
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}

# Serve React frontend (must be last to catch all routes)
frontend_dist_path = os.getenv("FRONTEND_DIST_PATH", "/app/frontend/dist")
if os.path.exists(frontend_dist_path):
    # Mount static files but make sure API routes take precedence
    app.mount("/", StaticFiles(directory=frontend_dist_path, html=True), name="frontend")
    print(f"🚀 Frontend dist path exists: {frontend_dist_path}")
else:
    # Development fallback
    @app.get("/")
    async def root():
        return {"message": "Cliplink Backend API", "docs": "/docs", "health": "/health"}


@app.on_event("startup")
async def startup():
    """Initialize the database on startup"""
    await init_db()


@app.on_event("shutdown")
async def shutdown():
    """Clean up database connections on shutdown"""
    await close_db()


@app.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint
    
    Returns the service status and database connectivity.
    """
    database_connected = True
    try:
        # Simple database connectivity check
        await db.execute(select(1))
    except Exception:
        database_connected = False
    
    return HealthResponse(
        status="healthy" if database_connected else "unhealthy",
        service="cliplink-backend",
        timestamp=datetime.now(),
        database_connected=database_connected
    )


@app.get("/api/videos", response_model=VideosListResponse)
async def get_user_videos(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    video_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get paginated list of user's videos
    
    Returns a paginated list of videos submitted by the authenticated user,
    with optional status filtering.
    """
    try:
        # Calculate offset
        offset = (page - 1) * per_page
        
        # Build base query
        query = select(Video).where(Video.user_id == current_user.id)
        count_query = select(func.count(Video.id)).where(Video.user_id == current_user.id)
        
        # Apply status filter if provided
        if video_status:
            query = query.where(Video.status == video_status)
            count_query = count_query.where(Video.status == video_status)
        
        # Add ordering and pagination
        query = query.order_by(Video.created_at.desc()).offset(offset).limit(per_page)
        
        # Execute queries
        result = await db.execute(query)
        videos = result.scalars().all()
        
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        # Convert to response models with clips count
        video_responses = []
        for video in videos:
            clips_count_query = select(func.count(Clip.id)).where(Clip.video_id == video.id)
            clips_count_result = await db.execute(clips_count_query)
            clips_count = clips_count_result.scalar()
            
            video_responses.append(VideoSummaryResponse(
                id=video.id,
                user_id=video.user_id,
                youtube_id=video.youtube_id,
                title=video.title,
                status=video.status,
                created_at=video.created_at,
                clips_count=clips_count
            ))
        
        return VideosListResponse(
            videos=video_responses,
            total=total,
            page=page,
            per_page=per_page,
            has_next=offset + per_page < total,
            has_prev=page > 1
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve videos: {str(e)}"
        )


@app.get("/api/videos/{video_id}", response_model=VideoResponse)
async def get_video_details(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific video with secure SAS URLs
    
    Returns video metadata along with all generated clips.
    Only returns videos belonging to the authenticated user.
    Generates temporary SAS URLs for secure access to Azure-hosted clips.
    """
    try:
        # Query video with clips
        query = select(Video).where(
            Video.id == video_id,
            Video.user_id == current_user.id
        )
        result = await db.execute(query)
        video = result.scalar_one_or_none()
        
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        # Get clips for this video
        clips_query = select(Clip).where(Clip.video_id == video.id).order_by(Clip.start_time)
        clips_result = await db.execute(clips_query)
        clips = clips_result.scalars().all()
        
        # Generate SAS URLs for secure access
        from app.services.azure_storage import get_azure_storage_service
        azure_storage = await get_azure_storage_service()
        
        # Process clips and generate SAS URLs
        clips_with_sas = []
        for clip in clips:
            clip_dict = {
                "id": clip.id,
                "video_id": clip.video_id,
                "start_time": clip.start_time,
                "end_time": clip.end_time,
                "duration": clip.end_time - clip.start_time,
                "created_at": clip.created_at,
                "title": clip.title or f"Clip {clip.start_time:.0f}s-{clip.end_time:.0f}s",
                "file_size": clip.file_size
            }
            
            # Generate SAS URL for the clip (2-hour expiry)
            if clip.blob_url:
                try:
                    sas_url = await azure_storage.generate_sas_url(
                        blob_url=clip.blob_url,
                        expiry_hours=2
                    )
                    clip_dict["s3_url"] = sas_url  # Frontend expects s3_url field
                except Exception as e:
                    print(f"Warning: Failed to generate SAS URL for clip {clip.id}: {str(e)}")
                    clip_dict["s3_url"] = clip.blob_url  # Fallback to original URL
            else:
                clip_dict["s3_url"] = None
            
            # Generate SAS URL for the thumbnail (2-hour expiry)
            if clip.thumbnail_url:
                try:
                    thumbnail_sas_url = await azure_storage.generate_sas_url(
                        blob_url=clip.thumbnail_url,
                        expiry_hours=2
                    )
                    clip_dict["thumbnail_url"] = thumbnail_sas_url
                except Exception as e:
                    print(f"Warning: Failed to generate SAS URL for thumbnail {clip.id}: {str(e)}")
                    clip_dict["thumbnail_url"] = clip.thumbnail_url  # Fallback to original URL
            else:
                clip_dict["thumbnail_url"] = None
            
            clips_with_sas.append(clip_dict)
        
        return VideoResponse(
            id=video.id,
            user_id=video.user_id,
            youtube_id=video.youtube_id,
            title=video.title,
            status=video.status,
            created_at=video.created_at,
            clips=clips_with_sas
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting video details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve video details: {str(e)}"
        )


@app.post("/api/videos/{video_id}/clips/{clip_id}/view")
async def log_clip_view(
    video_id: str,
    clip_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Log a clip view event
    
    Records that the authenticated user viewed a specific clip.
    Used for analytics and tracking.
    """
    try:
        # Verify the clip exists and belongs to the user's video
        clip_query = select(Clip).join(Video).where(
            Clip.id == clip_id,
            Video.id == video_id,
            Video.user_id == current_user.id
        )
        clip_result = await db.execute(clip_query)
        clip = clip_result.scalar_one_or_none()
        
        if not clip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clip not found"
            )
        
        # Create view log entry
        view_log = ClipViewLog(
            user_id=current_user.id,
            clip_id=clip.id
        )
        
        db.add(view_log)
        await db.commit()
        
        return {"message": "Clip view logged successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to log clip view: {str(e)}"
        )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors"""
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal server error"
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENV", "production") == "development"
    )
