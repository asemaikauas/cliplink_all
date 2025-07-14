"""
User management routes for Cliplink Backend

This module provides authenticated endpoints for user profile management
and demonstrates the Clerk JWT authentication system.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID

from ..auth import get_current_user, get_optional_user
from ..database import get_db
from ..models import User, Video

router = APIRouter()


class UserResponse(BaseModel):
    """Response model for user data"""
    id: UUID
    clerk_id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    """Request model for updating user profile"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserStatsResponse(BaseModel):
    """Response model for user statistics"""
    total_videos: int
    total_clips: int
    videos_processing: int
    videos_completed: int
    videos_failed: int


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's profile information
    
    This is a protected route that requires authentication.
    """
    return UserResponse(
        id=current_user.id,
        clerk_id=current_user.clerk_id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        created_at=current_user.created_at.isoformat(),
        updated_at=current_user.updated_at.isoformat()
    )


@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user's profile information
    
    This is a protected route that requires authentication.
    """
    try:
        updated = False
        
        if profile_update.first_name is not None:
            current_user.first_name = profile_update.first_name
            updated = True
            
        if profile_update.last_name is not None:
            current_user.last_name = profile_update.last_name
            updated = True
        
        if updated:
            await db.commit()
            await db.refresh(current_user)
        
        return UserResponse(
            id=current_user.id,
            clerk_id=current_user.clerk_id,
            email=current_user.email,
            first_name=current_user.first_name,
            last_name=current_user.last_name,
            created_at=current_user.created_at.isoformat(),
            updated_at=current_user.updated_at.isoformat()
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )


@router.get("/me/stats", response_model=UserStatsResponse)
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's statistics
    
    This is a protected route that requires authentication.
    """
    try:
        # Get user's videos with status counts
        from sqlalchemy import func
        from ..models import VideoStatus, Clip
        
        # Count total videos
        total_videos_query = select(func.count(Video.id)).where(Video.user_id == current_user.id)
        total_videos_result = await db.execute(total_videos_query)
        total_videos = total_videos_result.scalar() or 0
        
        # Count videos by status
        status_counts = {}
        for video_status_enum in VideoStatus:
            status_query = select(func.count(Video.id)).where(
                Video.user_id == current_user.id,
                Video.status == video_status_enum.value
            )
            status_result = await db.execute(status_query)
            status_counts[video_status_enum.value] = status_result.scalar() or 0
        
        # Count total clips
        total_clips_query = select(func.count(Clip.id)).join(Video).where(
            Video.user_id == current_user.id
        )
        total_clips_result = await db.execute(total_clips_query)
        total_clips = total_clips_result.scalar() or 0
        
        return UserStatsResponse(
            total_videos=total_videos,
            total_clips=total_clips,
            videos_processing=status_counts.get("processing", 0),
            videos_completed=status_counts.get("done", 0),
            videos_failed=status_counts.get("failed", 0)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user stats: {str(e)}"
        )


@router.get("/dashboard")
async def get_dashboard(
    current_user: User = Depends(get_current_user)
):
    """
    Protected dashboard endpoint
    
    This demonstrates a simple protected route that requires authentication.
    """
    return {
        "message": f"Welcome to your dashboard, {current_user.first_name or current_user.email}!",
        "user_id": str(current_user.id),
        "clerk_id": current_user.clerk_id,
        "email": current_user.email
    }


@router.get("/public-info")
async def get_public_info(
    user: Optional[User] = Depends(get_optional_user)
):
    """
    Public endpoint with optional authentication
    
    This demonstrates how to use optional authentication where the endpoint
    is accessible to both authenticated and unauthenticated users.
    """
    if user:
        return {
            "message": f"Hello {user.first_name or user.email}! You are authenticated.",
            "authenticated": True,
            "user_id": str(user.id)
        }
    else:
        return {
            "message": "Hello anonymous user! This endpoint is public.",
            "authenticated": False
        }
