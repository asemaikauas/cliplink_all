-- Migration: Fix video_status enum to match schema.sql
-- This migration updates the video_status enum to use lowercase values
-- as defined in the original schema.sql file

BEGIN;

-- First, create the new enum type with correct lowercase values
CREATE TYPE video_status_new AS ENUM ('pending', 'processing', 'done', 'failed');

-- Update the videos table to use the new enum type
-- We need to map the old uppercase values to new lowercase values
ALTER TABLE videos 
ALTER COLUMN status TYPE video_status_new 
USING CASE 
    WHEN status::text = 'PENDING' THEN 'pending'::video_status_new
    WHEN status::text = 'PROCESSING' THEN 'processing'::video_status_new
    WHEN status::text = 'DONE' THEN 'done'::video_status_new
    WHEN status::text = 'FAILED' THEN 'failed'::video_status_new
    ELSE 'pending'::video_status_new
END;

-- Drop the old enum type
DROP TYPE video_status;

-- Rename the new enum type to the original name
ALTER TYPE video_status_new RENAME TO video_status;

-- Update the default value to use lowercase
ALTER TABLE videos ALTER COLUMN status SET DEFAULT 'pending';

-- Add a comment to track this migration
COMMENT ON TYPE video_status IS 'Video processing status enum - updated to lowercase values in migration 002';

COMMIT; 