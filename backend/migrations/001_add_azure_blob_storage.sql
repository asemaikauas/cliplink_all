-- Migration: Add Azure Blob Storage support
-- This migration updates the clips table to support Azure Blob Storage URLs
-- and adds additional fields for better file management

BEGIN;

-- Rename s3_url to blob_url for Azure Blob Storage
ALTER TABLE clips RENAME COLUMN s3_url TO blob_url;

-- Add new columns for enhanced file management
ALTER TABLE clips 
ADD COLUMN thumbnail_url TEXT,
ADD COLUMN file_size FLOAT;

-- Update comments to reflect Azure Blob Storage usage
COMMENT ON COLUMN clips.blob_url IS 'Azure Blob Storage URL where the processed clip is stored';
COMMENT ON COLUMN clips.thumbnail_url IS 'Azure Blob Storage URL for the clip thumbnail image';
COMMENT ON COLUMN clips.file_size IS 'File size in bytes';

-- Add index on blob_url for faster lookups
CREATE INDEX idx_clips_blob_url ON clips(blob_url);

-- Add index on thumbnail_url for faster lookups
CREATE INDEX idx_clips_thumbnail_url ON clips(thumbnail_url);

-- Update table comment
COMMENT ON TABLE clips IS 'Individual short video clips generated from YouTube videos, stored in Azure Blob Storage';

COMMIT; 