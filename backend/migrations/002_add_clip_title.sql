-- Migration: Add title column to clips table
-- This allows storing individual viral segment titles for each clip

BEGIN;

-- Add title column to clips table
ALTER TABLE clips ADD COLUMN title VARCHAR(255);

-- Add index on title for better search performance
CREATE INDEX idx_clips_title ON clips(title);

-- Update existing clips with default titles (if any exist)
UPDATE clips SET title = 'Clip ' || ROW_NUMBER() OVER (PARTITION BY video_id ORDER BY start_time)
WHERE title IS NULL;

-- Add comment for the new column
COMMENT ON COLUMN clips.title IS 'Individual clip title from viral segment analysis (e.g., "The Harsh Truth Most People Aren''t Really Living")';

COMMIT; 