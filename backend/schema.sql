-- Cliplink AI Database Schema
-- PostgreSQL schema for managing YouTube video processing and clip generation

-- Enable UUID extension for generating UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create ENUM for video processing status
CREATE TYPE video_status AS ENUM ('pending', 'processing', 'done', 'failed');

-- Users table: Stores registered users of the application
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clerk_id VARCHAR(255) UNIQUE NOT NULL, -- Clerk user ID from JWT sub claim
    email VARCHAR(255) UNIQUE NOT NULL, -- User's email address, must be unique
    first_name VARCHAR(255), -- User's first name
    last_name VARCHAR(255), -- User's last name
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, -- When user registered
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP -- When user data was last updated
);

-- Videos table: Metadata about YouTube videos submitted by users
-- Note: We only store metadata, not the actual video files
CREATE TABLE videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, -- Owner of the video
    youtube_id VARCHAR(20) NOT NULL, -- YouTube video ID (e.g., "dQw4w9WgXcQ")
    title TEXT, -- Optional: YouTube video title if fetched
    status video_status NOT NULL DEFAULT 'pending', -- Processing status
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP -- When video was submitted
);

-- Clips table: Individual short video clips generated from YouTube videos
-- Clips are stored in AWS S3, so we only store metadata and S3 URLs
CREATE TABLE clips (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE, -- Parent video
    s3_url TEXT NOT NULL, -- AWS S3 URL where the clip is stored
    start_time FLOAT NOT NULL, -- Start time in seconds from original video
    end_time FLOAT NOT NULL, -- End time in seconds from original video
    duration FLOAT NOT NULL, -- Duration of the clip in seconds
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP -- When clip was generated
);

-- Clip view logs table: Tracks when users view clips for analytics
CREATE TABLE clip_view_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, -- User who viewed the clip
    clip_id UUID NOT NULL REFERENCES clips(id) ON DELETE CASCADE, -- Clip that was viewed
    viewed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP -- When the clip was viewed
);

-- Indexes for performance optimization
-- Index on user_id for fast lookup of user's videos
CREATE INDEX idx_videos_user_id ON videos(user_id);

-- Index on video_id for fast lookup of clips belonging to a video
CREATE INDEX idx_clips_video_id ON clips(video_id);

-- Index on user_id in clip_view_logs for analytics queries
CREATE INDEX idx_clip_view_logs_user_id ON clip_view_logs(user_id);

-- Index on clip_id in clip_view_logs for clip-specific analytics
CREATE INDEX idx_clip_view_logs_clip_id ON clip_view_logs(clip_id);

-- Index on video status for filtering videos by processing status
CREATE INDEX idx_videos_status ON videos(status);

-- Index on created_at for chronological queries
CREATE INDEX idx_videos_created_at ON videos(created_at);
CREATE INDEX idx_clips_created_at ON clips(created_at);
CREATE INDEX idx_clip_view_logs_viewed_at ON clip_view_logs(viewed_at);

-- Comments on tables
COMMENT ON TABLE users IS 'Registered users of the Cliplink AI application';
COMMENT ON TABLE videos IS 'Metadata about YouTube videos submitted for processing';
COMMENT ON TABLE clips IS 'Individual short video clips generated from YouTube videos';
COMMENT ON TABLE clip_view_logs IS 'Logs of when users view clips for analytics';

-- Comments on important columns
COMMENT ON COLUMN videos.youtube_id IS 'YouTube video identifier (11 characters)';
COMMENT ON COLUMN videos.status IS 'Current processing status of the video';
COMMENT ON COLUMN clips.s3_url IS 'AWS S3 URL where the processed clip is stored';
COMMENT ON COLUMN clips.start_time IS 'Start time in seconds from the original video';
COMMENT ON COLUMN clips.end_time IS 'End time in seconds from the original video';
COMMENT ON COLUMN clips.duration IS 'Duration of the clip in seconds';

-- Additional constraints
-- Ensure clip times are logical
ALTER TABLE clips ADD CONSTRAINT check_clip_times 
    CHECK (start_time >= 0 AND end_time > start_time AND duration > 0);

-- Ensure YouTube ID is reasonable length (YouTube IDs are typically 11 characters)
ALTER TABLE videos ADD CONSTRAINT check_youtube_id_length 
    CHECK (LENGTH(youtube_id) BETWEEN 8 AND 20);

-- Ensure email format is reasonable
ALTER TABLE users ADD CONSTRAINT check_email_format 
    CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'); 