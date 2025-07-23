"""
Database models for Cliplink Backend

This module defines SQLAlchemy models that correspond to the PostgreSQL
schema used by the application.
"""

from sqlalchemy import Column, String, Text, Float, DateTime, Enum, ForeignKey, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from uuid import uuid4
import enum

Base = declarative_base()


class User(Base):
    """
    User model representing authenticated users via Clerk
    
    Corresponds to the 'users' table in PostgreSQL schema
    """
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    clerk_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<User(id={self.id}, clerk_id={self.clerk_id}, email={self.email})>"


class VideoStatus(enum.Enum):
    """Enumeration for video processing status"""
    PENDING = "pending"
    PROCESSING = "processing" 
    DONE = "done"
    FAILED = "failed"


class Video(Base):
    """
    Video model representing YouTube video metadata
    
    Corresponds to the 'videos' table in PostgreSQL schema
    """
    __tablename__ = "videos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    youtube_id = Column(String(20), nullable=False)
    title = Column(Text, nullable=True)
    status = Column(Enum(VideoStatus, name="video_status"), nullable=False, default=VideoStatus.PENDING, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    clips = relationship("Clip", back_populates="video", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Video(id={self.id}, youtube_id={self.youtube_id}, status={self.status})>"


class Clip(Base):
    """
    Clip model representing processed video clips
    
    Corresponds to the 'clips' table in PostgreSQL schema
    """
    __tablename__ = "clips"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    blob_url = Column(Text, nullable=False)  # Azure Blob Storage URL
    thumbnail_url = Column(Text, nullable=True)  # Thumbnail image URL
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    duration = Column(Float, nullable=False)
    file_size = Column(Float, nullable=True)  # File size in bytes
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    video = relationship("Video", back_populates="clips")
    view_logs = relationship("ClipViewLog", back_populates="clip", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Clip(id={self.id}, video_id={self.video_id}, duration={self.duration})>"


class ClipViewLog(Base):
    """
    ClipViewLog model for tracking clip views
    
    Corresponds to the 'clip_view_logs' table in PostgreSQL schema
    """
    __tablename__ = "clip_view_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    clip_id = Column(UUID(as_uuid=True), ForeignKey("clips.id", ondelete="CASCADE"), nullable=False, index=True)
    viewed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    clip = relationship("Clip", back_populates="view_logs")
    
    def __repr__(self):
        return f"<ClipViewLog(id={self.id}, user_id={self.user_id}, clip_id={self.clip_id})>" 